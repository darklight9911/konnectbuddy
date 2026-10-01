#!/usr/bin/env python3
"""
Agentic RAG Pipeline for DIU Konnect (KonnectBuddy)
Retrieves official context from Daffodil International University (DIU) sources
and answers queries in English, Bengali, or Banglish with exact citations.
"""

import os
import sys
import io
import argparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

import logging

try:
    import pypdf
    logging.getLogger("pypdf").setLevel(logging.ERROR)
except ImportError:
    pypdf = None

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.tools import tool

try:
    from langchain.agents import create_agent
except ImportError:
    create_agent = None

try:
    from langgraph.prebuilt import create_react_agent
except ImportError:
    create_react_agent = None

# Load environment variables (.env file)
load_dotenv()

# 1. Define the strict allowed sources
TARGET_URLS = [
    "https://daffodilvarsity.edu.bd/noticeboard",
    "https://alumni.daffodilvarsity.edu.bd/articles/membership-guidelines-28",  # Direct alumni card guideline
    "https://alumni.daffodilvarsity.edu.bd/",
    "https://daffodilvarsity.edu.bd/scholarship/diu-scholarship"
]

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
COLLECTION_NAME = "diu_knowledge_base"


def fetch_dynamic_scholarships(source_url: str, headers: dict):
    """
    Fetches full scholarship accordions from DIU's backend API,
    resolving the Next.js client-side dynamic rendering where the HTML shell is empty.
    """
    docs = []
    api_url = "https://webbackend.daffodilvarsity.edu.bd/api/v2/public/accordion/scholarship"
    try:
        r = requests.get(api_url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json().get("data", {})
            for cat in data.get("categories", []):
                cat_title = cat.get("title", "")
                for acc in cat.get("accordions", []):
                    acc_title = acc.get("title", "")
                    desc = acc.get("description", "")
                    soup = BeautifulSoup(desc, "html.parser")
                    # Format HTML tables as structured markdown tables
                    for t in soup.find_all("table"):
                        rows = []
                        for tr in t.find_all("tr"):
                            cells = [td.get_text(" ", strip=True) for td in tr.find_all(["th", "td"])]
                            if cells:
                                rows.append(" | ".join(cells))
                        t.replace_with("\n" + "\n".join(rows) + "\n")
                    content = (
                        f"DIU Scholarship & Waiver Policy\n"
                        f"Category: {cat_title}\n"
                        f"Title: {acc_title}\n\n"
                        f"{soup.get_text(separator='\n', strip=True)}"
                    )
                    docs.append(Document(page_content=content, metadata={"source": source_url}))
            print(f"  ✓ Extracted {len(docs)} dynamic scholarship & waiver policies from DIU backend.")
    except Exception as e:
        print(f"  ✗ Error fetching dynamic scholarship content: {e}")
    return docs


def fetch_dynamic_notices(source_url: str, headers: dict):
    """
    Fetches latest notices from DIU's backend API, extracts attached PDF files,
    and indexes individual notice URLs for deep grounding.
    """
    docs = []
    api_url = "https://webbackend.daffodilvarsity.edu.bd/api/v1/public/notice?per_page=40"
    base_notice_url = source_url.rstrip("/")

    try:
        r = requests.get(api_url, headers=headers, timeout=15)
        if r.status_code == 200:
            notices = r.json().get("data", [])
            for n in notices:
                title = n.get("title", "").strip()
                slug = n.get("slug", "").strip()
                notice_url = f"{base_notice_url}/{slug}" if slug else base_notice_url
                category = n.get("notice_category", "")
                dept = n.get("department", "")
                date = n.get("create_at") or n.get("date") or ""

                pdf_text = ""
                file_urls = []
                for f in n.get("noticeFiles", []):
                    fname = f.get("file_name", "")
                    if fname:
                        file_urls.append(fname)
                        if pypdf is not None and fname.lower().endswith(".pdf"):
                            try:
                                pr = requests.get(fname, headers=headers, timeout=10)
                                if pr.status_code == 200:
                                    reader = pypdf.PdfReader(io.BytesIO(pr.content))
                                    pages_text = []
                                    for p in reader.pages[:4]:  # first 4 pages
                                        t = p.extract_text()
                                        if t:
                                            pages_text.append(t.strip())
                                    if pages_text:
                                        pdf_text += "\n[Attached Notice PDF Content]:\n" + "\n".join(pages_text)
                            except Exception:
                                pass

                content = (
                    f"DIU Official Notice\n"
                    f"Title: {title}\n"
                    f"Department: {dept}\n"
                    f"Category: {category}\n"
                    f"Published Date: {date}\n"
                    f"Notice URL: {notice_url}\n"
                )
                if file_urls:
                    content += f"Attachments: {', '.join(file_urls)}\n"
                if pdf_text:
                    content += pdf_text

                docs.append(Document(page_content=content, metadata={"source": notice_url}))
            print(f"  ✓ Extracted {len(docs)} dynamic notices (with PDF contents) from DIU backend.")
    except Exception as e:
        print(f"  ✗ Error fetching dynamic noticeboard content: {e}")
    return docs


def scrape_pages(urls):
    """Scrapes raw text from the specified DIU target URLs."""
    documents = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    print(f"\n[Scraper] Fetching {len(urls)} target URLs...")
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                # Strip out non-content elements
                for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                    element.decompose()
                text = " ".join(soup.stripped_strings)
                documents.append(Document(page_content=text, metadata={"source": url}))
                print(f"  ✓ Successfully scraped: {url} ({len(text)} characters)")
            else:
                print(f"  ✗ Failed to fetch {url}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"  ✗ Error fetching {url}: {e}")

        # Handle Next.js client-side dynamic rendering
        if "scholarship" in url:
            dynamic_scholarships = fetch_dynamic_scholarships(url, headers)
            documents.extend(dynamic_scholarships)
        elif "noticeboard" in url:
            dynamic_notices = fetch_dynamic_notices(url, headers)
            documents.extend(dynamic_notices)

    return documents


def get_vector_store(force_reindex: bool = False, in_memory: bool = False):
    """Initializes or loads the vector store."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    if in_memory:
        print("[VectorDB] Creating in-memory vector store...")
        raw_docs = scrape_pages(TARGET_URLS)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
        chunks = text_splitter.split_documents(raw_docs)
        print(f"[VectorDB] Generated {len(chunks)} chunks across sources.")
        return Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=COLLECTION_NAME
        )

    # Persistent storage check
    if os.path.exists(DB_DIR) and not force_reindex:
        print(f"[VectorDB] Loading existing vector store from '{DB_DIR}'...")
        return Chroma(
            persist_directory=DB_DIR,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME
        )

    print(f"[VectorDB] Building new vector store at '{DB_DIR}'...")
    raw_docs = scrape_pages(TARGET_URLS)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    chunks = text_splitter.split_documents(raw_docs)
    print(f"[VectorDB] Generated {len(chunks)} chunks across sources.")

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_DIR,
        collection_name=COLLECTION_NAME
    )
    return vector_store


def build_agent(vector_store):
    """Creates the agent tool and ReAct agent graph."""

    # 3. Create the Retrieval Tool
    @tool
    def search_diu_knowledge_base(query: str) -> str:
        """
        Search exclusively within Daffodil International University (DIU) 
        official sources: Alumni affairs, Noticeboard, and Scholarships.
        """
        results = vector_store.similarity_search(query, k=4)
        if not results:
            return "No relevant records found in the verified DIU sources."

        formatted = []
        for doc in results:
            formatted.append(f"[Source: {doc.metadata['source']}]\n{doc.page_content}")
        return "\n\n---\n\n".join(formatted)

    # 4. Agent Configuration & System Instructions
    system_prompt = (
        "You are KonnectBuddy, a professional and courteous AI assistant dedicated to DIU Konnect. "
        "Your knowledge base is STRICTLY RESTRICTED to DIU Noticeboard, Alumni, and Scholarship pages. "
        "\n\nRules:"
        "\n1. Rely solely on the retrieved tool output. Do not make assumptions or fabricate info."
        "\n2. Always provide your final response in clear, professional English maintaining a polite and helpful tone, regardless of whether the user query is in English, Bengali, or Banglish."
        "\n3. Formulate your internal tool search queries in precise, canonical English terms."
        "\n4. Present details clearly and elegantly using structured lists, markdown tables, or bullet points where appropriate."
        "\n5. Always cite the exact source URL provided in the retrieved context."
        "\n6. If the requested information is absent from the official sources, politely inform the user that it is not available in the official records and offer guidance on where they may inquire further."
    )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    if create_agent is not None:
        agent = create_agent(
            model=llm,
            tools=[search_diu_knowledge_base],
            system_prompt=system_prompt
        )
    elif create_react_agent is not None:
        try:
            agent = create_react_agent(
                model=llm,
                tools=[search_diu_knowledge_base],
                prompt=system_prompt
            )
        except TypeError:
            agent = create_react_agent(
                model=llm,
                tools=[search_diu_knowledge_base],
                state_modifier=system_prompt
            )
    else:
        raise ImportError(
            "Neither langchain.agents.create_agent nor langgraph.prebuilt.create_react_agent is available."
        )

    return agent


def ask_konnectbuddy(agent, user_query: str):
    """Executes a query through the ReAct agent and prints the result."""
    print(f"\n{'=' * 60}")
    print(f"User Query: {user_query}")
    print(f"{'-' * 60}")
    response = agent.invoke({"messages": [("user", user_query)]})
    final_reply = response["messages"][-1].content
    print(final_reply)
    print(f"{'=' * 60}\n")
    return final_reply


def main():
    parser = argparse.ArgumentParser(description="DIU Konnect Agentic RAG Pipeline (KonnectBuddy)")
    parser.add_argument("--query", "-q", type=str, help="Specific query to run")
    parser.add_argument("--interactive", "-i", action="store_true", help="Launch interactive chat mode")
    parser.add_argument("--reindex", action="store_true", help="Force re-scraping and vector store reindexing")
    parser.add_argument("--in-memory", action="store_true", help="Use in-memory vector store without persisting to disk")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n[ERROR] OPENAI_API_KEY environment variable is not set!")
        print("Please set your OpenAI API key using one of the following:")
        print("  1. Export in shell: export OPENAI_API_KEY='your-key-here'")
        print("  2. Create a .env file with: OPENAI_API_KEY=your-key-here\n")
        sys.exit(1)

    # Initialize Vector DB & Agent
    vector_store = get_vector_store(force_reindex=args.reindex, in_memory=args.in_memory)
    agent = build_agent(vector_store)

    if args.query:
        ask_konnectbuddy(agent, args.query)
    elif args.interactive:
        print("\n--- KonnectBuddy Interactive Mode (Type 'exit' or 'quit' to end) ---")
        while True:
            try:
                user_input = input("\nYou: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit"]:
                    print("Exiting KonnectBuddy.")
                    break
                ask_konnectbuddy(agent, user_input)
            except (KeyboardInterrupt, EOFError):
                print("\nExiting KonnectBuddy.")
                break
    else:
        # Default test suite
        print("\n--- Running Default Evaluation Queries ---")
        test_queries = [
            "@konnectbuddy kivabe alumni card collect korte hobe?",
            "Where can I collect my alumni card and what are the fees? @konnectbuddy",
            "DIU scholarship pabar jonno minimum criteria ki ki lagbe?"
        ]
        for query in test_queries:
            ask_konnectbuddy(agent, query)


if __name__ == "__main__":
    main()
