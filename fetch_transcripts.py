import os, json, requests
from pathlib import Path
from datetime import datetime, timedelta, timezone
from twilio.rest import Client
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

twilio = Client(ACCOUNT_SID, AUTH_TOKEN)
groq   = Groq(api_key=GROQ_API_KEY)

Path("recordings").mkdir(exist_ok=True)
Path("transcripts").mkdir(exist_ok=True)

cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
calls  = twilio.calls.list(to="+18054398008", start_time_after=cutoff)
print(f"Found {len(calls)} calls\n")

results = []
for i, call in enumerate(calls, 1):
    print(f"[{i}] {call.sid} — {call.status} — {call.duration}s")
    recs = twilio.recordings.list(call_sid=call.sid)
    if not recs:
        print("  No recording, skipping")
        continue
    for rec in recs:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Recordings/{rec.sid}.mp3"
        mp3 = Path(f"recordings/call_{i:02d}_{rec.sid}.mp3")
        if not mp3.exists():
            r = requests.get(url, auth=(ACCOUNT_SID, AUTH_TOKEN))
            mp3.write_bytes(r.content)
            print(f"  Downloaded {mp3.name}")
        else:
            print(f"  Already have {mp3.name}")
        print("  Transcribing with Groq Whisper...")
        try:
            with open(mp3, "rb") as f:
                result = groq.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=f,
                    response_format="text"
                )
            txt = Path(f"transcripts/transcript_{i:02d}_{call.sid}.txt")
            txt.write_text(f"Call SID: {call.sid}\nDuration: {call.duration}s\nDate: {call.start_time}\n\n{result}")
            print(f"  Saved {txt.name}")
            results.append({"call_sid": call.sid, "mp3": str(mp3), "transcript": str(txt)})
        except Exception as e:
            print(f"  Transcription failed: {e}")

json.dump(results, open("transcripts/index.json", "w"), indent=2)
print(f"\nDone! {len(results)} transcripts saved.")
print("Now run: python analyze_bugs.py")