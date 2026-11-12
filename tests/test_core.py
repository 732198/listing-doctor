"""Run: python -m pytest -q"""
from streamlit.testing.v1 import AppTest

from core.ai import TONES, DemoService
from core.models import Listing, load_sample

svc = DemoService()


def test_sample_loads_with_photos():
    L = load_sample()
    assert L.title and len(L.photos) == 4 and "parking" in L.house_facts.lower()


def test_diagnosis_flags_known_problems():
    d = svc.diagnose(load_sample())
    assert d.overall < 6
    assert set(d.photo_extras) == {"Outdoor shower", "Beach chairs", "Two bikes"}
    assert any("location" in i for i in d.issues)


def test_rewrite_raises_score_and_keeps_extras():
    L = load_sample()
    d = svc.diagnose(L)
    for tone in TONES:
        r = svc.rewrite(L, d, d.photo_extras, tone)
        assert len(r.title) <= 50
        assert all(e in r.amenities for e in d.photo_extras)
        new = svc.diagnose(Listing(r.title, r.description, r.amenities, L.location, L.house_facts, L.photos))
        assert new.overall > d.overall + 3


def test_guest_answers_only_from_facts():
    L = load_sample()
    assert "driveway" in svc.answer(L, "Is there parking?").reply
    assert "4pm" in svc.answer(L, "What time is check-in?").reply
    hot_tub = svc.answer(L, "Is there a hot tub?")
    assert hot_tub.answered_from_listing is False


def test_app_full_flow_in_demo_mode():
    at = AppTest.from_file("../app.py", default_timeout=30).run()
    [b for b in at.button if b.label.startswith("Use sample")][0].click().run()
    assert at.session_state.listing is not None
    [b for b in at.button if b.label == "Diagnose my listing"][0].click().run()
    assert at.session_state.diagnosis.overall < 6
    [b for b in at.button if b.label == "Write new draft"][0].click().run()
    assert at.session_state.new_diagnosis.overall > 9
    assert not at.exception
