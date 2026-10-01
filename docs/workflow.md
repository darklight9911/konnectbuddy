# Agent & System Workflows

This document outlines the operational workflows of **DIU Konnect (KonnectBuddy)** through detailed descriptions and professional Mermaid diagrams.

---

## 🔄 Lifecycle Overview

The DIU Konnect architecture operates across two primary operational lifecycles:
1. **Ingestion & Indexing Lifecycle (Offline / Setup Phase)**: Gathers, sanitizes, chunks, embeds, and stores verified institutional knowledge.
2. **Agentic ReAct Inference Lifecycle (Runtime Phase)**: Receives user queries across multilingual inputs, reasons over intent, queries the vector database using canonical terms, verifies retrieved evidence, and generates grounded responses.

---

## 1. Ingestion & Indexing Pipeline

The data ingestion workflow captures both static HTML and dynamic client-side content (Next.js backend APIs and binary notice PDFs) into ChromaDB.

```mermaid
sequenceDiagram
    autonumber
    participant Main as CLI / Main Engine
    participant VS as VectorStore Manager
    participant Scraper as Scraper & API Client
    participant PDF as PyPDF Reader
    participant Splitter as Text Splitter
    participant Embed as OpenAI Embeddings
    participant Chroma as ChromaDB Index

    Main->>VS: get_vector_store(force_reindex, in_memory)
    alt Cached Index exists and force_reindex is False
        VS->>Chroma: Load persisted collection ("diu_knowledge_base")
        Chroma-->>VS: Initialized VectorStore
        VS-->>Main: Return Chroma instance
    else Build Index from scratch / force_reindex is True
        VS->>Scraper: scrape_pages(TARGET_URLS)
        loop Each Target URL
            Scraper->>Scraper: Fetch HTML & decompose scripts/nav/footer
            opt If URL contains "scholarship"
                Scraper->>Scraper: Call REST API (/accordion/scholarship)
                Scraper->>Scraper: Parse tables into Markdown
            end
            opt If URL contains "noticeboard"
                Scraper->>Scraper: Call REST API (/notice?per_page=40)
                loop Each Notice Attachment
                    Scraper->>PDF: Download binary PDF & extract text (pages 1-4)
                    PDF-->>Scraper: Extracted text
                end
            end
        end
        Scraper-->>VS: Raw Documents List [Document(content, metadata)]
        VS->>Splitter: split_documents(raw_docs, chunk=700, overlap=100)
        Splitter-->>VS: Chunks List
        VS->>Embed: Embed Chunks (text-embedding-3-small)
        Embed-->>VS: Vector Embeddings
        VS->>Chroma: Chroma.from_documents(chunks, embeddings, persist_dir)
        Chroma-->>VS: Persisted Index
        VS-->>Main: Return Chroma instance
    end
```

---

## 2. Agentic ReAct Inference Lifecycle

The inference pipeline follows the **ReAct (Reason + Act)** paradigm. The agent dynamically decides whether external retrieval is required, constructs a targeted search string, analyzes retrieved context, and synthesizes a verified answer.

```mermaid
flowchart TD
    Start(["User Input (CLI / Interactive / Notebook)"]) --> InitAgent["Initialize Agent State (Conversation History + User Message)"]
    InitAgent --> LLMReason["LLM Reasoning Step (gpt-4o-mini | temp=0)<br/>System Prompt: Act as KonnectBuddy"]
    
    LLMReason --> Decision{"Does answering require<br/>DIU Official Knowledge?"}
    
    Decision -- "Yes: Generate Action" --> GenAction["Formulate Tool Call: search_diu_knowledge_base<br/>Canonical English query translated from user language"]
    Decision -- "No: Synthesize Direct Response" --> FormReply["Formulate Polite English Response"]
    
    GenAction --> ExecTool["Execute Tool: search_diu_knowledge_base(query)"]
    ExecTool --> VectorSearch["ChromaDB Similarity Search (k=4)<br/>Distance Metric: Cosine Similarity"]
    
    VectorSearch --> HasResults{"Were matching<br/>records found?"}
    
    HasResults -- "Yes" --> FormatDocs["Format Records with Source Metadata:<br/>[Source: URL] + Content Chunks"]
    HasResults -- "No" --> NoRecords["Return: 'No relevant records found in verified sources'"]
    
    FormatDocs --> ReturnObs["Feed Observation back into Agent State"]
    NoRecords --> ReturnObs
    
    ReturnObs --> SynthesizeReason["LLM Second Reasoning Step:<br/>Evaluate Observation against User Query"]
    
    SynthesizeReason --> GroundingCheck{"Is fact strictly present in context?"}
    
    GroundingCheck -- "Yes" --> BuildAnswer["Synthesize structured English response<br/>(Markdown tables / lists + Exact Source Citation)"]
    GroundingCheck -- "No / Absent" --> PoliteFallback["Politely inform user data is not in official records<br/>Suggest relevant DIU office/desk to contact"]
    
    BuildAnswer --> Output(["Deliver Final Reply to User"])
    PoliteFallback --> Output
    FormReply --> Output

    classDef proc fill:#e3f2fd,stroke:#1565c0,stroke-width:1px,color:#0d47a1;
    classDef dec fill:#fff8e1,stroke:#f57f17,stroke-width:1px,color:#e65100;
    classDef term fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    
    class InitAgent,LLMReason,GenAction,ExecTool,VectorSearch,FormatDocs,NoRecords,ReturnObs,SynthesizeReason,BuildAnswer,PoliteFallback,FormReply proc;
    class Decision,HasResults,GroundingCheck dec;
    class Start,Output term;
```

