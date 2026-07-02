# AI Patient Call System

An automated voice bot that calls a medical office's AI phone agent and simulates realistic patient conversations to test for bugs and quality issues. Built for the Pretty Good AI engineering challenge.

## How it works

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full explanation.

In short: Twilio places outbound calls to the target number, FastAPI serves TwiML instructions, and Groq's LLM (llama-3.3-70b-versatile) generates realistic patient dialogue in response to what the AI agent says, across 15 distinct scenarios (scheduling, refills, cancellations, urgent requests, and edge cases like interruptions and vague requests).

## Setup

1. Clone this repo
2. Install dependencies:
   \\\
   pip install -r requirements.txt
   \\\
3. Copy \.env.example\ to \.env\ and fill in your own API keys:
   \\\
   cp .env.example .env
   \\\
4. Run the server:
   \\\
   python main.py
   \\\
5. Expose it publicly (e.g. via ngrok) and point a Twilio phone number's outbound call webhook at \/twiml\.

## Scenarios

15 patient personas covering: appointment scheduling, rescheduling, cancellation, medication refills, office hours, insurance questions, urgent symptoms, pediatric visits, mental health referrals, lab results, and edge cases (interruptions, vague requests, closed-day requests).

## Deliverables

- \ecordings/\ — call audio (.mp3)
- \	ranscripts/\ — call transcripts
- \eports/\ — bug report
