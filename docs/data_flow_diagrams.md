# Data Flow Diagrams (DFD)

This document provides formal **Level 0**, **Level 1**, and **Level 2** Data Flow Diagrams (DFDs) for **DIU Konnect (KonnectBuddy)**. These diagrams illustrate how data originates, transforms, flows between subsystems, persists in data stores, and reaches external actors.

---

## 📌 Overview of DFD Levels

Data Flow Diagrams model the functional and data transformation perspective of a software system:

* **Level 0 (Context Diagram)**: Defines the system boundary, treating the entire application as a single process and illustrating its relationships with external entities (terminators).
* **Level 1 (System Functional Decomposition)**: Explodes the Level 0 process into core functional subsystems, major data stores, and primary inter-process data pipelines.
* **Level 2 (Detailed Sub-Process Decomposition)**: Explodes key Level 1 subsystems into granular algorithmic operations, showing internal transformations, conditional routing, and intermediate data transfers.

---

## 🌐 DFD Level 0: Context Diagram

The Context Diagram shows the entire DIU Konnect system as a single black box (`Process 0`), communicating with four external entities:
1. **User / Student / Alumni**: Submits natural language queries across languages and receives verified, grounded answers.
2. **DIU Institutional Web & API Infrastructure**: Supplies raw web pages, dynamic Next.js JSON payloads, and binary notice PDFs.
3. **OpenAI Cloud Services**: Powers 1536-dimensional semantic embeddings (`text-embedding-3-small`) and ReAct reasoning (`gpt-4o-mini`).
4. **System Administrator / CLI Operator**: Initiates indexing, re-indexing flags, configuration, and benchmark evaluations.

```mermaid
flowchart TB
    classDef entity fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#01579b;
    classDef process fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100;

    USER["External Entity: User<br/>(Student / Alumni / Faculty)"]:::entity
    DIU_WEB["External Entity: DIU Web & API Infrastructure<br/>(Main Portal, Backend REST APIs, Notice CDN)"]:::entity
    OPENAI["External Entity: OpenAI Cloud Services<br/>(Embedding API & LLM Reasoning API)"]:::entity
    ADMIN["External Entity: System Operator / CLI<br/>(Execution Flags, Config, .env)"]:::entity

    SYS(("Process 0<br/><br/>DIU Konnect<br/>(KonnectBuddy)<br/>Agentic RAG System")):::process

    %% User flows
    USER -->|"User Query (English, Bengali, Banglish)"| SYS
    SYS -->|"Grounded Response + Exact Source URLs"| USER

    %% Admin flows
    ADMIN -->|"Execution Flags (--query, --interactive, --reindex)"| SYS
    ADMIN -->|"API Credentials & Config Settings"| SYS

    %% DIU Infrastructure flows
    SYS -->|"HTTP GET Requests & REST API Calls"| DIU_WEB
    DIU_WEB -->|"HTML Pages, JSON Accordions, Binary Notice PDFs"| SYS

    %% OpenAI flows
    SYS -->|"Text Chunks for Vectorization"| OPENAI
    OPENAI -->|"1536-dim Embedding Vectors"| SYS
    SYS -->|"System Prompt, Chat History & Search Context"| OPENAI
    OPENAI -->|"LLM Tool Calls & Synthesized Reasoning Answers"| SYS
```

---

## ⚙️ DFD Level 1: Functional Decomposition

Level 1 explodes the central system into five core functional processes, three persistent/ephemeral data stores, and explicit data pipelines:
* **Process 1.0: Ingestion & Scraping Engine**: Fetches static HTML, dynamic Next.js JSON accordions, and streams binary PDFs.
* **Process 2.0: Preprocessing & Text Chunking**: Converts raw HTML tables to Markdown and segments documents into overlapping chunks.
* **Process 3.0: Vector Embedding & Storage Management**: Interfaces with OpenAI Embeddings and persists vectors into ChromaDB.
* **Process 4.0: Agentic ReAct Reasoning & Tool Routing**: Evaluates intent, translates queries, orchestrates tools, and evaluates observations.
* **Process 5.0: Grounding Verification & Output Formatting**: Validates retrieved evidence, prevents hallucination, appends citations, and formats responses.