---

## 3. Agent State Machine

The following state machine details the internal states of the ReAct agent graph during an execution turn:

```mermaid
stateDiagram-v2
    [*] --> Idle: Awaiting User Input
    Idle --> ProcessingInput: Receive Query (Bengali / Banglish / English)
    
    state ProcessingInput {
        [*] --> IngestMessage
        IngestMessage --> AppendToState: Update messages list
    }

    ProcessingInput --> Reasoning: Invoke Model (gpt-4o-mini)
    
    state Reasoning {
        [*] --> EvaluateIntent
        EvaluateIntent --> PlanAction: Requires External Retrieval
        EvaluateIntent --> PlanDirectResponse: Self-contained Query
    }

    Reasoning --> ExecutingTool: Action Generated (search_diu_knowledge_base)
    Reasoning --> Responding: Direct Response Generated

    state ExecutingTool {
        [*] --> TranslateQuery: Formulate Canonical English Keywords
        TranslateQuery --> QueryVectorDB: Query ChromaDB (k=4)
        QueryVectorDB --> FormatObservations: Collate [Source: URL] + Chunks
    }

    ExecutingTool --> EvaluatingObservation: Feed Observations to Model

    state EvaluatingObservation {
        [*] --> CheckGrounding: Verify factual presence in context
        CheckGrounding --> ValidateCitations: Extract verified source URLs
    }

    EvaluatingObservation --> Responding: Observations Sufficient
    EvaluatingObservation --> Reasoning: Additional Retrieval Required (Iterate)

    state Responding {
        [*] --> StructureMarkdown: Format bullet points & tables
        StructureMarkdown --> AppendCitation: Attach official source URLs
        AppendCitation --> PolitenessFilter: Ensure courteous tone
    }

    Responding --> Idle: Output Delivered to User
```

---

## 4. Cross-Lingual Query Resolution Sequence

A core design feature of DIU Konnect is bridging colloquial Banglish / Bengali queries with canonical English institutional documents in the vector store.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Agent as KonnectBuddy ReAct Agent
    participant Tool as search_diu_knowledge_base
    participant VectorStore as ChromaDB Vector Store
    
    User->>Agent: "@konnectbuddy kivabe alumni card collect korte hobe?"
    Note over Agent: Detects Banglish query regarding Alumni Card collection & fee
    Note over Agent: System prompt mandates: "Formulate internal tool search queries in precise, canonical English terms"
    Agent->>Tool: search_diu_knowledge_base("alumni card collection procedure fee")
    Tool->>VectorStore: similarity_search("alumni card collection procedure fee", k=4)
    VectorStore-->>Tool: Top 4 chunks from /articles/membership-guidelines-28
    Tool-->>Agent: Observation with Source Metadata & Fee Details (200 BDT + 300 BDT)
    Note over Agent: System prompt mandates: "Rely solely on retrieved tool output; response in clear, professional English"
    Agent->>User: "To collect your DIU Alumni Card, please follow these official procedures... Fees: ... Source: https://alumni.daffodilvarsity.edu.bd/articles/membership-guidelines-28"
```

---

## 5. Hallucination Mitigation & Grounding Decision Tree

To ensure zero hallucinations in high-stakes university guidance (fees, graduation requirements, scholarships), the agent implements the following decision path:

```mermaid
flowchart TD
    Q["User Prompt Received"] --> S["Vector Search Executed"]
    S --> R{"Retrieved Chunks Similarity Score & Content"}
    
    R -- "High Relevance & Direct Match" --> V1["Verify Explicit Figures (e.g. fees, percentages, dates)"]
    V1 --> G1["Synthesize Response using ONLY stated facts"]
    G1 --> C1["Cite exact source URL from metadata"]
    C1 --> Out1["Deliver Grounded Response"]
    
    R -- "Partial Relevance (Topic found, specific detail omitted)" --> V2["Identify Knowledge Boundary"]
    V2 --> G2["Explain verified facts, explicitly state the requested detail is not specified"]
    G2 --> C2["Cite official category source URL + recommend relevant office (e.g., Financial Aid Office)"]
    C2 --> Out2["Deliver Clarified Response"]
    
    R -- "Zero Relevance / Empty Chunks" --> V3["Trigger Safe Fallback Response"]
    V3 --> G3["State: 'Information not available in verified DIU records'"]
    G3 --> C3["Provide DIU general contact guidance"]
    C3 --> Out3["Deliver Courteous Redirection"]

    classDef pass fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20;
    classDef warn fill:#fff8e1,stroke:#f57f17,color:#e65100;
    classDef fail fill:#ffebee,stroke:#c62828,color:#b71c1c;

    class V1,G1,C1,Out1 pass;
    class V2,G2,C2,Out2 warn;
    class V3,G3,C3,Out3 fail;
```
