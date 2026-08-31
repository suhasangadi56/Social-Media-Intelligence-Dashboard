"""
nlp_engine.py
Sentiment + topic-categorization pipeline for the dashboard.

Design goals:
- Work out of the box with ZERO extra dependencies (pure-python fallback
  lexicon/rule engine), so the dashboard is runnable immediately.
- Automatically upgrade to stronger backends if they're installed:
    * vaderSentiment          -> better sentiment scoring
    * transformers (RoBERTa)  -> cardiffnlp/twitter-roberta-base-sentiment
                                  for sentiment, and zero-shot-classification
                                  (facebook/bart-large-mnli) for topics
- Never crash the app if a heavy dependency is missing -- degrade gracefully
  and log which backend is active.

Usage:
    from nlp_engine import SentimentAnalyzer, TopicClassifier, RiskAlertEngine

    sa = SentimentAnalyzer()
    sa.analyze("This flyover project has been a disaster for months.")
    -> {"label": "Negative", "score": -0.62}

    tc = TopicClassifier()
    tc.classify("The new metro line inauguration is finally happening")
    -> "Traffic & Mobility"
"""

from __future__ import annotations
import re
from collections import Counter
from typing import Dict, List, Tuple

from config import TOPIC_CATEGORIES, TOPIC_KEYWORDS

# ---------------------------------------------------------------------------
# Sentiment Analyzer
# ---------------------------------------------------------------------------

# Small built-in polarity lexicon used as a zero-dependency fallback.
# (Deliberately compact -- swap in VADER / RoBERTa for production use.)
_POSITIVE_WORDS = {
    "great", "good", "excellent", "amazing", "well done", "thank you",
    "thanks", "support", "proud", "progress", "improved", "improvement",
    "fantastic", "appreciate", "happy", "impressive", "welcome", "kudos",
    "love", "best", "helpful", "outstanding", "inspiring", "success",
    "successful", "grateful", "awesome", "brilliant", "positive", "trust",
}
_NEGATIVE_WORDS = {
    "bad", "worst", "terrible", "poor", "fail", "failed", "failure",
    "disappointed", "disappointing", "angry", "unsafe", "unacceptable",
    "corrupt", "corruption", "scam", "shameful", "shame", "neglect",
    "neglected", "ignored", "broken", "disaster", "problem", "issue",
    "complaint", "complaints", "outrage", "protest", "delay", "delayed",
    "pothole", "garbage", "unhappy", "frustrated", "waste", "hate",
    "useless", "fake", "lies", "lie", "negligence", "concern", "concerned",
}
_NEGATION_WORDS = {"not", "no", "never", "n't", "without", "hardly"}


class SentimentAnalyzer:
    """Sentiment scorer with automatic backend selection."""

    def __init__(self, prefer_backend: str = "auto"):
        self.backend = "lexicon_fallback"
        self._vader = None
        self._hf_pipeline = None

        if prefer_backend in ("auto", "vader"):
            try:
                from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
                self._vader = SentimentIntensityAnalyzer()
                self.backend = "vader"
            except ImportError:
                pass

        if prefer_backend in ("auto", "roberta"):
            try:
                from transformers import pipeline
                self._hf_pipeline = pipeline(
                    "sentiment-analysis",
                    model="cardiffnlp/twitter-roberta-base-sentiment",
                )
                self.backend = "roberta"
            except Exception:
                pass

    def analyze(self, text: str) -> Dict[str, float]:
        text = (text or "").strip()
        if not text:
            return {"label": "Neutral", "score": 0.0}

        if self.backend == "roberta" and self._hf_pipeline is not None:
            try:
                result = self._hf_pipeline(text[:512])[0]
                label_map = {"LABEL_0": "Negative", "LABEL_1": "Neutral", "LABEL_2": "Positive"}
                label = label_map.get(result["label"], result["label"])
                score = result["score"] if label == "Positive" else -result["score"] if label == "Negative" else 0.0
                return {"label": label, "score": round(float(score), 3)}
            except Exception:
                pass  # fall through to next backend

        if self.backend == "vader" and self._vader is not None:
            vs = self._vader.polarity_scores(text)
            compound = vs["compound"]
            label = "Positive" if compound >= 0.05 else "Negative" if compound <= -0.05 else "Neutral"
            return {"label": label, "score": round(compound, 3)}

        return self._lexicon_fallback(text)

    def _lexicon_fallback(self, text: str) -> Dict[str, float]:
        tokens = re.findall(r"[a-zA-Z']+", text.lower())
        pos_hits = 0
        neg_hits = 0
        for i, tok in enumerate(tokens):
            negated = i > 0 and tokens[i - 1] in _NEGATION_WORDS
            if tok in _POSITIVE_WORDS:
                neg_hits += 1 if negated else 0
                pos_hits += 0 if negated else 1
            elif tok in _NEGATIVE_WORDS:
                pos_hits += 1 if negated else 0
                neg_hits += 0 if negated else 1

        total = pos_hits + neg_hits
        if total == 0:
            return {"label": "Neutral", "score": 0.0}
        score = (pos_hits - neg_hits) / max(total, 1)
        label = "Positive" if score > 0.15 else "Negative" if score < -0.15 else "Neutral"
        return {"label": label, "score": round(score, 3)}

    def analyze_batch(self, texts: List[str]) -> List[Dict[str, float]]:
        return [self.analyze(t) for t in texts]


