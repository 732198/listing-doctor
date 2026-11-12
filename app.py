"""Listing Doctor: Streamlit UI.

Run:  streamlit run app.py
Set GEMINI_API_KEY (env var or .streamlit/secrets.toml) for live AI.
Without a key the app runs in demo mode.
"""
import os

import streamlit as st

from core.ai import TONES, get_service
from core.models import Listing, Photo, load_sample

st.set_page_config(page_title="Listing Doctor", page_icon="🩺", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 3.5rem; max-width: 1150px;}
      .ld-card {background:#FFFFFF; border:1px solid #E6DED0; border-radius:12px; padding:18px 22px; margin-bottom:12px;}
      .ld-score {font-size:56px; font-weight:700; color:#B5452F; line-height:1;}
      .ld-score.good {color:#2F7A55;}
      .ld-label {font-size:13px; letter-spacing:1.5px; text-transform:uppercase; color:#B5452F; font-weight:600;}
      .ld-issue {background:#FFF8F0; border:1px solid #EBD9C3; border-radius:8px; padding:8px 12px; margin:6px 0;}
      .ld-before {color:#8A8F99; text-decoration:line-through;}
      .ld-after {font-size:22px; font-weight:700; color:#1B2A4A;}
      .ld-pill {display:inline-block; background:#EFE8DC; border-radius:20px; padding:3px 12px; margin:2px 4px 2px 0; font-size:14px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- state
ss = st.session_state
for key, default in {
    "listing": None, "diagnosis": None, "extras": [], "rewrite": None,
    "new_diagnosis": None, "chat": [], "error": None,
}.items():
    ss.setdefault(key, default)


def reset_results():
    ss.diagnosis = ss.rewrite = ss.new_diagnosis = None
    ss.extras, ss.chat = [], []


def secret_key() -> str:
    try:
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return ""


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### 🩺 Listing Doctor")
    st.caption("Diagnose, rewrite and answer guests for your short-term rental.")
    key = os.getenv("GEMINI_API_KEY") or secret_key()
    typed = st.text_input("Gemini API key", type="password", value="", placeholder="optional")
    key = typed or key
    force_demo = st.toggle("Demo mode (offline)", value=not bool(key))
    service = get_service(key, force_demo=force_demo)
    if service.is_demo:
        st.info("**Demo mode.** Rules and saved results stand in for Gemini. Add a key for live AI.")
    else:
        st.success(f"**Live AI:** {service.name} ({service.model})")
    st.divider()
    if st.button("Start over", use_container_width=True):
        ss.listing = None
        reset_results()
        st.rerun()


def run(fn, *args, **kwargs):
    """Call the AI layer and show a friendly error instead of a stack trace."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:  # network, quota, bad key, schema errors
        st.error(f"The AI call failed: {e}. Try again, or switch on demo mode in the sidebar.")
        return None


# ---------------------------------------------------------------- header
st.markdown('<div class="ld-label">Listing Doctor</div>', unsafe_allow_html=True)
st.title("Fix your listing in minutes")

tab_listing, tab_diag, tab_rewrite, tab_guest = st.tabs(
    ["1 · Your listing", "2 · Diagnose", "3 · Rewrite", "4 · Guest replies"]
)

# ---------------------------------------------------------------- 1. listing
with tab_listing:
    left, right = st.columns([1, 1], gap="large")
    with left:
        st.subheader("Load a listing")
        if st.button("Use sample: Maria's Newport home", type="primary", use_container_width=True):
            ss.listing = load_sample()
            reset_results()
            st.rerun()
        with st.expander("Or paste your own listing"):
            with st.form("paste"):
                title = st.text_input("Title")
                location = st.text_input("Location", placeholder="Newport, Rhode Island")
                desc = st.text_area("Description", height=160)
                amen = st.text_input("Amenities (comma separated)", placeholder="Wifi, Kitchen, Free parking")
                facts = st.text_area(
                    "House facts for guest replies", height=100,
                    placeholder="Parking, check-in steps, beds, pets, distances...",
                )
                files = st.file_uploader("Photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
                if st.form_submit_button("Save listing"):
                    if not title or not desc:
                        st.warning("Add at least a title and a description.")
                    else:
                        ss.listing = Listing(
                            title=title, description=desc, location=location, house_facts=facts,
                            amenities=[a.strip() for a in amen.split(",") if a.strip()],
                            photos=[Photo(f.name, f.getvalue(), f.type or "image/jpeg") for f in files or []],
                        )
                        reset_results()
                        st.rerun()
    with right:
        L = ss.listing
        if L is None:
            st.markdown('<div class="ld-card">No listing loaded yet. Start with the sample to see the full flow.</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="ld-card"><div class="ld-label">Loaded</div>'
                f'<div class="ld-after">{L.title}</div>'
                f'<div>{L.location}</div>'
                f'<div style="margin-top:8px;color:#5A6170">{len(L.photos)} photos · {len(L.amenities)} amenities · '
                f'{L.word_count}-word description</div></div>',
                unsafe_allow_html=True,
            )
            if L.photos:
                cols = st.columns(min(len(L.photos), 4))
                for c, p in zip(cols * 4, L.photos):
                    c.image(p.data, use_container_width=True)
            st.caption("Next: open **2 · Diagnose**.")

# ---------------------------------------------------------------- 2. diagnose
with tab_diag:
    L = ss.listing
    if L is None:
        st.info("Load a listing in step 1 first.")
    else:
        if st.button("Diagnose my listing", type="primary"):
            with st.spinner("Scoring your listing and scanning photos..."):
                ss.diagnosis = run(service.diagnose, L)
                ss.extras = list(ss.diagnosis.photo_extras) if ss.diagnosis else []
                ss.rewrite = ss.new_diagnosis = None
        D = ss.diagnosis
        if D:
            c1, c2 = st.columns([1, 2], gap="large")
            with c1:
                st.markdown(
                    f'<div class="ld-card"><div class="ld-label">Listing score / 10</div>'
                    f'<div class="ld-score">{D.overall}</div>'
                    f'<div style="margin-top:6px">{L.title}</div></div>',
                    unsafe_allow_html=True,
                )
                m1, m2, m3 = st.columns(3)
                m1.metric("Title", f"{D.scores.title:g}")
                m2.metric("Description", f"{D.scores.description:g}")
                m3.metric("Amenities", f"{D.scores.amenities:g}")
            with c2:
                st.markdown("**What we found**")
                for issue in D.issues:
                    st.markdown(f'<div class="ld-issue">⚠️ {issue}</div>', unsafe_allow_html=True)
                if D.photo_extras:
                    st.markdown("**Seen in your photos but not listed.** Confirm what's really there:")
                    ss.extras = [e for e in D.photo_extras if st.checkbox(e, value=e in ss.extras, key=f"x_{e}")]
                elif L.photos and service.is_demo:
                    st.caption("Photo scan of your own photos needs a Gemini key.")
            st.caption("Next: open **3 · Rewrite**.")

# ---------------------------------------------------------------- 3. rewrite
with tab_rewrite:
    L, D = ss.listing, ss.diagnosis
    if D is None:
        st.info("Run the diagnosis in step 2 first.")
    else:
        tone = st.radio("Tone", TONES, horizontal=True)
        if st.button("Write new draft", type="primary"):
            with st.spinner("Writing a new draft..."):
                ss.rewrite = run(service.rewrite, L, D, ss.extras, tone)
                ss.new_diagnosis = None
        R = ss.rewrite
        if R:
            if ss.new_diagnosis is None:
                new_listing = Listing(R.title, R.description, R.amenities, L.location, L.house_facts, L.photos)
                ss.new_diagnosis = run(service.diagnose, new_listing)
            c1, c2 = st.columns([2, 1], gap="large")
            with c1:
                st.markdown(
                    f'<div class="ld-card"><div class="ld-label">Title · before and after</div>'
                    f'<div class="ld-before">{L.title}</div><div class="ld-after">{R.title}</div></div>',
                    unsafe_allow_html=True,
                )
                st.markdown("**New description**")
                st.markdown(f'<div class="ld-card">{R.description.replace(chr(10), "<br>")}</div>',
                            unsafe_allow_html=True)
                st.markdown("**Amenities** " + "".join(f'<span class="ld-pill">{a}</span>' for a in R.amenities),
                            unsafe_allow_html=True)
            with c2:
                if ss.new_diagnosis:
                    nd = ss.new_diagnosis
                    st.markdown(
                        f'<div class="ld-card"><div class="ld-label">New score / 10</div>'
                        f'<div class="ld-score good">{nd.overall}</div>'
                        f'<div style="color:#5A6170">up from {D.overall}</div></div>',
                        unsafe_allow_html=True,
                    )
                st.markdown("**What changed**")
                for c in R.changes:
                    st.markdown(f"- {c}")
            st.divider()
            fix = st.text_input("Need a change? Tell the AI",
                                placeholder="Keep it casual and mention the 5-minute walk to the beach")
            b1, b2 = st.columns([1, 3])
            if b1.button("Refine draft", disabled=not fix):
                with st.spinner("Updating the draft..."):
                    ss.rewrite = run(service.rewrite, L, D, ss.extras, tone, fix) or R
                    ss.new_diagnosis = None
                    st.rerun()
            text = f"{R.title}\n\n{R.description}\n\nAmenities: {', '.join(R.amenities)}"
            b2.download_button("Download listing (.txt)", text, file_name="listing.txt")
            st.caption("Copy into Airbnb's listing editor. Direct publishing is out of scope for the MVP.")

# ---------------------------------------------------------------- 4. guest replies
with tab_guest:
    L = ss.listing
    if L is None:
        st.info("Load a listing in step 1 first.")
    else:
        st.caption("Draft replies come only from your listing and house facts. If the answer isn't there, "
                   "the AI says the host will follow up.")
        examples = ["Is there parking?", "How far is the beach?", "Can we bring our dog?", "Is there a hot tub?"]
        cols = st.columns(len(examples))
        asked = None
        for c, q in zip(cols, examples):
            if c.button(q, use_container_width=True):
                asked = q
        with st.form("guest", clear_on_submit=True):
            typed_q = st.text_input("Guest message", placeholder="Type a guest question")
            if st.form_submit_button("Draft reply") and typed_q:
                asked = typed_q
        if asked:
            with st.spinner("Drafting a reply..."):
                r = run(service.answer, L, asked)
            if r:
                ss.chat.append((asked, r))
        for q, r in reversed(ss.chat):
            with st.chat_message("user", avatar="🧳"):
                st.write(q)
            with st.chat_message("assistant", avatar="🩺"):
                st.write(r.reply)
                if not r.answered_from_listing:
                    st.caption("Not in your listing facts. Flagged for you to answer.")