```mermaid
flowchart TD
    classDef entity fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#01579b;
    classDef process fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#bf360c;
    classDef store fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,stroke-dasharray: 5 5,color:#1b5e20;

    %% External Entities
    USER["User (Student / Alumni)"]:::entity
    DIU_EXT["DIU Web Infrastructure & APIs"]:::entity
    OPENAI_API["OpenAI API Services"]:::entity

    %% Data Stores
    D1[("D1: Configuration & Secrets (.env)")]:::store
    D2[("D2: Raw Normalized Documents")]:::store
    D3[("D3: ChromaDB Vector Store (diu_knowledge_base)")]:::store

    %% Level 1 Processes
    P1["1.0<br/>Multi-Source Ingestion & Scraping Engine"]:::process
    P2["2.0<br/>Preprocessing, Markdown Normalization & Chunking"]:::process
    P3["3.0<br/>Vector Embedding & Indexing Subsystem"]:::process
    P4["4.0<br/>Agentic ReAct Reasoning & Tool Orchestration"]:::process
    P5["5.0<br/>Grounding Verification & Response Formatter"]:::process

    %% Data Flows
    D1 -.->|"OPENAI_API_KEY, Target URLs, Collection Name"| P1
    D1 -.->|"Embedding Model & Persist Path Config"| P3
    D1 -.->|"Model Hyperparameters (temp=0, gpt-4o-mini)"| P4

    DIU_EXT -->|"HTML DOM, JSON Payloads, Binary PDF Streams"| P1
    P1 -->|"Structured LangChain Document Objects [Content, Metadata]"| D2

    D2 -->|"Raw Documents Stream"| P2
    P2 -->|"Recursive Chunks (700 chars, 100 overlap)"| P3

    P3 <-->|"Chunk Texts / 1536-dim Vectors"| OPENAI_API
    P3 -->|"Persisted Vector Embeddings & Source Metadata"| D3

    USER -->|"User Query (Multilingual / Banglish)"| P4
    P4 <-->|"Prompt, ReAct Thoughts, Tool Invocations"| OPENAI_API
    
    P4 -->|"Canonical English Search Query"| D3
    D3 -->|"Top-k (k=4) Retrieved Context Chunks + URLs"| P4

    P4 -->|"Observation Context & Unformatted Reply"| P5
    P5 -->|"Grounded Response with Exact Citations"| USER
```

---

## 🔍 DFD Level 2: Detailed Sub-Process Decompositions

To provide a granular view for implementation and technical defense, the critical subsystems are decomposed below.

### DFD Level 2.1: Sub-Process 1.0 (Dynamic Ingestion & Extraction Engine)

Details how static web pages, dynamic REST endpoints, and binary attachment streams are retrieved and normalized into standardized documents.

