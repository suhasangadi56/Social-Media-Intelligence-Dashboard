"""
data_generator.py
Produces a synthetic 30-day multi-platform dataset for the dashboard so
the UI can be built/tested without hitting real platform rate limits.

ALL content produced here is fake, template-generated placeholder text.
It is NOT scraped, NOT real, and NOT attributed as an actual statement
by any real person. Clearly synthetic by construction.

Run directly to (re)generate the SQLite database:
    python data_generator.py
"""

import random
import sqlite3
import uuid
from datetime import datetime, timedelta

from config import ALL_SUBJECTS, PLATFORMS, POST_FORMATS, DATE_RANGE, DB_PATH

random.seed(42)  # reproducible demo data

# ---------------------------------------------------------------------------
# Template pools (generic, non-attributed placeholder content)
# ---------------------------------------------------------------------------

CAPTION_TEMPLATES = {
    "Civic Issues": [
        "Held a ward-level review on {issue} today. More action coming soon.",
        "Residents raised concerns about {issue} in our locality meeting.",
        "Inspected the {issue} situation on-ground this morning.",
    ],
    "Traffic & Mobility": [
        "Reviewed the {issue} bottleneck near the main junction today.",
        "Good news: work on the {issue} corridor is progressing well.",
        "Discussed {issue} improvements with civic officials.",
    ],
    "Infrastructure": [
        "Inaugurated the new {issue} project for the constituency.",
        "Site visit for the ongoing {issue} works this afternoon.",
        "Funds sanctioned for {issue} upgrades in the coming quarter.",
    ],
    "Public Safety": [
        "Met with local police on strengthening {issue} measures.",
        "Community safety walk focused on {issue} concerns.",
        "New helpline launched to report {issue} incidents faster.",
    ],
    "Development & Economy": [
        "Exciting update on {issue} bringing new opportunities to the region.",
        "Roundtable with local businesses on {issue} growth.",
        "Signed an MoU to boost {issue} in the constituency.",
    ],
    "Education": [
        "Visited a government school to review {issue} initiatives.",
        "Launched a new {issue} scholarship program today.",
        "Interacted with students about {issue} access.",
    ],
    "Health": [
        "Inspected the {issue} facility upgrade at the local hospital.",
        "Free {issue} camp organized for residents this weekend.",
        "Reviewed {issue} readiness ahead of the season.",
    ],
    "Governance & Policy": [
        "Spoke in the House today on {issue} reforms.",
        "Constituency office now processing {issue} requests faster.",
        "Released a report card on {issue} progress this term.",
    ],
    "General / Other": [
        "Great to interact with citizens at today's outreach event.",
        "Thank you for the warm welcome at today's programme.",
        "Sharing a quick update from today's schedule.",
    ],
}

ISSUE_FILLERS = {
    "Civic Issues": ["garbage collection", "water supply", "street lighting", "drainage"],
    "Traffic & Mobility": ["signal timing", "metro connectivity", "bus route", "parking"],
    "Infrastructure": ["flyover", "footpath", "underpass", "road relaying"],
    "Public Safety": ["night patrolling", "women's safety", "traffic safety", "CCTV"],
    "Development & Economy": ["startup hub", "local industry", "tourism", "employment"],
    "Education": ["digital classroom", "scholarship", "skill training", "library access"],
    "Health": ["diagnostic centre", "vaccination drive", "ambulance service", "mental health"],
    "Governance & Policy": ["grievance redress", "welfare scheme", "budget allocation", "e-governance"],
    "General / Other": ["community", "outreach", "engagement", "programme"],
}

COMMENT_TEMPLATES = {
    "Positive": [
        "Great work, keep it up!", "Finally some progress, thank you!",
        "Appreciate the quick action on this.", "This is a welcome step for our area.",
        "Thanks for listening to residents.", "Good to see visible change on ground.",
        "Well done, needed this for a long time.", "Proud to have a responsive representative.",
    ],
    "Negative": [
        "This has been an issue for months, why so late?",
        "Just photo-ops, no real change on ground.",
        "Still waiting for action in our locality.",
        "This is not enough, ground reality is very different.",
        "Complaints have gone unanswered for weeks.",
        "Disappointed, expected better follow-through.",
        "Same promises every time, no delivery.",
        "This area still has serious problems, please visit in person.",
    ],
    "Neutral": [
        "When will this be completed?",
        "Can you share more details on the timeline?",
        "Which locality does this cover?",
        "Is this applicable to our ward too?",
        "Following up on this for updates.",
        "Noted, will wait for further updates.",
    ],
}

# Rough weighting so the reference leader + competitors don't look identical
SUBJECT_PROFILE = {
    "reference_leader": {"base_reach": 180000, "base_engagement_rate": 0.045, "sentiment_bias": 0.10},
    "competitor_a": {"base_reach": 140000, "base_engagement_rate": 0.038, "sentiment_bias": -0.05},
    "competitor_b": {"base_reach": 95000, "base_engagement_rate": 0.03, "sentiment_bias": 0.0},
    "competitor_c": {"base_reach": 60000, "base_engagement_rate": 0.05, "sentiment_bias": -0.15},
}

