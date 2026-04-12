import secrets
import string
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from async_database import get_db
from auth.dependencies import get_current_user
from models.tracking.models import Shipment, ShipmentStatusHistory
from models.tracking.choices import ShipmentStatus
from models.users.models import User
from models.users.choices import UserRole
from schemas.tracking.schemas import (
    ShipmentCreateSchema,
    ShipmentPatchSchema,
    ShipmentReadSchema,
    ShipmentStatusHistoryReadSchema,
)

tracking_router = APIRouter(prefix="/tracking", tags=["tracking"])


def _parse_user_id(user_id: str | int) -> int:
    return int(user_id)


async def _get_user(db: AsyncSession, uid: int) -> Optional[User]:
    r = await db.execute(select(User).where(User.id == uid))
    return r.scalars().first()


async def _generate_tracking_number(db: AsyncSession) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(12):
        candidate = "TRK-" + "".join(secrets.choice(alphabet) for _ in range(10))
        exists = await db.execute(
            select(Shipment.id).where(Shipment.tracking_number == candidate)
        )
        if exists.scalars().first() is None:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not allocate tracking number",
    )


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


async def _get_shipment(db: AsyncSession, shipment_id: int) -> Optional[Shipment]:
    r = await db.execute(
        select(Shipment)
        .options(selectinload(Shipment.status_history))
        .where(Shipment.id == shipment_id)
    )
    return r.scalars().first()


def _can_access_shipment(user: User, shipment: Shipment) -> bool:
    if _is_admin(user):
        return True
    if shipment.carrier_id == user.id or shipment.driver_id == user.id:
        return True
    return False


@tracking_router.get("/", status_code=status.HTTP_200_OK)
async def tracking_root(user_id: str = Depends(get_current_user)):
    _parse_user_id(user_id)
    return {"message": "Tracking API — use /tracking/shipments"}


@tracking_router.get("/shipments", response_model=list[ShipmentReadSchema])
async def list_shipments(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = _parse_user_id(user_id)
    me = await _get_user(db, uid)
    if me is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if _is_admin(me):
        q = select(Shipment).order_by(Shipment.created_at.desc())
    else:
        q = (
            select(Shipment)
            .where(or_(Shipment.carrier_id == uid, Shipment.driver_id == uid))
            .order_by(Shipment.created_at.desc())
        )
    r = await db.execute(q)
    return list(r.scalars().all())


@tracking_router.post(
    "/shipments",
    response_model=ShipmentReadSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_shipment(
    body: ShipmentCreateSchema,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = _parse_user_id(user_id)
    me = await _get_user(db, uid)
    if me is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    tracking_number = body.tracking_number
    if tracking_number:
        taken = await db.execute(
            select(Shipment.id).where(Shipment.tracking_number == tracking_number)
        )
        if taken.scalars().first() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tracking number already in use",
            )
    else:
        tracking_number = await _generate_tracking_number(db)

    if body.driver_id is not None:
        driver = await _get_user(db, body.driver_id)
        if driver is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Driver user not found",
            )
    shipment = Shipment(
        tracking_number=tracking_number,
        title=body.title,
        description=body.description,
        origin=body.origin,
        destination=body.destination,
        carrier_id=uid,
        driver_id=body.driver_id,
        status=ShipmentStatus.CREATED,
    )
    db.add(shipment)
    await db.flush()

    db.add(
        ShipmentStatusHistory(
            shipment_id=shipment.id,
            old_status=None,
            new_status=ShipmentStatus.CREATED,
            changed_by_id=uid,
            note="Shipment created",
        )
    )
    await db.commit()
    await db.refresh(shipment)
    return shipment


@tracking_router.get("/shipments/{shipment_id}", response_model=ShipmentReadSchema)
async def get_shipment(
    shipment_id: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = _parse_user_id(user_id)
    me = await _get_user(db, uid)
    if me is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    shipment = await _get_shipment(db, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    if not _can_access_shipment(me, shipment):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    return shipment


@tracking_router.patch("/shipments/{shipment_id}", response_model=ShipmentReadSchema)
async def patch_shipment(
    shipment_id: int,
    body: ShipmentPatchSchema,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = _parse_user_id(user_id)
    me = await _get_user(db, uid)
    if me is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    shipment = await _get_shipment(db, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    if not _can_access_shipment(me, shipment):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    data = body.model_dump(exclude_unset=True)
    status_change_note = data.pop("status_change_note", None)
    new_status = data.pop("status", None)

    if "driver_id" in data and data["driver_id"] is not None:
        driver = await _get_user(db, data["driver_id"])
        if driver is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Driver user not found",
            )

    for key, value in data.items():
        setattr(shipment, key, value)

    if new_status is not None and new_status != shipment.status:
        db.add(
            ShipmentStatusHistory(
                shipment_id=shipment.id,
                old_status=shipment.status,
                new_status=new_status,
                changed_by_id=uid,
                note=status_change_note,
            )
        )
        shipment.status = new_status

    await db.commit()
    await db.refresh(shipment)
    return shipment


@tracking_router.delete("/shipments/{shipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shipment(
    shipment_id: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = _parse_user_id(user_id)
    me = await _get_user(db, uid)
    if me is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    shipment = await _get_shipment(db, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")

    if not (_is_admin(me) or shipment.carrier_id == uid):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    await db.delete(shipment)
    await db.commit()


@tracking_router.get(
    "/shipments/{shipment_id}/history",
    response_model=list[ShipmentStatusHistoryReadSchema],
)
async def get_shipment_history(
    shipment_id: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = _parse_user_id(user_id)
    me = await _get_user(db, uid)
    if me is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    shipment = await _get_shipment(db, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    if not _can_access_shipment(me, shipment):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    r = await db.execute(
        select(ShipmentStatusHistory)
        .where(ShipmentStatusHistory.shipment_id == shipment_id)
        .order_by(ShipmentStatusHistory.created_at.asc())
    )
    return list(r.scalars().all())
