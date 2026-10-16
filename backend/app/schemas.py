from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CharacterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    franchise: str = Field(min_length=1, max_length=160)
    variant: str = Field(min_length=1, max_length=160)
    fictional_confirmed: Literal[True]

    @field_validator("name", "franchise", "variant")
    @classmethod
    def no_control_characters(cls, value: str) -> str:
        if any(ord(c) < 32 for c in value):
            raise ValueError("Use a single line of text.")
        return value


class CharacterUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    revision: int = Field(ge=1)
    notes: str = Field(max_length=6000)
    direction: str = Field(max_length=3000)


class ArchiveUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: int = Field(ge=1)
    archived: bool
