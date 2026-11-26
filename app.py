"""
AI Customer Review Analyzer - Streamlit web app
-----------------------------------------------
A web page version of analyzer.py: upload a CSV, tag every review,
see the results and charts, and download the Excel report.

Run it:
    streamlit run app.py
"""

import io
import os

import pandas as pd
import streamlit as st

# Reuse the logic we already wrote in analyzer.py (no copy-paste!)
from analyzer import (GEMINI_MODEL, INPUT_FILE, MODEL, analyze_demo,
                      make_claude_analyzer, make_gemini_analyzer,
                      write_basic_summary)

REQUIRED_COLUMNS = ["review_id", "product", "rating", "review_text"]

st.set_page_config(page_title="AI Review Analyzer", page_icon="📊", layout="wide")
st.title("📊 AI Customer Review Analyzer")
st.write("Upload customer reviews and AI tags each one with "
         "**sentiment**, **topic** and **urgency**.")


# ---------------------------------------------------------------------------
# 1. Sidebar: settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    mode = st.radio("Mode", ["demo", "gemini", "claude"],
                    format_func=lambda m: {"demo": "Demo (free keyword rules)",
                                           "gemini": "Gemini (free real AI)",
                                           "claude": "Claude (paid real AI)"}[m])
    api_key = None
    if mode != "demo":
        key_name = {"gemini": "GEMINI_API_KEY", "claude": "ANTHROPIC_API_KEY"}[mode]
        api_key = (st.text_input(f"{mode.title()} API key", type="password",
                                 help="Not saved anywhere. Leave empty to use "
                                      f"{key_name} from your terminal.")
                   or os.environ.get(key_name))
        st.caption(f"Model: `{GEMINI_MODEL if mode == 'gemini' else MODEL}`")
        if mode == "gemini":
            st.caption("Free key: aistudio.google.com → Get API key. "
                       "Free tier is slow (few requests per minute).")


# ---------------------------------------------------------------------------
# 2. Load the data: an uploaded CSV, or the sample file
# ---------------------------------------------------------------------------
uploaded = st.file_uploader("Upload a CSV with columns: "
                            + ", ".join(REQUIRED_COLUMNS), type="csv")
df = pd.read_csv(uploaded) if uploaded else pd.read_csv(INPUT_FILE)
st.caption(f"Using **{uploaded.name if uploaded else 'sample data'}** "
           f"({len(df)} reviews)")

missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
if missing:
    st.error(f"Your CSV is missing these columns: {', '.join(missing)}")
    st.stop()

with st.expander("Preview the raw reviews"):
    st.dataframe(df, hide_index=True)


# ---------------------------------------------------------------------------
# 3. Run the analysis when the button is clicked
# ---------------------------------------------------------------------------
if st.button("🚀 Analyze reviews", type="primary"):
    if mode != "demo" and not api_key:
        st.error("Enter your API key in the sidebar first.")
        st.stop()
    if mode == "claude":
        analyze, summarize = make_claude_analyzer(api_key)
    elif mode == "gemini":
        analyze, summarize = make_gemini_analyzer(api_key)
    else:
        analyze, summarize = analyze_demo, write_basic_summary

    progress = st.progress(0, text="Starting...")
    results = []
    try:
        for i, row in enumerate(df.itertuples(), start=1):
            result = analyze(row.product, row.rating, row.review_text)
            results.append(result.model_dump())
            progress.progress(i / len(df), text=f"Analyzed {i}/{len(df)} reviews")
        tagged = pd.concat([df, pd.DataFrame(results)], axis=1)
        tagged = tagged.sort_values("urgency", ascending=False)
        with st.spinner("Writing the management summary..."):
            summary = summarize(tagged)
    except Exception as e:  # e.g. wrong API key, no credit, no internet
        st.error(f"Something went wrong: {e}")
        st.stop()

    # st.session_state keeps results when the page reruns (e.g. on a click)
    st.session_state.tagged = tagged
    st.session_state.summary = summary
    progress.empty()


# ---------------------------------------------------------------------------
# 4. Show the results
# ---------------------------------------------------------------------------
if "tagged" not in st.session_state:
    st.info("Click **Analyze reviews** to start.")
    st.stop()

tagged = st.session_state.tagged
neg = tagged[tagged.sentiment == "negative"]

# Key numbers
c1, c2, c3, c4 = st.columns(4)
c1.metric("Reviews", len(tagged))
c2.metric("Negative", f"{len(neg) / len(tagged):.0%}")
c3.metric("Average rating", f"{tagged.rating.mean():.1f} / 5")
c4.metric("Urgent (4-5)", int((tagged.urgency >= 4).sum()))

tab_table, tab_charts, tab_summary = st.tabs(["📋 Results", "📈 Charts", "📝 Summary"])

with tab_table:
    min_urgency = st.slider("Show reviews with urgency at least", 1, 5, 1)
    products = st.multiselect("Products", sorted(tagged["product"].unique()))
    view = tagged[tagged.urgency >= min_urgency]
    if products:
        view = view[view["product"].isin(products)]
    st.dataframe(view, hide_index=True)

with tab_charts:
    left, right = st.columns(2)
    left.subheader("What customers complain about")
    left.bar_chart(neg.topic.value_counts(), color="#c0392b", horizontal=True)
    right.subheader("Sentiment by product")
    by_product = pd.crosstab(tagged["product"], tagged["sentiment"]).reindex(
        columns=["negative", "neutral", "positive"], fill_value=0)
    right.bar_chart(by_product, horizontal=True,
                    color=["#c0392b", "#95a5a6", "#27ae60"])

with tab_summary:
    st.markdown(st.session_state.summary)

# Excel report built in memory (no file saved on disk), same 2 sheets as analyzer.py
buffer = io.BytesIO()
with pd.ExcelWriter(buffer) as writer:
    tagged.to_excel(writer, sheet_name="All reviews", index=False)
    pd.crosstab(tagged["product"], tagged["sentiment"]).to_excel(
        writer, sheet_name="Sentiment by product")

st.download_button("⬇️ Download Excel report", buffer.getvalue(),
                   file_name="review_report.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
