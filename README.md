# AI/ML Social Media Intelligence & Competitor Dashboard

An end-to-end Streamlit dashboard that tracks, analyzes, and benchmarks
social media activity for a reference political leader (configured here
as **Tejasvi Surya**) against 3 tracked competitors, across five
platforms: X, Instagram, Facebook, YouTube, and LinkedIn.

> **Data note:** This repo ships with a **synthetic** 30-day dataset
> (`data_generator.py`) so the UI is fully runnable and testable with
> zero API keys and zero rate-limit risk. Competitor accounts are
> generic placeholders (`Competitor A/B/C`) — swap in real handles in
> `config.py` only once you've wired up compliant, credentialed access
> in `scraper.py` (see "Going live" below). No fabricated statements
> are ever attributed to a real person in this codebase — all sample
> captions/comments are clearly templated placeholder text.

## Features

- **Multi-platform analytics** across X, Instagram, Facebook, YouTube, LinkedIn
- **Sentiment engine** (Positive/Negative/Neutral) over sampled top comments (50–100/post)
- **Topic categorization** into Civic Issues, Traffic & Mobility, Infrastructure,
  Public Safety, Development & Economy, Education, Health, Governance & Policy
- **High-risk alerts** for negative-sentiment spikes by topic/day/subject
- **Competitor Watch**: post frequency, avg. reach, engagement rate, format
  performance, and platform-strength radar chart
- **Executive dashboard**: KPIs, 30-day trends, top-performing posts

## Project structure

```
app.py             Streamlit dashboard (UI, charts, tabs)
scraper.py          Data-access layer: synthetic loader + live-API stubs
nlp_engine.py        Sentiment analysis, topic classification, risk alerts
data_generator.py    Synthetic 30-day dataset generator -> SQLite
config.py            Subjects, platforms, topic taxonomy, formats
data/social_intel.db  Generated SQLite dataset (created by data_generator.py)
requirements.txt
```

## Quick start

```bash
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt

python data_generator.py      # generates data/social_intel.db
streamlit run app.py          # opens the dashboard in your browser
```

## NLP pipeline

`nlp_engine.py` auto-selects the strongest backend available, with
graceful fallback so the app never crashes on missing dependencies:

| Task       | Preferred backend                                   | Fallback (zero-dependency) |
|------------|------------------------------------------------------|-----------------------------|
| Sentiment  | `cardiffnlp/twitter-roberta-base-sentiment` (HF)     | `vaderSentiment` -> built-in lexicon scorer |
| Topics     | `facebook/bart-large-mnli` zero-shot (HF)            | Keyword/rule-based classifier |

To enable the heavier backends, uncomment `transformers`/`torch` in
`requirements.txt` and reinstall — no code changes needed.

## Going live (real scraping/APIs)

`scraper.py` is synthetic-by-default (`SOCIAL_INTEL_MODE=synthetic`).
Each platform has a stub function (`fetch_x_posts`, `fetch_instagram_posts`,
etc.) documenting the recommended **official API** route:

- **X**: X API v2 (recent search / user timeline), developer account required
- **Instagram / Facebook**: Meta Graph API (Business/Creator account +
  app review for pages you don't own)
- **YouTube**: YouTube Data API v3 (generous free quota, well-supported)
- **LinkedIn**: LinkedIn Marketing/Partner API (most restrictive; consider
  manual export fallback)

Fill in real credentials and logic in these functions, then run with:

```bash
SOCIAL_INTEL_MODE=live streamlit run app.py
```

**Important:** Unofficial scraping libraries (e.g. generic headless-browser
scrapers) frequently violate platform Terms of Service and can break
without notice. Prefer official APIs, respect each platform's rate
limits and data-use policies, and only track accounts/content you have
a legitimate basis to monitor (this is standard practice for campaign
analytics, PR/media monitoring, and academic research on **public**
posts — not private data or non-public accounts).

## Customizing for your own subjects

Edit `config.py`:
- `REFERENCE_LEADER` — name, role, and real handles per platform
- `COMPETITORS` — add/rename competitors and real handles
- `TOPIC_CATEGORIES` / `TOPIC_KEYWORDS` — adjust the issue taxonomy to
  your region's civic priorities

## Screenshots

After running `streamlit run app.py`, capture screenshots of each tab
(Executive Overview, Competitor Watch, Sentiment & Topics, High-Risk
Alerts, Top Posts) for your submission deliverable.