```mermaid
flowchart TD
    classDef process fill:#fff3e0,stroke:#e65100,stroke-width:1.5px,color:#bf360c;
    classDef store fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,stroke-dasharray: 5 5,color:#1b5e20;
    classDef ext fill:#e1f5fe,stroke:#0288d1,stroke-width:1.5px,color:#01579b;

    EXT_WEB["DIU Web Servers & Backend APIs"]:::ext
    D2[("D2: Raw Normalized Documents")]:::store

    P11["1.1<br/>Target URL Dispatcher & Router"]:::process
    P12["1.2<br/>Static HTML Scraper & DOM Sanitizer<br/>(BeautifulSoup4)"]:::process
    P13["1.3<br/>Scholarship REST API Client<br/>(/accordion/scholarship)"]:::process
    P14["1.4<br/>Dynamic Noticeboard REST Client<br/>(/notice?per_page=40)"]:::process
    P15["1.5<br/>Binary PDF Attachment Streamer<br/>(Requests + io.BytesIO)"]:::process
    P16["1.6<br/>PDF In-Memory Text Parser<br/>(pypdf.PdfReader)"]:::process
    P17["1.7<br/>Document Normalizer & Metadata Tagger"]:::process

    P11 -->|"Static URLs (Alumni/Guidelines)"| P12
    P11 -->|"Scholarship Route Trigger"| P13
    P11 -->|"Noticeboard Route Trigger"| P14

    EXT_WEB <-->|"HTTP GET (Headers, DOM)"| P12
    EXT_WEB <-->|"JSON GET (Accordion Categories)"| P13
    EXT_WEB <-->|"JSON GET (Notice Metadata & Slugs)"| P14

    P14 -->|"Attachment File URLs (.pdf)"| P15
    EXT_WEB <-->|"Binary Stream GET"| P15
    P15 -->|"Memory Buffer (io.BytesIO)"| P16

    P12 -->|"Sanitized Body Text & URL"| P17
    P13 -->|"Markdown-Formatted Accordion Content"| P17
    P14 -->|"Notice Title, Category, Dept & Date"| P17
    P16 -->|"Extracted PDF Attachment Text (Pages 1-4)"| P17

    P17 -->|"Standardized Document(page_content, metadata={'source': url})"| D2
```

---

### DFD Level 2.2: Sub-Process 2.0 & 3.0 (Preprocessing, Chunking & Vector Storage)

Illustrates the transformation from raw documents to normalized Markdown tables, sliding window text chunks, OpenAI vector embeddings, and ChromaDB persistent storage.

```mermaid
flowchart TD
    classDef process fill:#fff3e0,stroke:#e65100,stroke-width:1.5px,color:#bf360c;
    classDef store fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,stroke-dasharray: 5 5,color:#1b5e20;
    classDef ext fill:#e1f5fe,stroke:#0288d1,stroke-width:1.5px,color:#01579b;

    D2[("D2: Raw Normalized Documents")]:::store
    OPENAI["OpenAI Embedding API<br/>(text-embedding-3-small)"]:::ext
    D3[("D3: ChromaDB Vector Store<br/>(./chroma_db)")]:::store

    P21["2.1<br/>HTML Table-to-Markdown Transformer"]:::process
    P22["2.2<br/>Whitespace Cleaner & Non-Ascii Normalizer"]:::process
    P23["2.3<br/>Recursive Character Text Splitter<br/>(chunk=700, overlap=100)"]:::process

    P31["3.1<br/>Batch Embedding Dispatcher"]:::process
    P32["3.2<br/>Vector Indexing & Collection Writer<br/>(collection: diu_knowledge_base)"]:::process
    P33["3.3<br/>Persistent SQLite/HNSW Cache Sync"]:::process

    D2 -->|"Raw Ingested Documents"| P21
    P21 -->|"Documents with Clean Markdown Tables"| P22
    P22 -->|"Cleaned Document Stream"| P23
    P23 -->|"Document Chunks + Metadata"| P31

    P31 <-->|"Batched Chunks / 1536-dim Dense Vectors"| OPENAI
    P31 -->|"Vector-Document Tuples"| P32
    P32 -->|"Collection Additions"| P33
    P33 -->|"HNSW Index & Document Metadatas"| D3
```

---

### DFD Level 2.3: Sub-Process 4.0 & 5.0 (Agentic ReAct Reasoning & Grounding)

Details the runtime decision cycle: intent evaluation, cross-lingual translation, tool retrieval from ChromaDB, evidence inspection, anti-hallucination check, and response synthesis.

