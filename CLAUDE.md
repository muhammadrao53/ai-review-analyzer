# Project context for Claude

## About the user
- Business Analytics student, new to Python, AI engineering and Claude Code.
- Learning AI Automation and AI Engineering by building projects.
- Uses Windows; runs code in Command Prompt (cmd) opened from the project folder.
- Gets the code onto the laptop by downloading the ZIP from GitHub (not git yet).
- Explain step by step in simple language. Claude writes the code; the user runs it and learns it.
- Keep responses concise to save tokens.

## Project status
- `analyzer.py` tags customer reviews (sentiment, topic, urgency) and writes an Excel report, a chart and a summary.
- Demo mode (keyword rules) has been run successfully on the user's laptop.
- The user has completed a walkthrough of all 3 parts of the code
  (structured output and prompt, demo rules vs Claude API call, pandas pipeline).
- Claude mode (`--mode claude`) has NOT been run yet. The user still needs an Anthropic API key.

## Next steps (roadmap)
1. Switch on real AI: get an API key at console.anthropic.com, set ANTHROPIC_API_KEY in cmd, run `--mode claude`, compare with demo results.
2. Streamlit web app: DONE in code (`app.py`, run with `streamlit run app.py`). User has not run it yet.
3. Later projects: no-code automation (n8n), RAG chatbot over course PDFs, agents, deployment.
