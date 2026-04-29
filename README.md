# RupeeVoice

AI voice agent prototype for Rupeezy partner lead conversion. It demonstrates a browser voice/text call flow, Hindi/Hinglish/English handling, top-objection responses, lead scoring, RM handoff context, WhatsApp fallback recommendations, and a conversion dashboard.

## Run

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

- Live agent: `http://127.0.0.1:8000/`
- RM dashboard: `http://127.0.0.1:8000/dashboard`

## What is included

- `backend/main.py`: FastAPI API, language detection, scripted sales flow, objection handling, scoring, summaries.
- `data/knowledge_base.yaml`: Appendix A-style pitch, FAQ, and objection rebuttals.
- `frontend/index.html`: Browser voice and text conversation demo using Web Speech API.
- `frontend/dashboard.html`: RM funnel and handoff dashboard.

The current prototype avoids paid telephony and paid model dependencies. It uses the freely available browser Web Speech API for STT/TTS and a deterministic conversation manager that can later be replaced or enhanced with an LLM.
