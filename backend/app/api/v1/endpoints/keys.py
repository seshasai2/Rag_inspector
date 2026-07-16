import json
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.pagination import DEFAULT_LIMIT, LimitParam
from app.core.security import generate_api_key, get_key_prefix
from app.db.session import get_db
from app.models.models import APIKey, User
from app.schemas.schemas import APIKeyCreate, APIKeyCreated, APIKeyOut
from app.services.audit import AuditAction, record_audit

router = APIRouter()


@router.get("", response_model=List[APIKeyOut])
async def list_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: LimitParam = DEFAULT_LIMIT,
):
    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == current_user.id, APIKey.is_active == True)
        .order_by(APIKey.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("", response_model=APIKeyCreated, status_code=201)
async def create_key(
    payload: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    raw_key, hashed = generate_api_key()
    key = APIKey(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        key_hash=hashed,
        key_prefix=get_key_prefix(raw_key),
        name=payload.name,
        scopes=json.dumps(payload.scopes),
    )
    db.add(key)
    await record_audit(
        db,
        current_user,
        AuditAction.API_KEY_CREATED,
        "api_key",
        key.id,
        {"name": payload.name},
    )
    await db.commit()
    await db.refresh(key)
    return APIKeyCreated(
        id=key.id,
        name=key.name,
        key_prefix=key.key_prefix,
        last_used_at=key.last_used_at,
        is_active=key.is_active,
        created_at=key.created_at,
        raw_key=raw_key,
    )


@router.post("/{key_id}/rotate", response_model=APIKeyCreated)
async def rotate_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an existing key and issue a replacement with the same name/scopes."""
    key_id_str = str(key_id)
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id_str, APIKey.user_id == current_user.id)
    )
    old = result.scalar_one_or_none()
    if not old or not old.is_active:
        raise HTTPException(status_code=404, detail="API key not found")

    old.is_active = False
    raw_key, hashed = generate_api_key()
    new_key = APIKey(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        key_hash=hashed,
        key_prefix=get_key_prefix(raw_key),
        name=old.name,
        scopes=old.scopes,
    )
    db.add(new_key)
    await record_audit(
        db,
        current_user,
        AuditAction.API_KEY_ROTATED,
        "api_key",
        new_key.id,
        {"revoked_key_id": old.id, "name": old.name},
    )
    await db.commit()
    await db.refresh(new_key)
    return APIKeyCreated(
        id=new_key.id,
        name=new_key.name,
        key_prefix=new_key.key_prefix,
        last_used_at=new_key.last_used_at,
        is_active=new_key.is_active,
        created_at=new_key.created_at,
        raw_key=raw_key,
    )


@router.delete("/{key_id}", status_code=204)
async def revoke_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    key_id_str = str(key_id)
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id_str, APIKey.user_id == current_user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    await record_audit(db, current_user, AuditAction.API_KEY_REVOKED, "api_key", key.id)
    await db.commit()
