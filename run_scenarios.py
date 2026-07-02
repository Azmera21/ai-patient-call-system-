import os, time, json
from datetime import datetime
from twilio.rest import Client
from dotenv import load_dotenv
load_dotenv()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
BASE_URL = os.getenv("BASE_URL")
TARGET = "+18054398008"

SCENARIOS = {
    "1": "Appointment Scheduling", "2": "Rescheduling", "3": "Cancellation",
    "4": "Medication Refill", "5": "Office Hours", "6": "Insurance Question",
    "7": "Urgent Chest Pain", "8": "Pediatric Visit", "9": "Mental Health Referral",
    "10": "Lab Results", "11": "Sunday Appointment", "12": "Interruptions",
    "13": "Vague Request", "14": "New Patient", "15": "Medication Side Effects",
}

client = Client(ACCOUNT_SID, AUTH_TOKEN)
ids = list(SCENARIOS.keys())
log = []
print(f"Placing {len(ids)} calls to {TARGET}")
print(f"Webhook: {BASE_URL}\n")

for i, sid in enumerate(ids, 1):
    name = SCENARIOS[sid]
    print(f"[{i}/{len(ids)}] {name}")
    try:
        call = client.calls.create(
            to=TARGET, from_=FROM_NUMBER,
            url=f"{BASE_URL}/twiml?scenario={sid}",
            status_callback=f"{BASE_URL}/call-status",
            status_callback_method="POST",
            record=True, recording_channels="dual",
        )
        print(f"  SID: {call.sid}  Status: {call.status}")
        log.append({"scenario_id": sid, "name": name, "sid": call.sid, "time": datetime.now().isoformat()})
    except Exception as e:
        print(f"  ERROR: {e}")
        log.append({"scenario_id": sid, "name": name, "error": str(e)})
    if i < len(ids):
        for s in range(90, 0, -10):
            print(f"  Waiting {s}s...", end="\r")
            time.sleep(10)
        print()

os.makedirs("logs", exist_ok=True)
path = f"logs/calls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
open(path, "w").write(json.dumps(log, indent=2))
print(f"\nDone! Log saved: {path}")
print("Wait 5 minutes then run: python fetch_transcripts.py")