```mermaid
flowchart TD
    classDef process fill:#fff3e0,stroke:#e65100,stroke-width:1.5px,color:#bf360c;
    classDef store fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,stroke-dasharray: 5 5,color:#1b5e20;
    classDef ext fill:#e1f5fe,stroke:#0288d1,stroke-width:1.5px,color:#01579b;

    USER["User Query"]:::ext
    LLM["OpenAI gpt-4o-mini (temp=0)"]:::ext
    D3[("D3: ChromaDB Vector Store")]:::store
    CLIENT["Final Grounded Reply to User"]:::ext

    P41["4.1<br/>Query Parsing & Conversational State Assembly"]:::process
    P42["4.2<br/>Intent & Language Assessment<br/>(Banglish / Bengali / English)"]:::process
    P43["4.3<br/>Canonical English Search Formulator"]:::process
    P44["4.4<br/>Tool Invocation Dispatcher<br/>(search_diu_knowledge_base)"]:::process
    P45["4.5<br/>Vector Similarity Search Executor<br/>(k=4 Nearest Neighbors)"]:::process
    P46["4.6<br/>Observation Synthesizer & State Updater"]:::process

    P51["5.1<br/>Observation Evidence & Factual Verification"]:::process
    P52["5.2<br/>Anti-Hallucination Guardrail Check"]:::process
    P53["5.3<br/>Source URL & Metadata Extractor"]:::process
    P54["5.4<br/>Polite English Markdown Response Builder"]:::process
    P55["5.5<br/>Missing Record Fallback Handler"]:::process

    USER -->|"Raw Query"| P41
    P41 -->|"State Messages [('user', query)]"| P42
    P42 <-->|"System Prompt + Query / Needs Search?"| LLM

    P42 -->|"Needs Institutional Knowledge"| P43
    P43 -->|"Canonical Search Term (e.g. 'alumni card fee')"| P44
    P44 -->|"Function Call: search_diu_knowledge_base(query)"| P45

    P45 <-->|"Similarity Search (k=4)"| D3
    P45 -->|"Top-4 Documents with Metadata Sources"| P46
    P46 -->|"Formatted Observation Stream"| P51

    P51 <-->|"ReAct Evaluation (Observation vs Query)"| LLM
    P51 -->|"Candidate Factual Synthesis"| P52

    P52 -->|"Facts Verified in Retrieved Context"| P53
    P53 -->|"Verified Data + Source URLs"| P54
    P54 --> CLIENT

    P52 -->|"Requested Info Not Found in Sources"| P55
    P55 -->|"Polite Out-of-Domain / Missing Record Message"| CLIENT
```

---

## 📊 Data Flow & Transformation Catalog

| Data Flow Identifier | Name | Origin Process / Entity | Destination Process / Store | Data Structure & Type |
| :--- | :--- | :--- | :--- | :--- |
| **DF-01** | Raw Query | User | Process 4.1 | UTF-8 String (Banglish, Bengali, or English) |
| **DF-02** | Target Routes | Config (.env) | Process 1.1 | `List[str]` (Static & Dynamic URLs) |
| **DF-03** | Dynamic API Data | DIU Backend | Process 1.3 / 1.4 | JSON Object (`categories`, `accordions`, `notices`) |
| **DF-04** | PDF Binary Stream | Notice CDN | Process 1.5 | HTTP Binary Stream (`io.BytesIO`) |
| **DF-05** | Normalized Docs | Process 1.7 | Store D2 | `List[Document(page_content, metadata)]` |
| **DF-06** | Text Chunks | Process 2.3 | Process 3.1 | `List[Document]` (Max 700 chars, 100 overlap) |
| **DF-07** | Vector Embeddings | OpenAI API | Process 3.2 | Array of 1536 Float32 values |
| **DF-08** | Persisted Vectors | Process 3.3 | Store D3 | ChromaDB SQLite/HNSW Persistent Collection |
| **DF-09** | Canonical Search Query | Process 4.3 | Process 4.5 | Normalized English keyword string |
| **DF-10** | Retrieved Context | Store D3 | Process 4.6 | `List[Document]` (Top 4 chunks + URL metadatas) |
| **DF-11** | Observation Payload | Process 4.6 | Process 5.1 | String formatted with `[Source: URL]\n<Content>` |
| **DF-12** | Grounded Response | Process 5.4 / 5.5 | User | Markdown text with exact URL source citations |
