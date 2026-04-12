from sqlalchemy import (
    Column,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.commons.models import BaseModel

from .choices import ShipmentStatus

ShipmentStatusPG = SqlEnum(
    ShipmentStatus,
    name="shipmentstatus",
    values_callable=lambda enum_cls: [m.value for m in enum_cls],
    native_enum=True,
)


class Shipment(BaseModel):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)

    status = Column(
        ShipmentStatusPG,
        default=ShipmentStatus.CREATED,
        nullable=False,
        index=True,
    )

    carrier_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    carrier = relationship("User", foreign_keys=[carrier_id], backref="created_shipments")
    driver = relationship("User", foreign_keys=[driver_id], backref="assigned_shipments")
    status_history = relationship(
        "ShipmentStatusHistory",
        back_populates="shipment",
        cascade="all, delete-orphan",
    )


class ShipmentStatusHistory(BaseModel):
    __tablename__ = "shipment_status_history"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)

    old_status = Column(ShipmentStatusPG, nullable=True)
    new_status = Column(ShipmentStatusPG, nullable=False)

    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    note = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    shipment = relationship("Shipment", foreign_keys=[shipment_id],back_populates="status_history")
    changed_by = relationship("User", foreign_keys=[changed_by_id], backref="shipment_status_updates")
