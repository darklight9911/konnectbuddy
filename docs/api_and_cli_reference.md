# API & CLI Reference

This document provides a comprehensive technical reference for all functions, tools, configuration constants, and CLI flags in `agentic_rag.py`.

---

## ⚙️ Configuration Constants

```python
TARGET_URLS = [
    "https://daffodilvarsity.edu.bd/noticeboard",
    "https://alumni.daffodilvarsity.edu.bd/articles/membership-guidelines-28",
    "https://alumni.daffodilvarsity.edu.bd/",
    "https://daffodilvarsity.edu.bd/scholarship/diu-scholarship"
]

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
COLLECTION_NAME = "diu_knowledge_base"
```

| Constant | Type | Description |
| :--- | :--- | :--- |
| `TARGET_URLS` | `list[str]` | The official DIU website endpoints scraped during index creation. |
| `DB_DIR` | `str` | Absolute path to the local directory where ChromaDB stores persistent SQLite and index binary files. |
| `COLLECTION_NAME` | `str` | The Chroma vector collection name (`"diu_knowledge_base"`). |

---

## 🛠️ CLI Interface Reference

The script is invoked via command line using standard POSIX flags:

```bash
python agentic_rag.py [-h] [--query QUERY] [--interactive] [--reindex] [--in-memory]
```

### Argument Flags

| Flag | Short | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `--query` | `-q` | `str` | `None` | Executes a single prompt through KonnectBuddy and prints the response. |
| `--interactive` | `-i` | `flag` | `False` | Initiates an interactive REPL chat session with KonnectBuddy. |
| `--reindex` | | `flag` | `False` | Forces a fresh scrape of all `TARGET_URLS` and re-indexes into ChromaDB. |
| `--in-memory` | | `flag` | `False` | Disables disk persistence and creates an ephemeral vector index in RAM. |
| `--help` | `-h` | `flag` | | Displays standard help text and exits. |

---

## 📚 Core Function Reference

### `fetch_dynamic_scholarships`

```python
def fetch_dynamic_scholarships(source_url: str, headers: dict) -> list[Document]
```

Fetches scholarship categories and accordion policies from DIU's backend API, resolving Next.js client-side dynamic rendering where static HTML is empty.

* **Parameters**:
  * `source_url` (`str`): The canonical public scholarship URL (used in document metadata for citation).
  * `headers` (`dict`): HTTP request headers, including custom `User-Agent`.
* **Returns**:
  * `list[Document]`: A list of LangChain `Document` objects. Each document contains category metadata, accordion titles, and markdown-formatted tables.
* **Exceptions Handled**:
  * Catches `requests.RequestException` and logs errors without crashing the pipeline.

---

### `fetch_dynamic_notices`

```python
def fetch_dynamic_notices(source_url: str, headers: dict) -> list[Document]
```

Fetches the latest 40 notices from the DIU backend REST API, extracts text from attached binary PDF files using `pypdf`, and formats individual notice documents.

* **Parameters**:
  * `source_url` (`str`): Base noticeboard URL (e.g. `https://daffodilvarsity.edu.bd/noticeboard`).
  * `headers` (`dict`): HTTP headers including `User-Agent`.
* **Returns**:
  * `list[Document]`: A list of `Document` objects containing notice titles, departments, published dates, attachment links, extracted PDF text, and individual notice slug URLs (`source_url/slug`).
* **PDF Extraction Mechanics**:
  * Downloads PDF streams into `io.BytesIO`.
  * Extracts up to the first 4 pages per attached file.
  * Silences `pypdf` internal logging to prevent console pollution.

---

### `scrape_pages`

```python
def scrape_pages(urls: list[str]) -> list[Document]
```

Main scraping orchestrator that iterates over the supplied URLs, strips unwanted HTML DOM nodes, and delegates to dynamic extractors when required.

* **Parameters**:
  * `urls` (`list[str]`): List of target web page URLs to scrape.
* **Returns**:
  * `list[Document]`: Aggregated list of all extracted documents across static HTML, dynamic scholarship accordions, and dynamic notices with PDFs.
* **DOM Cleanup Rules**:
  * Decomposes `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`, and `<noscript>` elements using `BeautifulSoup`.

---

### `get_vector_store`

```python
def get_vector_store(force_reindex: bool = False, in_memory: bool = False) -> Chroma
```

Initializes, loads, or rebuilds the ChromaDB vector database.

* **Parameters**:
  * `force_reindex` (`bool`, default=`False`): If `True`, triggers `scrape_pages()` and rebuilds the collection regardless of existing disk caches.
  * `in_memory` (`bool`, default=`False`): If `True`, creates an ephemeral Chroma instance without writing to `./chroma_db`.
* **Returns**:
  * `Chroma`: An initialized LangChain Chroma vector store configured with `text-embedding-3-small`.
* **Chunking Configuration**:
  * `RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)`.

---

### `build_agent`

```python
def build_agent(vector_store: Chroma)
```

Constructs the ReAct agent graph with the retrieval tool and system instructions.

* **Parameters**:
  * `vector_store` (`Chroma`): The initialized vector database instance to bind to the tool.
* **Returns**:
  * `CompiledGraph` or `AgentExecutor`: A callable agent object supporting `.invoke({"messages": [...]})`.
* **Model Configuration**:
  * `ChatOpenAI(model="gpt-4o-mini", temperature=0)`.
* **Dual Runtime Fallback**:
  * Tries `langchain.agents.create_agent`.
  * Falls back to `langgraph.prebuilt.create_react_agent` with both `prompt` and `state_modifier` compatibility.

---

### `@tool search_diu_knowledge_base`

```python
@tool
def search_diu_knowledge_base(query: str) -> str
```

LangChain tool exposed to the ReAct agent for semantic knowledge retrieval.

* **Parameters**:
  * `query` (`str`): Semantic search query formulated by the agent.
* **Returns**:
  * `str`: Formatted string containing up to 4 retrieved chunks separated by `---`, with source metadata formatted as `[Source: <url>]`. Returns a fallback notice if no chunks match.

---

### `ask_konnectbuddy`

```python
def ask_konnectbuddy(agent, user_query: str) -> str
```

Helper function that formats the user query into the agent state message list, triggers execution, prints formatted logs, and returns the final response string.

* **Parameters**:
  * `agent`: The compiled agent instance returned by `build_agent()`.
  * `user_query` (`str`): The raw user prompt (in Bengali, Banglish, or English).
* **Returns**:
  * `str`: The final generated response text.
