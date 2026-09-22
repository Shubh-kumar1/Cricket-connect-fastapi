from pydantic import BaseModel, ConfigDict, Field


class ProviderProfileCreate(BaseModel):
    business_name: str = Field(min_length=2, max_length=150)
    bio: str | None = None
    phone: str | None = Field(default=None, max_length=30)


class ProviderProfileRead(ProviderProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int

