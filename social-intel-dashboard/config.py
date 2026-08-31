"""
config.py
Central configuration for the Social Media Intelligence Dashboard.

IMPORTANT ON DATA:
- REFERENCE_LEADER identifies the public figure whose *public, official
  social accounts* this tool is configured to track (name/handle only).
- COMPETITORS use generic placeholder labels ("Competitor A/B/C") by
  design. Swap in real handles only if you have a legitimate basis for
  tracking them (public account, compliant with each platform's ToS and
  applicable law) -- do NOT fabricate quotes or statements and attribute
  them to a real, named individual anywhere in this codebase.
- The bundled synthetic dataset (data_generator.py) produces clearly
  fake, non-attributed sample content for UI development / demo
  purposes only. It is not real social media data and should never be
  presented as such.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Subjects being tracked
# ---------------------------------------------------------------------------

REFERENCE_LEADER = {
    "id": "reference_leader",
    "display_name": "Tejasvi Surya",
    "role": "Reference Leader (MP, Bengaluru South)",
    "handles": {
        "x": "@Tejasvi_Surya",
        "instagram": "@tejasvi.surya",
        "facebook": "TejasviSuryaOfficial",
        "youtube": "TejasviSurya",
        "linkedin": "tejasvi-surya",
    },
    "color": "#FF7A00",  # used consistently in charts
}

# Generic competitor placeholders -- rename/rewire to real public handles
# as needed. Keeping them generic avoids baking fabricated content into
# the repo under a real person's name.
COMPETITORS = [
    {
        "id": "competitor_a",
        "display_name": "Competitor A",
        "role": "Rival Leader A",
        "handles": {p: f"@competitor_a_{p}" for p in
                    ["x", "instagram", "facebook", "youtube", "linkedin"]},
        "color": "#2E5EAA",
    },
    {
        "id": "competitor_b",
        "display_name": "Competitor B",
        "role": "Rival Leader B",
        "handles": {p: f"@competitor_b_{p}" for p in
                    ["x", "instagram", "facebook", "youtube", "linkedin"]},
        "color": "#2CA58D",
    },
    {
        "id": "competitor_c",
        "display_name": "Competitor C",
        "role": "Rival Leader C",
        "handles": {p: f"@competitor_c_{p}" for p in
                    ["x", "instagram", "facebook", "youtube", "linkedin"]},
        "color": "#B23A9E",
    },
]

ALL_SUBJECTS = [REFERENCE_LEADER] + COMPETITORS
SUBJECT_BY_ID = {s["id"]: s for s in ALL_SUBJECTS}

# ---------------------------------------------------------------------------
# Platforms & post formats
# ---------------------------------------------------------------------------

PLATFORMS = ["x", "instagram", "facebook", "youtube", "linkedin"]

PLATFORM_DISPLAY = {
    "x": "X (Twitter)",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "youtube": "YouTube",
    "linkedin": "LinkedIn",
}

POST_FORMATS = {
    "x": ["Single Tweet", "Thread", "Poll", "Video"],
    "instagram": ["Reel", "Carousel", "Single Image", "Story Highlight"],
    "facebook": ["Photo Post", "Video", "Live", "Text Update"],
    "youtube": ["Short", "Long-form Video", "Community Post"],
    "linkedin": ["Article", "Text Post", "Document Carousel"],
}

# ---------------------------------------------------------------------------
# Topic taxonomy (used by nlp_engine.TopicClassifier)
# ---------------------------------------------------------------------------

TOPIC_CATEGORIES = [
    "Civic Issues",
    "Traffic & Mobility",
    "Infrastructure",
    "Public Safety",
    "Development & Economy",
    "Education",
    "Health",
    "Governance & Policy",
    "General / Other",
]

# Keyword seeds for the rule-based / zero-shot-lite classifier.
TOPIC_KEYWORDS = {
    "Civic Issues": ["garbage", "waste", "sanitation", "water supply", "sewage",
                      "streetlight", "civic", "pothole", "encroachment"],
    "Traffic & Mobility": ["traffic", "signal", "congestion", "metro", "bus",
                            "flyover", "parking", "commute", "junction"],
    "Infrastructure": ["road", "construction", "bridge", "project", "footpath",
                        "underpass", "pipeline", "power outage", "infrastructure"],
    "Public Safety": ["crime", "safety", "police", "harassment", "theft",
                       "accident", "security", "law and order"],
    "Development & Economy": ["investment", "startup", "jobs", "economy",
                               "development", "industry", "business", "gdp"],
    "Education": ["school", "college", "student", "education", "exam",
                  "university", "scholarship"],
    "Health": ["hospital", "health", "clinic", "vaccination", "doctor",
               "medicine", "healthcare"],
    "Governance & Policy": ["policy", "bill", "parliament", "assembly",
                             "governance", "scheme", "budget", "reform"],
}

# ---------------------------------------------------------------------------
# Data generation window
# ---------------------------------------------------------------------------

DEFAULT_WINDOW_DAYS = 30
TODAY = date.today()
DATE_RANGE = [TODAY - timedelta(days=i) for i in range(DEFAULT_WINDOW_DAYS)][::-1]

DB_PATH = "data/social_intel.db"
