import os, logging
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request
from fastapi.responses import Response
from groq import Groq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

app = FastAPI()

SCENARIOS = {
    "1": {"name":"Appointment Scheduling","symptoms":"lower back pain for 2 weeks","goal":"Schedule a new patient appointment","age":42,"gender":"male"},
    "2": {"name":"Rescheduling","symptoms":"migraines","goal":"Reschedule from Tuesday to Friday","age":35,"gender":"female"},
    "3": {"name":"Cancellation","symptoms":"mild cold","goal":"Cancel tomorrows appointment","age":28,"gender":"male"},
    "4": {"name":"Medication Refill","symptoms":"diabetes needs metformin","goal":"Request metformin 500mg refill","age":58,"gender":"female"},
    "5": {"name":"Office Hours","symptoms":"needs checkup","goal":"Ask if open on Saturday","age":45,"gender":"male"},
    "6": {"name":"Insurance Question","symptoms":"knee pain","goal":"Ask if BCBS is accepted","age":52,"gender":"female"},
    "7": {"name":"Urgent Chest Pain","symptoms":"chest tightness since morning","goal":"Be seen urgently today","age":65,"gender":"male"},
    "8": {"name":"Pediatric Visit","symptoms":"child has fever and ear pain","goal":"Same day appointment for child","age":34,"gender":"female"},
    "9": {"name":"Mental Health Referral","symptoms":"anxiety and panic attacks","goal":"Get a mental health referral","age":29,"gender":"female"},
    "10":{"name":"Lab Results","symptoms":"had bloodwork last week","goal":"Ask about my results","age":48,"gender":"male"},
    "11":{"name":"Sunday Appointment","symptoms":"knee pain","goal":"Ask specifically for Sunday appointment","age":40,"gender":"male"},
    "12":{"name":"Interruptions","symptoms":"allergies","goal":"Keep changing details mid-sentence","age":33,"gender":"female"},
    "13":{"name":"Vague Request","symptoms":"not feeling well","goal":"Be vague and unclear","age":55,"gender":"male"},
    "14":{"name":"New Patient","symptoms":"annual physical","goal":"Register as new patient and schedule physical","age":31,"gender":"female"},
    "15":{"name":"Medication Side Effects","symptoms":"nausea from lisinopril","goal":"Ask if I should stop taking it","age":62,"gender":"male"},
}

calls = {}

def get_ai_opening(scenario):
    r = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":f"You are a patient calling a medical office. Age {scenario['age']}, {scenario['gender']}. Situation: {scenario['symptoms']}. Goal: {scenario['goal']}. Start the call naturally under 30 words. Sound like a real person, slightly anxious."}],
        max_tokens=100,
    )
    return r.choices[0].message.content.strip()

def get_ai_response(agent_said, scenario, history):
    messages = [{"role":"system","content":f"You are a patient calling a medical office. Age {scenario['age']}, {scenario['gender']}. Symptoms: {scenario['symptoms']}. Goal: {scenario['goal']}. Respond naturally under 35 words. Stay in character."}]
    messages.extend(history[-8:])
    messages.append({"role":"user","content":agent_said})
    r = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=120,
    )
    return r.choices[0].message.content.strip()

@app.get("/")
async def root(): return {"status":"running","scenarios":len(SCENARIOS)}

@app.get("/health")
async def health(): return {"status":"healthy","groq":"ok" if GROQ_API_KEY else "MISSING"}

@app.post("/twiml")
async def twiml_entry(request: Request):
    scenario_id = request.query_params.get("scenario","1")
    if scenario_id not in SCENARIOS: scenario_id = "1"
    form_data = await request.form()
    call_sid = form_data.get("CallSid","unknown")
    scenario = SCENARIOS[scenario_id]
    calls[call_sid] = {"scenario":scenario,"history":[],"scenario_id":scenario_id}
    logger.info(f"Call {call_sid} scenario {scenario_id}: {scenario['name']}")
    opening = get_ai_opening(scenario)
    logger.info(f"Patient: {opening}")
    return Response(content=f'<?xml version="1.0" encoding="UTF-8"?><Response><Pause length="1"/><Say voice="Polly.Joanna">{opening}</Say><Gather input="speech" timeout="8" speechTimeout="2" action="/webhook/gather" method="POST"></Gather><Hangup/></Response>',media_type="application/xml")

@app.post("/webhook/gather")
async def gather(request: Request):
    form_data = await request.form()
    call_sid = form_data.get("CallSid","unknown")
    agent_said = form_data.get("SpeechResult","").strip()
    logger.info(f"Agent: {agent_said}")
    state = calls.get(call_sid)
    if not state:
        return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>',media_type="application/xml")
    history = state["history"]
    if agent_said:
        history.append({"role":"user","content":agent_said})
        reply = get_ai_response(agent_said,state["scenario"],history)
        history.append({"role":"assistant","content":reply})
        logger.info(f"Patient: {reply}")
        if len(history) >= 14:
            reply += " Thank you so much, goodbye."
            return Response(content=f'<?xml version="1.0" encoding="UTF-8"?><Response><Say voice="Polly.Joanna">{reply}</Say><Hangup/></Response>',media_type="application/xml")
    else:
        reply = "Sorry, could you repeat that?"
    return Response(content=f'<?xml version="1.0" encoding="UTF-8"?><Response><Say voice="Polly.Joanna">{reply}</Say><Gather input="speech" timeout="8" speechTimeout="2" action="/webhook/gather" method="POST"></Gather><Hangup/></Response>',media_type="application/xml")

@app.post("/call-status")
async def call_status(request: Request):
    form_data = await request.form()
    sid = form_data.get("CallSid")
    status = form_data.get("CallStatus")
    logger.info(f"Call {sid}: {status}")
    if status in ("completed","failed","busy","no-answer","canceled"):
        calls.pop(sid,None)
    return Response(content="",media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting AI Patient Call System (Groq)...")
    logger.info(f"Groq Key: {'FOUND' if GROQ_API_KEY else 'MISSING'}")
    uvicorn.run(app,host="0.0.0.0",port=8000,log_level="info")