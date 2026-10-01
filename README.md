# DIU Konnect: Standalone Agentic RAG Pipeline

A self-contained, standalone Python script and Jupyter Notebook implementing an Agentic RAG (Retrieval-Augmented Generation) pipeline for **Daffodil International University (DIU)**. 

Designed for **DIU Konnect (KonnectBuddy)** to answer student and alumni queries with verified official information in **Bengali**, **Banglish**, and **English**.

---

## 🚀 Features

* **Targeted Web Scraping**: Scrapes official DIU sources directly:
  * DIU Noticeboard: `https://daffodilvarsity.edu.bd/noticeboard`
  * Alumni Membership Guidelines: `https://alumni.daffodilvarsity.edu.bd/articles/membership-guidelines-28`
  * Alumni Association Portal: `https://alumni.daffodilvarsity.edu.bd/`
  * DIU Scholarship Guidelines: `https://daffodilvarsity.edu.bd/scholarship/diu-scholarship`
* **Local Vector Database**: Chunks documents with `RecursiveCharacterTextSplitter` and embeds with OpenAI's `text-embedding-3-small` in a local `chromadb` instance (supports both persistent disk storage to save API credits and ephemeral in-memory mode).
* **LangChain / LangGraph ReAct Agent**: Powered by `gpt-4o-mini` with strict system prompt grounding to eliminate hallucinations.
* **Cross-Lingual Intent Mapping & Polite Professional English Response**: Translates Banglish/Bengali queries into canonical English terms for semantic retrieval, and delivers well-structured, professional, and courteous English responses.
* **Deep Dynamic Scraping & PDF Ingestion**: Handles Next.js client-side rendering for full scholarship accordion tables and parses noticeboard PDF attachment documents.
* **Exact Source Citation**: Mandates URL citations for every answer.
* **Multiple Interfaces**: CLI query mode, interactive REPL mode, benchmark mode, and a Jupyter Notebook.

---

## 📖 Comprehensive Documentation

For detailed architectural specifications, end-to-end Mermaid workflow diagrams, and technical deep-dives, explore the [`docs/`](docs/README.md) directory:

* **[Architecture Overview](docs/architecture.md)**: System topology, ingestion, vector store, and reasoning layers.
* **[Agent & System Workflows](docs/workflow.md)**: Mermaid sequence diagrams, ReAct execution loops, and state machine graphs.
* **[Data Pipeline & Scraping](docs/data_pipeline.md)**: Handling Next.js backend APIs, in-memory PDF extraction, and text chunking.
* **[Agent & Prompt Engineering](docs/agent_and_prompt_engineering.md)**: Dual LangChain/LangGraph support, grounding rules, and cross-lingual translation.
* **[Setup & Deployment Guide](docs/setup_and_deployment.md)**: Full setup instructions, CLI usage options, and troubleshooting.
* **[API & CLI Reference](docs/api_and_cli_reference.md)**: Complete parameter and return type references for all functions and flags.
* **[Benchmarks & Evaluation](docs/benchmarks_and_evaluation.md)**: Test queries, expected outputs, and evaluation metrics.

---

## 📦 Setup & Prerequisites

### 1. Clone & Set Up Python Environment

```bash
# Navigate to the project directory
cd /path/to/agenticBot

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 2. Configure OpenAI API Key

You can configure your OpenAI API key in either of two ways:

**Option A: Using `.env` file (Recommended)**
```bash
cp .env.example .env
# Edit .env and paste your API key:
# OPENAI_API_KEY="sk-..."
```

**Option B: Shell Export**
```bash
export OPENAI_API_KEY="sk-..."
```

---

## 💻 Usage

### 1. Run Default Benchmark Evaluation Queries
Runs pre-configured test queries (Banglish, English, Scholarship):
```bash
python agentic_rag.py
```

### 2. Ask a Specific Question via CLI
```bash
python agentic_rag.py --query "@konnectbuddy kivabe alumni card collect korte hobe?"
```

```bash
python agentic_rag.py --query "What is the fee for the 'I am Daffodilian' smart card?"
```

### 3. Interactive Chat Mode
Launch a chat session with KonnectBuddy:
```bash
python agentic_rag.py --interactive
```

### 4. Vector Store Options
* Force re-scrape and rebuild the Chroma index:
  ```bash
  python agentic_rag.py --reindex
  ```
* Run with in-memory vector store (ephemeral, no disk caching):
  ```bash
  python agentic_rag.py --in-memory
  ```

---

## 📓 Running in Jupyter Notebook

To explore step-by-step or visualize tool calls and retrieved chunks:

1. Launch Jupyter Notebook or JupyterLab:
   ```bash
   jupyter notebook agentic_rag_demo.ipynb
   ```
2. Run cells sequentially to observe scraping, chunk creation, vector indexing, tool calling, and responses.

---

## 🔍 Sample Evaluation & Output

### Query:
```text
@konnectbuddy kivabe alumni card collect korte hobe?
```

### Expected Output:
```markdown
Alumni card collect korar step-gulo niche deya holo:

1. **Eligibility:** DIU theke degree complete thakte hobe।
2. **Application:** Office of the Controller of Examinations-e giye application form puron korte hobe।
3. **Fees:**
   * DIU Alumni Association Membership: 200 BDT
   * "I am Daffodilian" Smart Card: 300 BDT
4. **Delivery/Collection:** Student portal-e status check korun। Card print hoye gele Office of the Controller of Examinations (Exam Office) theke collect korte parben।

Source: https://alumni.daffodilvarsity.edu.bd/articles/membership-guidelines-28
```

---

## 📐 Key Design Considerations

1. **Sub-route Scraping**:
   The DIU Alumni portal places key procedural guidelines under `/articles/membership-guidelines-28`. Adding direct article sub-routes ensures deep institutional knowledge is captured without missing details behind navigation links.

2. **Cross-Lingual Semantic Gap**:
   `text-embedding-3-small` excels at mapping cross-lingual queries. The agent is explicitly instructed to formulate internal retrieval queries in formal English (e.g., `"alumni card fee collection procedure"`) even when asked in Banglish (`"kivabe card collect korbo"`), bridging lexical mismatch.
