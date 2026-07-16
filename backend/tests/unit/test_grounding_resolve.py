"""Unit tests for grounding chunk resolution helpers (mirrors frontend logic)."""


def resolve_supporting_chunk(sentence: dict, chunks: list[dict]) -> dict | None:
    """Match GroundingAttribution resolveSupportingChunk."""
    key = sentence.get("supporting_chunk_id")
    if not key:
        return None
    for c in chunks:
        if c.get("chunk_id") == key or c.get("id") == key:
            return c
    return None


def test_resolve_by_chunk_id():
    sentence = {"supporting_chunk_id": "doc-1#0", "is_grounded": True}
    chunks = [
        {"id": "uuid-a", "chunk_id": "doc-2#0", "chunk_text": "no"},
        {"id": "uuid-b", "chunk_id": "doc-1#0", "chunk_text": "yes"},
    ]
    assert resolve_supporting_chunk(sentence, chunks)["chunk_text"] == "yes"


def test_resolve_by_db_id():
    sentence = {"supporting_chunk_id": "uuid-b", "is_grounded": True}
    chunks = [
        {"id": "uuid-b", "chunk_id": "doc-1#0", "chunk_text": "matched"},
    ]
    assert resolve_supporting_chunk(sentence, chunks)["chunk_text"] == "matched"


def test_resolve_missing_returns_none():
    assert resolve_supporting_chunk({"supporting_chunk_id": "missing"}, []) is None
    assert resolve_supporting_chunk({}, [{"id": "1", "chunk_id": "x"}]) is None
