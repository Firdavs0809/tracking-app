from sqlalchemy import Column, Integer, String, Boolean, Enum as SqlEnum, text
from models.commons.models import BaseModel
from .choices import UserRole


class User(BaseModel):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_superadmin = Column(Boolean, default=False, nullable=False)
    is_staff = Column(Boolean, default=False, nullable=False)
    role = Column(
        SqlEnum(
            UserRole,
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=UserRole.ADMIN,
        server_default=text("'admin'"),
    )

    def __repr__(self):
        return f"<User {self.username}>"

