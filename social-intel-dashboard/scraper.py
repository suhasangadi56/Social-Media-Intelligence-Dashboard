"""
scraper.py
Data-access layer for the dashboard. Two modes:

1. SYNTHETIC (default) -- reads from the local SQLite DB produced by
   data_generator.py. No network calls, no rate limits, safe for
   development and demos.

2. LIVE -- per-platform fetch functions you wire up to real APIs /
   scraping tools. Each is a clearly marked stub with notes on what's
   needed (API keys, ToS considerations, libraries). None of these are
   implemented with working credentials here -- you must supply your
   own, and you are responsible for complying with each platform's
   Terms of Service and applicable law (many platforms restrict or
   prohibit scraping outright; official APIs are the safer route).

Switch modes via the USE_SYNTHETIC flag or an environment variable:
    SOCIAL_INTEL_MODE=live python app.py
"""

import os
import sqlite3
import pandas as pd

from config import DB_PATH

USE_SYNTHETIC = os.environ.get("SOCIAL_INTEL_MODE", "synthetic").lower() != "live"


# ---------------------------------------------------------------------------
# Synthetic data access
# ---------------------------------------------------------------------------

def _connect():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"No dataset found at {DB_PATH}. Run `python data_generator.py` first."
        )
    return sqlite3.connect(DB_PATH)


def load_posts(subject_ids=None, platforms=None, start_date=None, end_date=None) -> pd.DataFrame:
    conn = _connect()
    df = pd.read_sql("SELECT * FROM posts", conn)
    conn.close()
    df["post_date"] = pd.to_datetime(df["post_date"])

    if subject_ids:
        df = df[df["subject_id"].isin(subject_ids)]
    if platforms:
        df = df[df["platform"].isin(platforms)]
    if start_date:
        df = df[df["post_date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["post_date"] <= pd.to_datetime(end_date)]
    return df.reset_index(drop=True)


def load_comments(post_ids=None, subject_ids=None) -> pd.DataFrame:
    conn = _connect()
    df = pd.read_sql("SELECT * FROM comments", conn)
    conn.close()

    if post_ids is not None:
        df = df[df["post_id"].isin(post_ids)]
    if subject_ids is not None:
        df = df[df["subject_id"].isin(subject_ids)]
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Live scraper stubs -- fill in with real implementations
# ---------------------------------------------------------------------------
# Each function should return a list[dict] shaped like the `posts` records
# produced in data_generator.py (post_id, subject_id, subject_name,
# platform, post_date, post_time, format, topic*, caption, reach, likes,
# shares, comments_count, engagement_rate). *topic is normally filled in
# later by nlp_engine.TopicClassifier, not by the scraper itself.

def fetch_x_posts(handle: str, since: str, until: str) -> list:
    """
    Fetch recent posts for `handle` on X/Twitter.
    Suggested approach: official X API v2 (recent search / user timeline
    endpoints) with a developer account -- avoid unofficial scraping
    libraries, which frequently break and can violate X's ToS.
    """
    raise NotImplementedError(
        "Wire this up to the X API v2 with your own developer credentials."
    )


def fetch_instagram_posts(handle: str, since: str, until: str) -> list:
    """
    Fetch recent posts for `handle` on Instagram.
    Suggested approach: Instagram Graph API (requires the account to be a
    Business/Creator account you or a client controls, plus app review
    for public content access). Unofficial scrapers frequently breach
    Instagram's ToS -- use with caution and only where you have rights
    to the data.
    """
    raise NotImplementedError(
        "Wire this up to the Instagram Graph API with your own app credentials."
    )


def fetch_facebook_posts(handle: str, since: str, until: str) -> list:
    """
    Fetch recent posts for a public Facebook Page.
    Suggested approach: Meta Graph API (Page Public Content Access
    feature, requires app review for pages you don't own).
    """
    raise NotImplementedError(
        "Wire this up to the Meta Graph API with your own app credentials."
    )


def fetch_youtube_posts(channel_id: str, since: str, until: str) -> list:
    """
    Fetch recent videos/shorts for a YouTube channel.
    Suggested approach: YouTube Data API v3 (search.list / videos.list),
    which is well-supported for public channel data and has a generous
    free quota.
    """
    raise NotImplementedError(
        "Wire this up to the YouTube Data API v3 with your own API key."
    )


def fetch_linkedin_posts(handle: str, since: str, until: str) -> list:
    """
    Fetch recent posts for a LinkedIn profile/page.
    LinkedIn's public API surface for third-party post retrieval is very
    limited; most legitimate options require LinkedIn Marketing/Partner
    API access tied to an owned page. Treat this as the hardest platform
    to source programmatically and consider manual/CSV export fallback.
    """
    raise NotImplementedError(
        "Wire this up to LinkedIn's official API access you're approved for."
    )


def fetch_top_comments(platform: str, post_id: str, limit: int = 100) -> list:
    """
    Fetch the top `limit` (50-100 recommended) comments for a given post,
    per platform. Returns list[dict] with at least {comment_id, text}.
    Sampling top comments (rather than all comments) is what keeps this
    within most platforms' API rate limits.
    """
    raise NotImplementedError(
        "Implement per-platform comment retrieval using the matching official API."
    )


PLATFORM_FETCHERS = {
    "x": fetch_x_posts,
    "instagram": fetch_instagram_posts,
    "facebook": fetch_facebook_posts,
    "youtube": fetch_youtube_posts,
    "linkedin": fetch_linkedin_posts,
}


def get_posts(subject_ids=None, platforms=None, start_date=None, end_date=None) -> pd.DataFrame:
    """Single entry point the app calls -- routes to synthetic or live mode."""
    if USE_SYNTHETIC:
        return load_posts(subject_ids, platforms, start_date, end_date)

    from config import SUBJECT_BY_ID
    records = []
    for sid in subject_ids or SUBJECT_BY_ID.keys():
        subject = SUBJECT_BY_ID[sid]
        for platform in platforms or PLATFORM_FETCHERS.keys():
            handle = subject["handles"].get(platform)
            fetcher = PLATFORM_FETCHERS[platform]
            records.extend(fetcher(handle, start_date, end_date))
    return pd.DataFrame(records)


def get_comments(post_ids=None, subject_ids=None) -> pd.DataFrame:
    if USE_SYNTHETIC:
        return load_comments(post_ids, subject_ids)

    records = []
    for post_id in post_ids or []:
        # platform lookup would come from the posts table in a real pipeline
        records.extend(fetch_top_comments(platform="x", post_id=post_id))
    return pd.DataFrame(records)
