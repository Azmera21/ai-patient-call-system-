"""
setup_project.py
Run this once: python setup_project.py
It creates all the other files you need.
"""
import os

files = {}

files["run_scenarios.py"] = """import os, time, json
from datetime import datetime
from twilio.rest import Client
from dotenv import load_dotenv
load_dotenv()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN")
FROM_NUMBER  = os.getenv("TWILIO_PHONE_NUMBER")
BASE_URL     = os.getenv("BASE_URL")
TARGET       = "+12135706161"

SCENARIOS = {
    "1": "Appointment Scheduling",
    "2": "Rescheduling",
    "3": "Cancellation",
    "4": "Medication Refill",
    "5": "Office Hours",
    "6": "Insurance Question",
    "7": "Urgent Chest Pain",
    "8": "Pediatric Visit",
    "9": "Mental Health Referral",
    "10": "Lab Results",
    "11": "Sunday Appointment",
    "12": "Interruptions",
    "13": "Vague Request",
    "14": "New Patient",
    "15": "Medication Side Effects",
}

client = Client(ACCOUNT_SID, AUTH_TOKEN)
ids    = list(SCENARIOS.keys())
log    = []

print(f"Placing {len(ids)} calls to {TARGET}")
print(f"Webhook: {BASE_URL}\\n")

for i, sid in enumerate(ids, 1):
    name = SCENARIOS[sid]
    print(f"[{i}/{len(ids)}] {name}")
    try:
        call = client.calls.create(
            to=TARGET,
            from_=FROM_NUMBER,
            url=f"{BASE_URL}/twiml?scenario={sid}",
            status_callback=f"{BASE_URL}/call-status",
            status_callback_method="POST",
            record=True,
            recording_channels="dual",
        )
        print(f"  SID: {call.sid}  Status: {call.status}")
        log.append({"scenario_id": sid, "name": name, "sid": call.sid,
                    "time": datetime.now().isoformat()})
    except Exception as e:
        print(f"  ERROR: {e}")
        log.append({"scenario_id": sid, "name": name, "error": str(e)})

    if i < len(ids):
        for s in range(90, 0, -10):
            print(f"  Waiting {s}s...", end="\\r")
            time.sleep(10)
        print()

os.makedirs("logs", exist_ok=True)
path = f"logs/calls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
open(path, "w").write(json.dumps(log, indent=2))
print(f"\\nDone! Log saved: {path}")
print("Wait 5 minutes then run: python fetch_transcripts.py")
"""

files["fetch_transcripts.py"] = """import os, json, requests
from pathlib import Path
from datetime import datetime, timedelta, timezone
from twilio.rest import Client
import openai
from dotenv import load_dotenv
load_dotenv()

ACCOUNT_SID    = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN     = os.getenv("TWILIO_AUTH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

twilio = Client(ACCOUNT_SID, AUTH_TOKEN)
oai    = openai.OpenAI(api_key=OPENAI_API_KEY)

Path("recordings").mkdir(exist_ok=True)
Path("transcripts").mkdir(exist_ok=True)

cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
calls  = twilio.calls.list(to="+18054398008", start_time_after=cutoff)
print(f"Found {len(calls)} calls in last 24h\\n")

results = []
for i, call in enumerate(calls, 1):
    print(f"[{i}] {call.sid} — {call.status} — {call.duration}s")
    recs = twilio.recordings.list(call_sid=call.sid)
    if not recs:
        print("  No recording yet, skipping")
        continue
    for rec in recs:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Recordings/{rec.sid}.mp3"
        mp3 = Path(f"recordings/call_{i:02d}_{rec.sid}.mp3")
        if not mp3.exists():
            r = requests.get(url, auth=(ACCOUNT_SID, AUTH_TOKEN))
            mp3.write_bytes(r.content)
            print(f"  Downloaded {mp3.name}")
        print("  Transcribing...")
        with open(mp3, "rb") as f:
            result = oai.audio.transcriptions.create(
                model="whisper-1", file=f, response_format="text"
            )
        txt = Path(f"transcripts/transcript_{i:02d}_{call.sid}.txt")
        txt.write_text(f"Call SID: {call.sid}\\nDuration: {call.duration}s\\nDate: {call.start_time}\\n\\n{result}")
        print(f"  Saved {txt.name}")
        results.append({"call_sid": call.sid, "mp3": str(mp3), "transcript": str(txt)})

json.dump(results, open("transcripts/index.json", "w"), indent=2)
print(f"\\nDone! {len(results)} transcripts saved.")
print("Now run: python analyze_bugs.py")
"""

