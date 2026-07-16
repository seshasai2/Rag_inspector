"""IP allowlist enforcement for organizations that configured CIDR entries."""

from __future__ import annotations

import ipaddress
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import IPAllowlistEntry


def client_ip_from_headers(
    *,
    x_forwarded_for: Optional[str],
    x_real_ip: Optional[str],
    peer: Optional[str],
) -> Optional[str]:
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    if x_real_ip:
        return x_real_ip.strip()
    return peer


def ip_allowed(client_ip: str, cidrs: list[str]) -> bool:
    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    for cidr in cidrs:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            continue
        if addr in network:
            return True
    return False


async def organization_allowlist_cidrs(db: AsyncSession, organization_id: str) -> list[str]:
    result = await db.execute(
        select(IPAllowlistEntry.cidr).where(IPAllowlistEntry.organization_id == organization_id)
    )
    return [row[0] for row in result.all()]


async def enforce_org_ip_allowlist(
    db: AsyncSession,
    *,
    organization_id: Optional[str],
    client_ip: Optional[str],
) -> bool:
    """Return True if request is allowed. Empty allowlist = allow all."""
    if not organization_id:
        return True
    cidrs = await organization_allowlist_cidrs(db, organization_id)
    if not cidrs:
        return True
    if not client_ip:
        return False
    return ip_allowed(client_ip, cidrs)
