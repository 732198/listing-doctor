"""Data models shared by the UI and the AI layer.

The Pydantic models double as response schemas for Gemini's JSON mode, so the
model is forced to return exactly these fields.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Photo:
    name: str
    data: bytes
    mime_type: str = "image/jpeg"


@dataclass
class Listing:
    title: str
    description: str
    amenities: list[str]
    location: str = ""
    house_facts: str = ""  # host-provided facts used to answer guest questions
    photos: list[Photo] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return len(self.description.split())

    def as_text(self) -> str:
        """Plain-text view of the listing that goes into prompts."""
        return (
            f"TITLE: {self.title}\n"
            f"LOCATION: {self.location or 'not given'}\n"
            f"AMENITIES: {', '.join(self.amenities) or 'none listed'}\n"
            f"DESCRIPTION: {self.description}"
        )


def load_sample() -> Listing:
    """Load the bundled Newport sample listing and its photos."""
    raw = json.loads((DATA_DIR / "sample_listing.json").read_text())
    photos = [
        Photo(name=p.stem, data=p.read_bytes())
        for p in sorted((DATA_DIR / "photos").glob("*.jpg"))
    ]
    return Listing(photos=photos, **raw)


# ---------- AI response schemas ----------

class Scores(BaseModel):
    title: float = Field(ge=0, le=10)
    description: float = Field(ge=0, le=10)
    amenities: float = Field(ge=0, le=10)


class Diagnosis(BaseModel):
    scores: Scores
    issues: list[str] = Field(description="Specific problems, most important first")
    strengths: list[str] = Field(default_factory=list)
    photo_extras: list[str] = Field(
        default_factory=list,
        description="Features visible in the photos that are not in the amenities or description",
    )

    @property
    def overall(self) -> float:
        s = self.scores
        return round((s.title + s.description + s.amenities) / 3, 1)


class Rewrite(BaseModel):
    title: str
    description: str
    amenities: list[str]
    changes: list[str] = Field(description="Short list of what changed and why")


class GuestReply(BaseModel):
    reply: str
    answered_from_listing: bool = Field(
        description="False if the facts did not contain the answer and the host must follow up"
    )
