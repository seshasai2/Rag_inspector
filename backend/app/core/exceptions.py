"""
Domain exceptions for RAGInspector.
"""

from __future__ import annotations

from typing import Any, Optional


class BaseRAGInspectorError(Exception):
    """Base error with message, stable code, and optional details."""

    code: str = "raginspector_error"

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.details: dict[str, Any] = details or {}

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "code": self.code,
            "details": self.details,
        }


class ValidationError(BaseRAGInspectorError):
    code = "validation_error"


class RetrievalError(BaseRAGInspectorError):
    code = "retrieval_error"


class EmbeddingError(BaseRAGInspectorError):
    code = "embedding_error"


class GroundingError(BaseRAGInspectorError):
    code = "grounding_error"


class EvaluationError(BaseRAGInspectorError):
    code = "evaluation_error"


class PipelineError(BaseRAGInspectorError):
    code = "pipeline_error"


class ProviderError(BaseRAGInspectorError):
    code = "provider_error"


class DatabaseError(BaseRAGInspectorError):
    code = "database_error"


class WorkerError(BaseRAGInspectorError):
    code = "worker_error"


class ConfigurationError(BaseRAGInspectorError):
    code = "configuration_error"


class NetworkError(BaseRAGInspectorError):
    code = "network_error"


class AppTimeoutError(BaseRAGInspectorError):
    """Application timeout (does not shadow builtin TimeoutError)."""

    code = "timeout_error"
