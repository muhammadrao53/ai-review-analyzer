"""
AI Customer Review Analyzer
---------------------------
Reads customer reviews from a CSV, uses AI to tag each one with
sentiment, topic and urgency, then produces an Excel report,
a chart and a short management summary.

Run in demo mode (free, no API key, simple keyword rules):
    python analyzer.py

Run with free real AI (needs GEMINI_API_KEY set):
    python analyzer.py --mode gemini

Run with Claude (paid, needs ANTHROPIC_API_KEY set):
    python analyzer.py --mode claude
"""

import argparse
import os
import time
from typing import Literal

import matplotlib
matplotlib.use("Agg")  # draw charts to files, no screen needed
import matplotlib.pyplot as plt
import pandas as pd
from pydantic import BaseModel

INPUT_FILE = "data/reviews.csv"
OUTPUT_DIR = "output"

# Claude Opus 5.5 is the most capable. "claude-haiku-5-5" is ~40x cheaper
# and good enough for simple tagging like this; try both and compare.
MODEL = "claude-opus-5-5"

TOPICS = ["product quality", "delivery", "customer service", "price",
          "wrong or fake item", "safety", "returns and refunds", "other"]


# ---------------------------------------------------------------------------
# 1. The shape of the answer we want from the AI (structured output)
# ---------------------------------------------------------------------------
class ReviewAnalysis(BaseModel):
    sentiment: Literal["positive", "neutral", "negative"]
    topic: Literal["product quality", "delivery", "customer service", "price",
                   "wrong or fake item", "safety", "returns and refunds", "other"]
    urgency: int  # 1 = no action needed ... 5 = act today
    summary: str  # one short sentence


PROMPT = """You are a customer-experience analyst for an online store in Pakistan.
Analyze this customer review.

- sentiment: positive, neutral or negative
- topic: the single main topic of the review
- urgency: 1-5, how quickly the business should act
  (5 = safety risk or fraud, 4 = angry customer wanting a refund,
   3 = clear complaint, 2 = minor issue, 1 = happy customer)
- summary: one short sentence describing the issue or praise

Product: {product}
Rating: {rating}/5
Review: {text}"""


# ---------------------------------------------------------------------------
# 2a. Demo mode: simple keyword rules (free, lets you test the pipeline)
# ---------------------------------------------------------------------------
KEYWORDS = {
    "safety": ["hot", "burning", "spark", "dangerous", "smell"],
    "wrong or fake item": ["fake", "wrong item", "not the original"],
    "returns and refunds": ["refund", "money back", "return", "warranty"],
    "delivery": ["deliver", "days to arrive", "late", "box was damaged"],
    "customer service": ["support", "helpline", "replied", "customer service"],
    "price": ["price", "rupees", "value for money"],
}


def analyze_demo(product: str, rating: int, text: str) -> ReviewAnalysis:
    lower = text.lower()
    topic = next((t for t, words in KEYWORDS.items()
                  if any(w in lower for w in words)), "product quality")
    sentiment = "positive" if rating >= 4 else "neutral" if rating == 3 else "negative"
    urgency = {"safety": 5, "wrong or fake item": 4, "returns and refunds": 4}.get(
        topic, {1: 3, 2: 3, 3: 2}.get(rating, 1))
    return ReviewAnalysis(sentiment=sentiment, topic=topic, urgency=urgency,
                          summary=text[:80])


# ---------------------------------------------------------------------------
# 2b. Claude mode: the real AI call (paid)
# ---------------------------------------------------------------------------
SUMMARY_PROMPT = ("Here are analyzed customer reviews:\n\n{table}\n"
                  "Write a management summary in under 200 words: "
                  "top 3 problems with evidence, which product needs attention "
                  "first, and 3 concrete recommended actions. Use markdown.")


def results_table(df: pd.DataFrame) -> str:
    cols = ["product", "rating", "sentiment", "topic", "urgency", "summary"]
    return df[cols].to_csv(index=False)


def make_claude_analyzer(api_key=None):
    """Returns two functions: analyze(one review) and summarize(all results)."""
    import anthropic
    # With no api_key given, reads ANTHROPIC_API_KEY from the environment
    client = anthropic.Anthropic(api_key=api_key)

    def analyze_claude(product: str, rating: int, text: str) -> ReviewAnalysis:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=2000,
            output_config={"effort": "low"},  # simple task -> low effort = cheaper
            messages=[{"role": "user", "content": PROMPT.format(
                product=product, rating=rating, text=text)}],
            output_format=ReviewAnalysis,  # forces valid JSON in our shape
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            return ReviewAnalysis(sentiment="neutral", topic="other",
                                  urgency=1, summary="(AI could not analyze)")
        return response.parsed_output

    def summarize_claude(df: pd.DataFrame) -> str:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            output_config={"effort": "medium"},
            messages=[{"role": "user",
                       "content": SUMMARY_PROMPT.format(table=results_table(df))}],
        )
        return "".join(b.text for b in response.content if b.type == "text")

    return analyze_claude, summarize_claude


