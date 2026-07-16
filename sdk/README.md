# raginspector

Instrument your RAG pipeline in 3 lines of code. Find hallucinations and retrieval failures automatically.

## Install

```bash
pip install raginspector
```

## Usage

```python
from raginspector import RAGInspector

inspector = RAGInspector(
    api_key="ri-your-key",
    pipeline_name="my-rag-app",
    base_url="http://localhost:8000",
)

@inspector.trace_retrieval
def retrieve(query: str) -> list[dict]:
    return your_vector_db.search(query, k=5)

@inspector.trace_generation
def generate(query: str, context: list[dict]) -> str:
    return your_llm.complete(query, context)
```

The SDK sends traces asynchronously — it never blocks your application.

## Framework adapters

### LangChain

```python
from raginspector.langchain import RAGInspectorCallbackHandler
```

### LlamaIndex

```python
from raginspector.llamaindex import RAGInspectorLlamaIndexHandler

handler = RAGInspectorLlamaIndexHandler(api_key="ri-...", pipeline_name="li-rag")
# Register with your LlamaIndex callback manager
```

### Haystack

```python
from raginspector.haystack import RAGInspectorHaystackTracer

tracer = RAGInspectorHaystackTracer(api_key="ri-...", pipeline_name="hs-rag")
result = tracer.run(query="...", documents=[...], answer="...")
```
