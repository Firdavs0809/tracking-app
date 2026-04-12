from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from models.tracking.choices import ShipmentStatus


class ShipmentCreateSchema(BaseModel):
    """Create shipment; current user becomes carrier."""

    tracking_number: Optional[str] = Field(
        None,
        max_length=64,
        description="Unique tracking id; auto-generated if omitted",
    )
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    origin: str = Field(..., min_length=1, max_length=255)
    destination: str = Field(..., min_length=1, max_length=255)
    driver_id: Optional[int] = Field(None, description="Optional assigned driver user id")


class ShipmentPatchSchema(BaseModel):
    """Partial update; if status changes, history is recorded when status_change_note is used with status."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    origin: Optional[str] = Field(None, min_length=1, max_length=255)
    destination: Optional[str] = Field(None, min_length=1, max_length=255)
    driver_id: Optional[int] = None
    status: Optional[ShipmentStatus] = None
    status_change_note: Optional[str] = Field(
        None,
        description="Stored on status history when status is updated",
    )


class ShipmentReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: int
    tracking_number: str
    title: str
    description: Optional[str]
    origin: str
    destination: str
    status: ShipmentStatus
    carrier_id: int
    driver_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class ShipmentStatusHistoryReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: int
    shipment_id: int
    old_status: Optional[ShipmentStatus]
    new_status: ShipmentStatus
    changed_by_id: int
    note: Optional[str]
    created_at: datetime