# ---------------------------------------------------------------------------
# 2c. Gemini mode: real AI with Google's FREE tier (key from aistudio.google.com)
# ---------------------------------------------------------------------------
# "gemini-flash-latest" always points to Google's current Flash model.
GEMINI_MODEL = "gemini-flash-latest"


def make_gemini_analyzer(api_key=None):
    """Same idea as make_claude_analyzer, but with Google's Gemini."""
    from google import genai
    from google.genai import errors, types
    # With no api_key given, reads GEMINI_API_KEY from the environment
    client = genai.Client(api_key=api_key)

    def call(prompt: str, config=None):
        # The free tier allows only a few requests per minute.
        # If we hit the limit (error 429), wait and try again.
        for attempt in range(5):
            try:
                return client.models.generate_content(
                    model=GEMINI_MODEL, contents=prompt, config=config)
            except errors.APIError as e:
                if e.code != 429 or attempt == 4:
                    raise
                print("  Free-tier limit reached, waiting 30 seconds...")
                time.sleep(30)

    def analyze_gemini(product: str, rating: int, text: str) -> ReviewAnalysis:
        response = call(
            PROMPT.format(product=product, rating=rating, text=text),
            types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReviewAnalysis,  # forces valid JSON in our shape
            ),
        )
        if response.parsed is None:
            return ReviewAnalysis(sentiment="neutral", topic="other",
                                  urgency=1, summary="(AI could not analyze)")
        return response.parsed

    def summarize_gemini(df: pd.DataFrame) -> str:
        return call(SUMMARY_PROMPT.format(table=results_table(df))).text

    return analyze_gemini, summarize_gemini


def write_basic_summary(df: pd.DataFrame) -> str:
    """Demo-mode summary built with plain pandas (no AI)."""
    neg = df[df.sentiment == "negative"]
    lines = [
        "# Review Summary (demo mode)",
        f"- Reviews analyzed: {len(df)}",
        f"- Negative: {len(neg)} ({len(neg) / len(df):.0%})",
        f"- Average rating: {df.rating.mean():.1f}/5",
        "",
        "## Top complaint topics",
        *[f"- {t}: {n}" for t, n in neg.topic.value_counts().head(3).items()],
        "",
        "## Urgent reviews (urgency 4-5)",
        *[f"- #{r.review_id} {r.product}: {r.review_text}"
          for r in df[df.urgency >= 4].itertuples()],
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 3. The automation pipeline
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["demo", "gemini", "claude"], default="demo")
    args = parser.parse_args()

    df = pd.read_csv(INPUT_FILE)
    print(f"Loaded {len(df)} reviews. Mode: {args.mode}")

    if args.mode == "claude":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("Set ANTHROPIC_API_KEY first (see README.md).")
        analyze, summarize = make_claude_analyzer()
    elif args.mode == "gemini":
        if not os.environ.get("GEMINI_API_KEY"):
            raise SystemExit("Set GEMINI_API_KEY first (see README.md).")
        analyze, summarize = make_gemini_analyzer()
    else:
        analyze, summarize = analyze_demo, write_basic_summary

    results = []
    for i, row in enumerate(df.itertuples(), start=1):
        result = analyze(row.product, row.rating, row.review_text)
        results.append(result.model_dump())
        print(f"  [{i}/{len(df)}] {row.product}: {result.sentiment}, "
              f"{result.topic}, urgency {result.urgency}")

    df = pd.concat([df, pd.DataFrame(results)], axis=1)
    df = df.sort_values("urgency", ascending=False)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Excel report with two sheets
    with pd.ExcelWriter(f"{OUTPUT_DIR}/review_report.xlsx") as writer:
        df.to_excel(writer, sheet_name="All reviews", index=False)
        pivot = pd.crosstab(df["product"], df["sentiment"])
        pivot.to_excel(writer, sheet_name="Sentiment by product")

    # Chart of complaint topics
    neg = df[df.sentiment == "negative"]
    neg.topic.value_counts().sort_values().plot.barh(color="#c0392b")
    plt.title("What customers complain about")
    plt.xlabel("Number of negative reviews")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/complaints_chart.png", dpi=150)

    # Management summary
    summary = summarize(df)
    with open(f"{OUTPUT_DIR}/summary.md", "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"\nDone! See the '{OUTPUT_DIR}' folder:")
    print("  review_report.xlsx, complaints_chart.png, summary.md")


if __name__ == "__main__":
    main()
