# RupeeVoice: AI Voice Agent for Partner Lead Conversion

## Problem Understanding

Rupeezy's partner program has a strong offer: zero joining fee, 100% brokerage share, and daily payouts through the RISE Portal. The low conversion rate is mainly caused by operational limits in the RM-led process:

- Leads go cold because follow-up is delayed after hours, on weekends, or during campaign spikes.
- Language mismatch causes early drop-offs, especially outside English-speaking markets.
- RM capacity is one call at a time, so high-volume lead batches create long queues.

The solution is an AI voice agent that contacts leads immediately, speaks in the lead's preferred language, follows the Rupeezy AP sales script, handles common objections, qualifies intent, and hands off the right leads to human RMs with full context.

## Multilingual Conversation

The agent starts in the lead's preferred language if available. If not, it detects language from the first reply:

- English for English input.
- Hindi for Devanagari input.
- Hinglish for Roman Hindi markers such as "haan", "nahi", "kya", "baad mein", and mixed English-Hindi phrases.

The agent can switch mid-conversation if the lead changes language. In production, this layer can be upgraded to:

- STT language auto-detection.
- Translation-aware LLM prompting.
- Regional language packs for Tamil, Telugu, Marathi, Gujarati, and Bengali.
- Code-mixed response style, so a Hinglish-speaking lead does not receive formal Hindi.

## Objection Handling

The agent uses Appendix A as its base knowledge and responds contextually instead of reading a static block. It tracks what has already been said and adapts the rebuttal.

Core objections covered:

- Already with another broker: acknowledge experience, compare 100% brokerage share and daily payouts against typical 60-70% and monthly payout models.
- Not enough contacts: explain that a small trusted network of 20-30 serious investors is enough to begin.
- Client issues/support: clarify that Rupeezy support and RM ecosystem handle operational support.
- Trustworthiness: mention broker-license-backed onboarding, structured process, RISE Portal transparency, and official documents.
- Think later/call later: respect timing while asking whether to send WhatsApp details or schedule RM callback.

## Lead Qualification Model

The prototype scores every conversation from 0 to 100 using:

- Positive intent: "interested", "ready", "send link", "WhatsApp", "sign up".
- Engagement: asks about benefits, brokerage, payout, eligibility, or getting started.
- Network size: stated numbers such as 25, 50, 100 contacts.
- Objection pattern: objections do not automatically make a lead cold; resolved objections can still qualify as warm or hot.
- Negative intent: "not interested", "wrong number", "stop", repeated postponement.

Thresholds:

- Hot: 75-100. High interest, signup intent, or strong network. Warm transfer to RM.
- Warm: 45-74. Interested but needs details, callback, or WhatsApp follow-up.
- Cold: 0-44. Low intent or not ready. Log for nurture.

Multi-turn memory is maintained per lead/session: language, stage, transcript, objections, score, topics covered, and recommended next action.

## Handoff Design

For Hot leads, the RM dashboard shows:

- Lead name, phone, city, source.
- Hot/Warm/Cold classification and score.
- Objections raised.
- Topics covered.
- Full transcript.
- Recommended next action.

For Warm leads, the recommended action is to send the WhatsApp signup/details link and schedule an RM follow-up. In production, this connects to WhatsApp Business API with a templated message:

> Thanks for speaking with Rupeezy. Here is your AP partner signup link. An RM will help you complete onboarding.

Cold leads are logged for later nurture campaigns rather than being discarded.

## Architecture

Current prototype:

- Browser UI: Web Speech API for voice input and speech output, with text fallback.
- Backend: FastAPI conversation API.
- Conversation manager: scripted state machine using Appendix A knowledge base.
- Knowledge base: YAML file containing pitch, eligibility, closing, and objection responses.
- Analytics: in-memory session store with summaries and funnel counts.
- Dashboard: RM view for Hot/Warm/Cold funnel and handoff context.

Production architecture:

- Telephony/WebRTC layer: Exotel, Twilio, or browser/WebRTC.
- STT/TTS: Bhashini, Azure Speech, Google Speech, or browser fallback for demo.
- LLM layer: small, instruction-tuned model or GPT-class model with guardrails.
- Conversation orchestration: state machine plus retrieval from Appendix A and FAQs.
- CRM/lead pipeline: lead upload, retry rules, status updates, and RM assignment.
- Analytics: warehouse events for contacted, engaged, qualified, transferred, converted.

## Technology Choices

- FastAPI: simple async backend, fast to build in a hackathon, clean API docs.
- Browser Web Speech API: free, no telephony required, matches non-negotiable demo requirement.
- YAML knowledge base: easy to ingest Appendix A and modify during judging.
- Vanilla HTML/CSS/JS: quick, portable, no build step, reliable for live demos.
- Optional LLM upgrade: use an LLM for response rewriting and deeper NLU while keeping deterministic scoring and handoff rules.

## Risks and Trade-offs

- Browser speech recognition varies by browser and OS. Text fallback is included.
- Deterministic objection detection is transparent but less flexible than an LLM. For Round 2, add LLM classification with fallback rules.
- In-memory sessions reset when the server restarts. For production, use Postgres or Redis.
- WhatsApp sending is simulated. Production needs WhatsApp Business API approval and templates.
- No live telephony is implemented because the hackathon explicitly does not require it.

## Round 2 Implementation Plan

1. Ingest final Appendix A and sample lead CSV into the YAML knowledge base.
2. Add CSV upload and automatic session creation for lead batches.
3. Add LLM-based response rewriting while preserving mandatory pitch facts.
4. Add regional language response packs.
5. Persist leads, sessions, summaries, and RM assignments in a database.
6. Add WhatsApp Business API integration for Warm lead follow-up.
7. Add simulated warm transfer queue for Hot leads.
8. Add evaluation scripts for objection coverage, language matching, and qualification accuracy.
