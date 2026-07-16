"""Shared list pagination defaults and hard caps (Phase 6.4).

All list endpoints must use these helpers (or the same numeric bounds) so
clients cannot request unbounded result sets.

Use as::

    limit: LimitParam = DEFAULT_LIMIT
    page: PageParam = DEFAULT_PAGE
    per_page: PerPageParam = DEFAULT_PER_PAGE

Defaults belong on the parameter (``=``), not inside ``Query()`` when using
``Annotated``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Query

DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100

DEFAULT_LIMIT = 50
MAX_LIMIT = 100
# Support / audit surfaces may page slightly larger slices
MAX_ADMIN_LIMIT = 200

PageParam = Annotated[
    int,
    Query(ge=1, description="1-based page index"),
]
PerPageParam = Annotated[
    int,
    Query(ge=1, le=MAX_PER_PAGE, description=f"Page size (max {MAX_PER_PAGE})"),
]
LimitParam = Annotated[
    int,
    Query(ge=1, le=MAX_LIMIT, description=f"Max rows to return (max {MAX_LIMIT})"),
]
AdminLimitParam = Annotated[
    int,
    Query(
        ge=1,
        le=MAX_ADMIN_LIMIT,
        description=f"Max rows for admin/audit lists (max {MAX_ADMIN_LIMIT})",
    ),
]


def page_offset(page: int, per_page: int) -> int:
    return max(0, (page - 1) * per_page)
