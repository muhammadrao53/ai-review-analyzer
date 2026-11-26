# AI Customer Review Analyzer

Reads customer reviews, uses AI to tag each one with **sentiment**, **topic** and
**urgency**, then automatically produces:

- `output/review_report.xlsx`: every review tagged and sorted by urgency, plus a sentiment-by-product sheet
- `output/complaints_chart.png`: what customers complain about most
- `output/summary.md`: a short management summary with recommended actions

## Skills this project teaches

| Skill | Where in `analyzer.py` |
|---|---|
| Calling an LLM API | `make_claude_analyzer()` |
| Prompt design | `PROMPT` |
| Structured output (AI returns clean data, not free text) | `ReviewAnalysis` + `messages.parse(...)` |
| Batch automation (process a whole file with no manual work) | the loop in `main()` |
| Turning AI output into business reporting | Excel / chart / summary section |

## How to run it on your own laptop

**1. Install Python 3.10+** from python.org. On Windows, tick "Add Python to PATH" during install.

**2. Get the project.** Download this folder (or `git clone` your GitHub repo), then open a terminal inside it.

**3. Install the libraries:**
```bash
pip install -r requirements.txt
```

**4. Run in demo mode** (free, no API key needed):
```bash
python analyzer.py
```

**5. Get a Claude API key** to use real AI:
- Go to console.anthropic.com, sign up, add a small amount of credit (USD 5 is plenty), and create an API key.
- Never share the key or upload it to GitHub.

**6. Set the key in your terminal:**

Windows (PowerShell):
```bash
$env:ANTHROPIC_API_KEY="sk-ant-..."
```
Mac / Linux:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**7. Run with real AI:**
```bash
python analyzer.py --mode claude
```
Expected cost for the 30 sample reviews: a few US cents with Opus, a fraction of a cent if you
change `MODEL` to `claude-haiku-5-5` at the top of `analyzer.py`.

## Web app version (Streamlit)

The same analyzer as a web page: upload a CSV, see results and charts, download the Excel report.
```bash
streamlit run app.py
```
Your browser opens at http://localhost:8501. Press Ctrl+C in the terminal to stop it.
For Claude mode, pick "Claude (real AI)" in the sidebar and paste your API key there.

## Exercises (do these yourself to learn)

1. Compare demo vs Claude results. Where did keyword rules fail? (Hint: review #26.)
2. Add your own reviews to `data/reviews.csv`, including Roman Urdu ones. Does the AI handle them?
3. Add a new field to `ReviewAnalysis`, e.g. `customer_wants_refund: bool`, and update the prompt.
4. Switch `MODEL` to `claude-haiku-5-5`. Is the quality still good enough? That's a real cost/quality decision engineers make.
5. Point it at a real dataset, e.g. a product-reviews dataset from Kaggle.