PLATFORM_REACH_MULTIPLIER = {
    "x": 0.9, "instagram": 1.3, "facebook": 0.8, "youtube": 1.1, "linkedin": 0.5,
}


def _pick_topic():
    from config import TOPIC_CATEGORIES
    weights = [0.16, 0.14, 0.14, 0.1, 0.1, 0.1, 0.1, 0.12, 0.04]
    return random.choices(TOPIC_CATEGORIES, weights=weights, k=1)[0]


def _make_caption(topic):
    template = random.choice(CAPTION_TEMPLATES.get(topic, CAPTION_TEMPLATES["General / Other"]))
    issue = random.choice(ISSUE_FILLERS.get(topic, ISSUE_FILLERS["General / Other"]))
    return template.format(issue=issue)


def _make_comments(n, sentiment_bias):
    """Generate n synthetic comments with a sentiment mix nudged by bias."""
    base_weights = {"Positive": 0.40, "Negative": 0.35, "Neutral": 0.25}
    pos = max(0.05, base_weights["Positive"] + sentiment_bias)
    neg = max(0.05, base_weights["Negative"] - sentiment_bias)
    neu = max(0.05, 1 - pos - neg)
    total = pos + neg + neu
    pos, neg, neu = pos / total, neg / total, neu / total

    labels = random.choices(["Positive", "Negative", "Neutral"], weights=[pos, neg, neu], k=n)
    return [(lbl, random.choice(COMMENT_TEMPLATES[lbl])) for lbl in labels]


def generate_dataset():
    posts = []
    comments = []

    for subject in ALL_SUBJECTS:
        profile = SUBJECT_PROFILE[subject["id"]]
        for day in DATE_RANGE:
            # Not every subject posts on every platform every day
            for platform in PLATFORMS:
                if random.random() > 0.55:  # ~55% chance of a post that day/platform
                    continue

                topic = _pick_topic()
                fmt = random.choice(POST_FORMATS[platform])
                caption = _make_caption(topic)

                reach = int(
                    profile["base_reach"]
                    * PLATFORM_REACH_MULTIPLIER[platform]
                    * random.uniform(0.6, 1.5)
                )
                engagement_rate = max(
                    0.005,
                    random.gauss(profile["base_engagement_rate"], 0.01),
                )
                engagements = int(reach * engagement_rate)
                likes = int(engagements * random.uniform(0.65, 0.8))
                shares = int(engagements * random.uniform(0.05, 0.15))
                num_comments_total = max(5, engagements - likes - shares)

                post_id = str(uuid.uuid4())[:8]
                post_time = datetime.combine(day, datetime.min.time()) + timedelta(
                    hours=random.randint(7, 21), minutes=random.randint(0, 59)
                )

                posts.append({
                    "post_id": post_id,
                    "subject_id": subject["id"],
                    "subject_name": subject["display_name"],
                    "platform": platform,
                    "post_date": day.isoformat(),
                    "post_time": post_time.isoformat(),
                    "format": fmt,
                    "topic": topic,
                    "caption": caption,
                    "reach": reach,
                    "likes": likes,
                    "shares": shares,
                    "comments_count": num_comments_total,
                    "engagement_rate": round(engagement_rate, 4),
                })

                # Sample 50-100 top comments per post (capped by comments_count)
                sample_n = min(num_comments_total, random.randint(50, 100))
                for lbl, text in _make_comments(sample_n, profile["sentiment_bias"]):
                    comments.append({
                        "comment_id": str(uuid.uuid4())[:8],
                        "post_id": post_id,
                        "subject_id": subject["id"],
                        "platform": platform,
                        "post_date": day.isoformat(),
                        "topic": topic,
                        "text": text,
                        "seed_sentiment": lbl,  # ground-truth label for demo validation
                    })

    return posts, comments


def save_to_sqlite(posts, comments, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS posts")
    cur.execute("""
        CREATE TABLE posts (
            post_id TEXT PRIMARY KEY,
            subject_id TEXT, subject_name TEXT, platform TEXT,
            post_date TEXT, post_time TEXT, format TEXT, topic TEXT,
            caption TEXT, reach INTEGER, likes INTEGER, shares INTEGER,
            comments_count INTEGER, engagement_rate REAL
        )
    """)
    cur.executemany(
        """INSERT INTO posts VALUES (:post_id, :subject_id, :subject_name, :platform,
           :post_date, :post_time, :format, :topic, :caption, :reach, :likes, :shares,
           :comments_count, :engagement_rate)""",
        posts,
    )

    cur.execute("DROP TABLE IF EXISTS comments")
    cur.execute("""
        CREATE TABLE comments (
            comment_id TEXT PRIMARY KEY,
            post_id TEXT, subject_id TEXT, platform TEXT,
            post_date TEXT, topic TEXT, text TEXT, seed_sentiment TEXT
        )
    """)
    cur.executemany(
        """INSERT INTO comments VALUES (:comment_id, :post_id, :subject_id, :platform,
           :post_date, :topic, :text, :seed_sentiment)""",
        comments,
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)
    posts, comments = generate_dataset()
    save_to_sqlite(posts, comments)
    print(f"Generated {len(posts)} posts and {len(comments)} comments -> {DB_PATH}")