files["analyze_bugs.py"] = """import os, json
from pathlib import Path
import openai
from dotenv import load_dotenv
load_dotenv()

oai = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
Path("reports").mkdir(exist_ok=True)

files = sorted(Path("transcripts").glob("transcript_*.txt"))
print(f"Analyzing {len(files)} transcripts...\\n")

PROMPT = \"\"\"You are a QA engineer testing a medical office AI voice agent.
Analyze the agent responses for bugs:
1. Wrong info about hours or availability
2. Scheduling on closed days like weekends
3. Misunderstanding patient requests
4. Not escalating urgent cases like chest pain
5. Incomplete or confusing answers
6. Unnatural conversation flow

Return only JSON in this format:
{"bugs":[{"severity":"HIGH/MEDIUM/LOW","type":"bug type","agent_said":"what agent said","problem":"what went wrong","expected":"what should have happened","timestamp":"MM:SS or null"}],"quality":"GOOD/ACCEPTABLE/POOR","summary":"one sentence"}\"\"\"

all_bugs  = []
summaries = []

for i, f in enumerate(files, 1):
    text = f.read_text()
    print(f"[{i}/{len(files)}] {f.name}")
    r = oai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": PROMPT},
                  {"role": "user", "content": text}],
        max_tokens=1500,
        temperature=0.2,
    )
    raw = r.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
    except Exception:
        data = {"bugs": [], "quality": "UNKNOWN", "summary": raw}

    bugs = data.get("bugs", [])
    for b in bugs:
        b["file"] = f.name
    all_bugs.extend(bugs)
    summaries.append({
        "file": f.name,
        "quality": data.get("quality"),
        "bugs": len(bugs),
        "summary": data.get("summary"),
    })
    print(f"  Quality: {data.get('quality')}  Bugs: {len(bugs)}")

high = [b for b in all_bugs if b.get("severity") == "HIGH"]
med  = [b for b in all_bugs if b.get("severity") == "MEDIUM"]
low  = [b for b in all_bugs if b.get("severity") == "LOW"]

report  = f"# Bug Report\\n\\n"
report += f"Calls analyzed: {len(files)}  \\n"
report += f"Total bugs: {len(all_bugs)} — HIGH: {len(high)} | MEDIUM: {len(med)} | LOW: {len(low)}\\n\\n---\\n\\n"
report += "## Call Summaries\\n\\n| # | File | Quality | Bugs |\\n|---|---|---|---|\\n"
for i, s in enumerate(summaries, 1):
    report += f"| {i} | {s['file']} | {s['quality']} | {s['bugs']} |\\n"

report += "\\n---\\n\\n## Bugs\\n\\n"
for sev, bugs, icon in [("HIGH", high, "RED"), ("MEDIUM", med, "YELLOW"), ("LOW", low, "GREEN")]:
    if not bugs:
        continue
    report += f"### {icon} {sev} ({len(bugs)})\\n\\n"
    for b in bugs:
        report += f"**Type:** {b.get('type')}  \\n"
        report += f"**File:** {b.get('file')} at {b.get('timestamp', '?')}  \\n"
        report += f"**Agent said:** {b.get('agent_said')}  \\n"
        report += f"**Problem:** {b.get('problem')}  \\n"
        report += f"**Expected:** {b.get('expected')}  \\n\\n---\\n\\n"

Path("reports/bug_report.md").write_text(report)
json.dump(all_bugs, open("reports/bugs.json", "w"), indent=2)
print(f"\\nReport saved: reports/bug_report.md")
print(f"HIGH: {len(high)}  MEDIUM: {len(med)}  LOW: {len(low)}")
"""

for filename, content in files.items():
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Created {filename}")

print("\nAll files created! Now run:")
print("  python run_scenarios.py")