"""
app.py
Streamlit entry point for the AI/ML Social Media Intelligence &
Competitor Dashboard.

Run with:
    streamlit run app.py

First-time setup:
    python data_generator.py   # builds the synthetic demo dataset
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import (
    ALL_SUBJECTS, SUBJECT_BY_ID, REFERENCE_LEADER, COMPETITORS,
    PLATFORMS, PLATFORM_DISPLAY, TOPIC_CATEGORIES,
)
import scraper
from nlp_engine import SentimentAnalyzer, TopicClassifier, RiskAlertEngine

st.set_page_config(
    page_title="Social Media Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Cached loaders
# ---------------------------------------------------------------------------

@st.cache_resource
def get_engines():
    return SentimentAnalyzer(), TopicClassifier(), RiskAlertEngine()


@st.cache_data(ttl=600)
def load_scored_data(subject_ids, platforms, start_date, end_date):
    posts = scraper.get_posts(subject_ids, platforms, start_date, end_date)
    if posts.empty:
        return posts, pd.DataFrame()

    comments = scraper.get_comments(post_ids=posts["post_id"].tolist())
    sa, _, _ = get_engines()
    if not comments.empty:
        scored = comments["text"].apply(sa.analyze)
        comments["sentiment_label"] = scored.apply(lambda x: x["label"])
        comments["sentiment_score"] = scored.apply(lambda x: x["score"])
    return posts, comments


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------

st.sidebar.title("📊 Filters")
st.sidebar.caption("Data source: synthetic demo dataset" if scraper.USE_SYNTHETIC
                    else "Data source: LIVE (real platform APIs)")

subject_labels = {s["id"]: s["display_name"] for s in ALL_SUBJECTS}
selected_subject_ids = st.sidebar.multiselect(
    "Subjects to compare",
    options=list(subject_labels.keys()),
    default=list(subject_labels.keys()),
    format_func=lambda sid: subject_labels[sid],
)

selected_platforms = st.sidebar.multiselect(
    "Platforms",
    options=PLATFORMS,
    default=PLATFORMS,
    format_func=lambda p: PLATFORM_DISPLAY[p],
)

date_range = st.sidebar.date_input(
    "Date range (last 30 days available)",
    value=(),
)
start_date = date_range[0] if len(date_range) == 2 else None
end_date = date_range[1] if len(date_range) == 2 else None

if not selected_subject_ids or not selected_platforms:
    st.warning("Select at least one subject and one platform in the sidebar.")
    st.stop()

posts, comments = load_scored_data(
    tuple(selected_subject_ids), tuple(selected_platforms), start_date, end_date
)

if posts.empty:
    st.warning("No data for the selected filters. Try widening the date range or "
                "run `python data_generator.py` if you haven't yet.")
    st.stop()

subject_color = {s["id"]: s["color"] for s in ALL_SUBJECTS}

# ---------------------------------------------------------------------------
# Header + top-line KPIs
# ---------------------------------------------------------------------------

st.title("AI/ML Social Media Intelligence & Competitor Dashboard")
st.caption(
    f"Reference leader: **{REFERENCE_LEADER['display_name']}** vs. "
    f"{len(COMPETITORS)} tracked competitors · {len(PLATFORMS)} platforms"
)

ref_posts = posts[posts["subject_id"] == "reference_leader"]
kpi_cols = st.columns(4)
kpi_cols[0].metric("Total Posts (selection)", f"{len(posts):,}")
kpi_cols[1].metric("Reference Leader Reach", f"{ref_posts['reach'].sum():,}")
kpi_cols[2].metric(
    "Reference Leader Avg. Engagement Rate",
    f"{ref_posts['engagement_rate'].mean()*100:.2f}%" if not ref_posts.empty else "—",
)
if not comments.empty:
    ref_comments = comments[comments["subject_id"] == "reference_leader"]
    pos_share = (ref_comments["sentiment_label"] == "Positive").mean() if not ref_comments.empty else 0
    kpi_cols[3].metric("Reference Leader Positive Sentiment", f"{pos_share*100:.1f}%")
else:
    kpi_cols[3].metric("Reference Leader Positive Sentiment", "—")

tabs = st.tabs(["Executive Overview", "Competitor Watch", "Sentiment & Topics",
                 "High-Risk Alerts", "Top Posts"])

# ---------------------------------------------------------------------------
# Tab 1: Executive Overview
# ---------------------------------------------------------------------------

with tabs[0]:
    st.subheader("30-Day Reach & Engagement Trend")
    daily = (
        posts.groupby(["post_date", "subject_id"])
        .agg(reach=("reach", "sum"), engagement_rate=("engagement_rate", "mean"))
        .reset_index()
    )
    daily["subject_name"] = daily["subject_id"].map(subject_labels)

    fig_reach = px.line(
        daily, x="post_date", y="reach", color="subject_name",
        title="Daily Reach by Subject",
        color_discrete_map={subject_labels[k]: v for k, v in subject_color.items()},
    )
    st.plotly_chart(fig_reach, use_container_width=True)

    fig_eng = px.line(
        daily, x="post_date", y="engagement_rate", color="subject_name",
        title="Daily Avg. Engagement Rate by Subject",
        color_discrete_map={subject_labels[k]: v for k, v in subject_color.items()},
    )
    fig_eng.update_yaxes(tickformat=".1%")
    st.plotly_chart(fig_eng, use_container_width=True)

    st.subheader("Platform Mix")
    platform_mix = posts.groupby(["subject_id", "platform"]).size().reset_index(name="posts")
    platform_mix["subject_name"] = platform_mix["subject_id"].map(subject_labels)
    fig_mix = px.bar(
        platform_mix, x="subject_name", y="posts", color="platform",
        title="Post Volume by Platform", barmode="stack",
    )
    st.plotly_chart(fig_mix, use_container_width=True)

# ---------------------------------------------------------------------------
# Tab 2: Competitor Watch
# ---------------------------------------------------------------------------

with tabs[1]:
    st.subheader("Competitor Benchmarking")

    bench = (
        posts.groupby("subject_id")
        .agg(
            post_frequency=("post_id", "count"),
            avg_reach=("reach", "mean"),
            avg_engagement_rate=("engagement_rate", "mean"),
            total_likes=("likes", "sum"),
            total_shares=("shares", "sum"),
        )
        .reset_index()
    )
    bench["subject_name"] = bench["subject_id"].map(subject_labels)
    display_bench = bench[["subject_name", "post_frequency", "avg_reach",
                            "avg_engagement_rate", "total_likes", "total_shares"]].copy()
    display_bench["avg_reach"] = display_bench["avg_reach"].round(0).astype(int)
    display_bench["avg_engagement_rate"] = (display_bench["avg_engagement_rate"] * 100).round(2)
    display_bench.columns = ["Subject", "Post Frequency", "Avg. Reach",
                              "Avg. Engagement Rate (%)", "Total Likes", "Total Shares"]
    st.dataframe(display_bench.sort_values("Avg. Reach", ascending=False),
                 use_container_width=True, hide_index=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Top-Performing Format by Subject**")
        fmt_perf = (
            posts.groupby(["subject_id", "format"])["engagement_rate"]
            .mean().reset_index()
        )
        fmt_perf["subject_name"] = fmt_perf["subject_id"].map(subject_labels)
        fig_fmt = px.bar(
            fmt_perf, x="format", y="engagement_rate", color="subject_name",
            barmode="group", title="Avg. Engagement Rate by Post Format",
        )
        fig_fmt.update_yaxes(tickformat=".1%")
        st.plotly_chart(fig_fmt, use_container_width=True)

    with col_b:
        st.markdown("**Platform Strength (share of subject's total reach)**")
        platform_strength = (
            posts.groupby(["subject_id", "platform"])["reach"].sum().reset_index()
        )
        platform_strength["subject_name"] = platform_strength["subject_id"].map(subject_labels)
        fig_radar = go.Figure()
        for sid in selected_subject_ids:
            sub_df = platform_strength[platform_strength["subject_id"] == sid]
            sub_df = sub_df.set_index("platform").reindex(PLATFORMS).fillna(0)
            fig_radar.add_trace(go.Scatterpolar(
                r=sub_df["reach"].tolist(),
                theta=[PLATFORM_DISPLAY[p] for p in PLATFORMS],
                fill="toself",
                name=subject_labels[sid],
                line_color=subject_color[sid],
            ))
        fig_radar.update_layout(title="Reach by Platform (radar)")
        st.plotly_chart(fig_radar, use_container_width=True)

# ---------------------------------------------------------------------------
# Tab 3: Sentiment & Topics
# ---------------------------------------------------------------------------

with tabs[2]:
    if comments.empty:
        st.info("No comment-level data available for the current selection.")
    else:
        st.subheader("Sentiment Breakdown by Subject")
        sent_mix = (
            comments.groupby(["subject_id", "sentiment_label"]).size()
            .reset_index(name="count")
        )
        sent_mix["subject_name"] = sent_mix["subject_id"].map(subject_labels)
        fig_sent = px.bar(
            sent_mix, x="subject_name", y="count", color="sentiment_label",
            title="Comment Sentiment Mix", barmode="stack",
            color_discrete_map={"Positive": "#2CA58D", "Neutral": "#B0B0B0", "Negative": "#D64545"},
        )
        st.plotly_chart(fig_sent, use_container_width=True)

        col_c, col_d = st.columns(2)
        with col_c:
            st.markdown("**Topic Distribution (all selected subjects)**")
            topic_dist = comments["topic"].value_counts().reset_index()
            topic_dist.columns = ["topic", "count"]
            fig_topic = px.pie(topic_dist, names="topic", values="count", hole=0.4)
            st.plotly_chart(fig_topic, use_container_width=True)

        with col_d:
            st.markdown("**Negative Sentiment Share by Topic**")
            topic_sent = (
                comments.groupby("topic")["sentiment_label"]
                .apply(lambda s: (s == "Negative").mean())
                .reset_index(name="negative_share")
                .sort_values("negative_share", ascending=False)
            )
            fig_topic_neg = px.bar(
                topic_sent, x="topic", y="negative_share",
                title="Negative Share by Topic", color="negative_share",
                color_continuous_scale="Reds",
            )
            fig_topic_neg.update_yaxes(tickformat=".0%")
            fig_topic_neg.update_xaxes(tickangle=30)
            st.plotly_chart(fig_topic_neg, use_container_width=True)

# ---------------------------------------------------------------------------
# Tab 4: High-Risk Alerts
# ---------------------------------------------------------------------------

with tabs[3]:
    st.subheader("Emerging Grievance / Negative-Sentiment Spike Alerts")
    if comments.empty:
        st.info("No comment-level data available for the current selection.")
    else:
        _, _, rae = get_engines()
        merged = comments.merge(
            posts[["post_id", "post_date"]].drop_duplicates(), on="post_id",
            how="left", suffixes=("", "_post"),
        )
        date_col = "post_date_post" if "post_date_post" in merged.columns else "post_date"
        alerts = rae.find_alerts(merged, date_col=date_col)

        if alerts.empty:
            st.success("No high-risk sentiment spikes detected for the current filters.")
        else:
            alerts["subject_name"] = alerts["subject_id"].map(subject_labels)
            display_alerts = alerts[["subject_name", date_col, "topic", "volume",
                                      "negative_share", "severity"]].copy()
            display_alerts["negative_share"] = (display_alerts["negative_share"] * 100).round(1)
            display_alerts.columns = ["Subject", "Date", "Topic", "Comment Volume",
                                       "Negative Share (%)", "Severity"]

            def highlight_severity(val):
                colors = {"High": "background-color:#f8d7da", "Medium": "background-color:#fff3cd",
                          "Low": "background-color:#d1ecf1"}
                return colors.get(val, "")

            st.dataframe(
                display_alerts.sort_values("Negative Share (%)", ascending=False),
                use_container_width=True, hide_index=True,
            )
            st.caption(
                "Severity: High ≥35% negative comments, Medium ≥28%, Low ≥22% "
                "(within a topic/day/subject group, min. 20 comments)."
            )

# ---------------------------------------------------------------------------
# Tab 5: Top Posts
# ---------------------------------------------------------------------------

with tabs[4]:
    st.subheader("Top-Performing Posts")
    posts["engagements"] = posts["likes"] + posts["shares"] + posts["comments_count"]
    posts["subject_name"] = posts["subject_id"].map(subject_labels)
    top_posts = posts.sort_values("engagements", ascending=False).head(20)
    display_top = top_posts[["subject_name", "platform", "post_date", "format",
                              "topic", "caption", "reach", "engagements", "engagement_rate"]].copy()
    display_top["platform"] = display_top["platform"].map(PLATFORM_DISPLAY)
    display_top["engagement_rate"] = (display_top["engagement_rate"] * 100).round(2)
    display_top.columns = ["Subject", "Platform", "Date", "Format", "Topic",
                            "Caption", "Reach", "Engagements", "Engagement Rate (%)"]
    st.dataframe(display_top, use_container_width=True, hide_index=True)

st.sidebar.divider()
st.sidebar.caption(
    "Synthetic demo data is generated for UI/UX testing only and does not "
    "represent real social media activity. Switch to live mode by wiring up "
    "scraper.py to official platform APIs."
)
