"""AI service layer.

Two interchangeable services with the same three methods:
    diagnose(listing)            -> Diagnosis   (Gemini text + vision, one call)
    rewrite(listing, ...)        -> Rewrite     (Gemini text)
    answer(listing, question)    -> GuestReply  (Gemini, grounded in listing facts)

GeminiService calls the real API. DemoService runs offline with rules and canned
results for the bundled sample, so the class demo works with no key or Wi-Fi.
"""
from __future__ import annotations

import os
import re

from . import prompts
from .models import Diagnosis, GuestReply, Listing, Rewrite, Scores

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TONES = ["Warm and casual", "Polished and upscale", "Short and punchy"]


# ---------------------------------------------------------------- Gemini

class GeminiService:
    name = "Gemini"
    is_demo = False

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        from google import genai  # imported here so demo mode needs no SDK

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def _json(self, contents, schema):
        from google.genai import types

        resp = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.4,
            ),
        )
        if getattr(resp, "parsed", None) is not None:
            return resp.parsed
        return schema.model_validate_json(resp.text)

    def diagnose(self, listing: Listing) -> Diagnosis:
        from google.genai import types

        prompt = prompts.DIAGNOSE.format(rubric=prompts.RUBRIC, listing=listing.as_text())
        parts = [prompt] + [
            types.Part.from_bytes(data=p.data, mime_type=p.mime_type) for p in listing.photos
        ]
        return self._json(parts, Diagnosis)

    def rewrite(self, listing, diagnosis, extras, tone, instruction="") -> Rewrite:
        prompt = prompts.REWRITE.format(
            extras=", ".join(extras) or "none",
            issues="; ".join(diagnosis.issues) or "none",
            tone=tone,
            instruction=prompts.REFINE_LINE.format(text=instruction) if instruction else "",
            listing=listing.as_text(),
        )
        return self._json(prompt, Rewrite)

    def answer(self, listing: Listing, question: str) -> GuestReply:
        prompt = prompts.GUEST.format(
            listing=listing.as_text(), facts=listing.house_facts or "none", question=question
        )
        return self._json(prompt, GuestReply)


# ---------------------------------------------------------------- Demo

GENERIC = {"cozy", "nice", "great", "lovely", "charming", "comfortable", "relaxing", "perfect"}
FEATURES = {"beach", "walk", "view", "pool", "hot tub", "waterfront", "ocean", "harbor", "steps"}
RULE_WORDS = ("no smoking", "no parties", "check-in", "check-out", "leave it the way")

# What the bundled sample photos show (stands in for the vision model offline)
SAMPLE_PHOTO_FINDINGS = {
    "03_backyard": ["Outdoor shower", "Beach chairs"],
    "04_garage": ["Two bikes"],
}

SAMPLE_REWRITES = {
    "Warm and casual": (
        "Sunny 3BR Retreat · Walk to Town & Beach",
        "Leave the car in the driveway: from this Newport home, Easton's Beach is a 5-minute walk, and Bellevue Avenue is just 10.\n\n"
        "Grab the two bikes and beach chairs from the garage, spend the day by the water, then rinse off in "
        "the outdoor shower before dinner.\n\n"
        "Inside, three bedrooms sleep six: two queens and two twins. The full kitchen has everything for "
        "family meals, and the washer and dryer make longer stays easy.\n\n"
        "Free parking for two cars and self check-in with a keypad.\n\n"
        "Check-in 4pm · Check-out 10am",
    ),
    "Polished and upscale": (
        "Newport 3BR Home · 5 Min Walk to the Beach",
        "A bright three-bedroom Newport home a 5-minute walk from Easton's Beach and 10 minutes on foot from "
        "Bellevue Avenue's mansions and dining.\n\n"
        "Two queen bedrooms and a twin room sleep six. A full kitchen, in-unit laundry and fast Wi-Fi "
        "make it easy to settle in for a week.\n\n"
        "Beach chairs, two bikes and a private outdoor shower are ready for summer days. Parking for two "
        "cars and keypad self check-in.\n\n"
        "Check-in 4pm · Check-out 10am",
    ),
    "Short and punchy": (
        "Walk to Easton's Beach · 3BR + Bikes",
        "Newport, on foot: 5 minutes to the beach. 10 to Bellevue Ave.\n\n"
        "Sleeps 6. Full kitchen. Washer and dryer. Fast Wi-Fi.\n\n"
        "Bikes, beach chairs and an outdoor shower included. Parking for two cars. Keypad self check-in.\n\n"
        "Check-in 4pm · Check-out 10am",
    ),
}

