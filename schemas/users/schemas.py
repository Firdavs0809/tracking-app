from pydantic import BaseModel, EmailStr, Field, field_validator

from models.users.choices import UserRole


class UserSignupSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: EmailStr = Field(..., description="Email address of the user")
    password: str = Field(..., min_length=8, max_length=64)
    user_role: UserRole = Field(
        ...,
        description="One of: admin, carrier, driver (values match UserRole)",
    )

    @field_validator("user_role")
    @classmethod
    def block_admin_self_signup(cls, v: UserRole) -> UserRole:
        if v is UserRole.ADMIN:
            raise ValueError("Admin accounts cannot be created via public signup")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john.doe@example.com",
                "password": "password123",
                "user_role": "carrier",
            }
        }

class UserLoginSchema(BaseModel):
    email: EmailStr = Field(..., description="Email address of the user")
    password: str = Field(..., min_length=8, max_length=64)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "password123",
            }
        }

class UsersListSchema(BaseModel):
    id: int
    username: str
    email: EmailStr