# ---------------------------------------------------------------------------
# Topic Classifier
# ---------------------------------------------------------------------------

class TopicClassifier:
    """Keyword-driven topic classifier with optional zero-shot upgrade."""

    def __init__(self, prefer_backend: str = "auto"):
        self.backend = "keyword_fallback"
        self._zero_shot = None

        if prefer_backend in ("auto", "zero_shot"):
            try:
                from transformers import pipeline
                self._zero_shot = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli",
                )
                self.backend = "zero_shot"
            except Exception:
                pass

    def classify(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return "General / Other"

        if self.backend == "zero_shot" and self._zero_shot is not None:
            try:
                result = self._zero_shot(text, TOPIC_CATEGORIES)
                return result["labels"][0]
            except Exception:
                pass  # fall through

        return self._keyword_fallback(text)

    def _keyword_fallback(self, text: str) -> str:
        lower = text.lower()
        scores = Counter()
        for topic, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                if kw in lower:
                    scores[topic] += 1
        if not scores:
            return "General / Other"
        return scores.most_common(1)[0][0]

    def classify_batch(self, texts: List[str]) -> List[str]:
        return [self.classify(t) for t in texts]


# ---------------------------------------------------------------------------
# Risk / Alert engine
# ---------------------------------------------------------------------------

class RiskAlertEngine:
    """
    Flags spikes in negative sentiment or emerging grievances per topic.
    Operates on a pandas DataFrame of scored comments (post_date, topic,
    sentiment_label columns required).
    """

    def __init__(self, negative_share_threshold: float = 0.22, min_volume: int = 20):
        self.negative_share_threshold = negative_share_threshold
        self.min_volume = min_volume

    def find_alerts(self, df, subject_col="subject_id", date_col="post_date",
                     topic_col="topic", sentiment_col="sentiment_label"):
        import pandas as pd

        if df.empty:
            return pd.DataFrame(columns=[subject_col, date_col, topic_col,
                                          "volume", "negative_share", "severity"])

        grouped = (
            df.groupby([subject_col, date_col, topic_col])[sentiment_col]
            .agg(volume="count",
                 negative=lambda s: (s == "Negative").sum())
            .reset_index()
        )
        grouped["negative_share"] = grouped["negative"] / grouped["volume"]
        alerts = grouped[
            (grouped["volume"] >= self.min_volume)
            & (grouped["negative_share"] >= self.negative_share_threshold)
        ].copy()

        def severity(row):
            if row["negative_share"] >= 0.35:
                return "High"
            if row["negative_share"] >= 0.28:
                return "Medium"
            return "Low"

        if not alerts.empty:
            alerts["severity"] = alerts.apply(severity, axis=1)
            alerts = alerts.sort_values(["negative_share", "volume"], ascending=False)
        return alerts.drop(columns=["negative"], errors="ignore")