SYNONYMS = {
    "park": ["parking", "driveway", "car"],
    "car": ["parking", "driveway"],
    "wifi": ["wifi"], "internet": ["wifi"],
    "pet": ["pets"], "dog": ["pets"], "cat": ["pets"],
    "beach": ["beach"], "bike": ["bikes"], "shower": ["shower"],
    "check": ["check-in", "check-out", "keypad"], "arrive": ["check-in", "keypad"],
    "key": ["keypad", "code"], "sleep": ["sleeps", "queen"], "bed": ["queen", "twins"],
    "crib": ["pack-and-play"], "baby": ["pack-and-play"], "coffee": ["coffee"],
    "smok": ["smoking"], "party": ["parties"], "time": ["4pm", "10am"],
}


class DemoService:
    name = "Demo mode"
    is_demo = True

    # -- diagnose: rule-based rubric that mirrors prompts.RUBRIC
    def diagnose(self, listing: Listing) -> Diagnosis:
        issues, strengths = [], []
        title_l, desc_l = listing.title.lower(), listing.description.lower()
        town = listing.location.split(",")[0].strip().lower()

        t = 9.0
        if any(w in title_l for w in GENERIC):
            t -= 3; issues.append("Title is generic and easy to scroll past")
        if not any(w in title_l for w in FEATURES):
            t -= 2; issues.append("Title doesn't name a standout feature like the beach")
        if len(listing.title) > 50:
            t -= 1; issues.append("Title is longer than 50 characters")

        d = 9.5
        if town and town not in desc_l:
            d -= 1.5; issues.append("Description never mentions the location")
        if not re.search(r"\bminute|\bmile|\bwalk", desc_l):
            d -= 1.5; issues.append("No walking distances to the beach or town")
        if sum(desc_l.count(w) for w in GENERIC) >= 3:
            d -= 0.5; issues.append("Leans on vague adjectives instead of details")
        if any(w in desc_l for w in RULE_WORDS[:2] + RULE_WORDS[4:]):
            d -= 0.5; issues.append("House rules take up space in the pitch")
        if listing.word_count > 200:
            d -= 1; issues.append("Description is long; guests skim")

        extras = self._photo_extras(listing)
        a = 9.0 - 1.0 * len(extras)
        if len(listing.amenities) < 4:
            a -= 1; issues.append("Very few amenities listed")

        if t >= 8: strengths.append("Title is specific")
        if d >= 8: strengths.append("Description gives concrete details")
        if "free parking" in " ".join(listing.amenities).lower(): strengths.append("Free parking is listed")

        return Diagnosis(
            scores=Scores(title=max(t, 0), description=max(d, 0), amenities=max(a, 0)),
            issues=issues, strengths=strengths, photo_extras=extras,
        )

    def _photo_extras(self, listing: Listing) -> list[str]:
        listed = (" ".join(listing.amenities) + " " + listing.description).lower()
        found = []
        for p in listing.photos:
            for item in SAMPLE_PHOTO_FINDINGS.get(p.name, []):
                key = item.lower().replace("two ", "").rstrip("s")
                if key not in listed and item not in found:
                    found.append(item)
        return found

    # -- rewrite: canned for the sample, template otherwise
    def rewrite(self, listing, diagnosis, extras, tone, instruction="") -> Rewrite:
        amenities = listing.amenities + [e for e in extras if e not in listing.amenities]
        if listing.title in ("Cozy 3BR Newport Home Near Town",) and tone in SAMPLE_REWRITES:
            title, desc = SAMPLE_REWRITES[tone]
        else:
            town = listing.location.split(",")[0] or "Your"
            title = f"{town} Stay · {extras[0] if extras else listing.amenities[0] if listing.amenities else 'Great Location'}"[:50]
            desc = listing.description
            if extras:
                desc += "\n\nAlso included: " + ", ".join(e.lower() for e in extras) + "."
        changes = [
            "Title now leads with location and a standout feature",
            "Opening line sells the location with walking distances",
            f"Added extras from your photos: {', '.join(extras).lower() or 'none'}",
            "Moved house rules out of the pitch",
        ]
        if instruction:
            changes.append("Demo mode: free-text changes are applied when a Gemini key is set")
        return Rewrite(title=title, description=desc, amenities=amenities, changes=changes)

    # -- answer: keyword retrieval over house facts
    def answer(self, listing: Listing, question: str) -> GuestReply:
        facts = [s.strip() for s in re.split(r"(?<=\.)\s+", listing.house_facts) if s.strip()]
        q = question.lower()
        terms = set()
        for k, v in SYNONYMS.items():
            if k in q:
                terms.update(v)
        best, best_score = None, 0
        for f in facts:
            score = sum(1 for t in terms if t in f.lower())
            if score > best_score:
                best, best_score = f, score
        if not best:
            return GuestReply(
                reply="Thanks for asking! I'll check with the host and get back to you shortly.",
                answered_from_listing=False,
            )
        opener = "Yes! " if q.startswith(("is there", "do you", "are there", "can i", "is it")) and not best.lower().startswith("no ") else ""
        return GuestReply(reply=f"{opener}{best}", answered_from_listing=True)


def get_service(api_key: str | None, force_demo: bool = False):
    if api_key and not force_demo:
        return GeminiService(api_key)
    return DemoService()
