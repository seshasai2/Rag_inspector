"""
RAGInspector Python SDK
Instrument your RAG pipeline in 3 lines of code.

Usage:
    from raginspector import RAGInspector
    inspector = RAGInspector(api_key="ri-...", pipeline_name="my-rag")

    @inspector.trace_retrieval
    def retrieve(query: str) -> list[dict]:
        return vector_db.search(query, k=5)

    @inspector.trace_generation
    def generate(query: str, context: list[dict]) -> str:
        return llm.complete(f"Context: {context}\\n\\nQuestion: {query}")
"""

from raginspector.tracer import RAGInspector

__all__ = ["RAGInspector"]

try:
    from raginspector.langchain import RAGInspectorCallbackHandler

    __all__.append("RAGInspectorCallbackHandler")
except ImportError:  # pragma: no cover
    pass

try:
    from raginspector.llamaindex import RAGInspectorLlamaIndexHandler

    __all__.append("RAGInspectorLlamaIndexHandler")
except ImportError:  # pragma: no cover
    pass

try:
    from raginspector.haystack import RAGInspectorHaystackTracer

    __all__.append("RAGInspectorHaystackTracer")
except ImportError:  # pragma: no cover
    pass

__version__ = "1.0.0"
