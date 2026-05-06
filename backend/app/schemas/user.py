from pydantic import BaseModel, EmailStr, field_validator


class UserUpdate(BaseModel):
    """Fields a user may change on their own profile."""

    full_name: str | None = None
    email: EmailStr | None = None

    model_config = {"str_strip_whitespace": True}

    @field_validator("full_name")
    @classmethod
    def full_name_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("full_name cannot be blank")
        return v
