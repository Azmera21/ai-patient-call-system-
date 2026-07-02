import os, json
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
Path("reports").mkdir(exist_ok=True)

files = sorted(Path("transcripts").glob("transcript_*.txt"))
print(f"Analyzing {len(files)} transcripts...\n")

PROMPT = """You are a QA engineer testing a medical office AI voice agent.
Analyze the agent responses in this transcript for bugs:
1. Wrong info about hours or availability
2. Scheduling on closed days like weekends
3. Misunderstanding patient requests
4. Not escalating urgent cases like chest pain
5. Incomplete or confusing answers
6. Unnatural conversation flow
7. Exposing internal/demo language to patients

Return only JSON:
{"bugs":[{"severity":"HIGH/MEDIUM/LOW","type":"bug type","agent_said":"what agent said","problem":"what went wrong","expected":"what should have happened","timestamp":"MM:SS or null"}],"quality":"GOOD/ACCEPTABLE/POOR","summary":"one sentence"}"""

all_bugs  = []
summaries = []

for i, f in enumerate(files, 1):
    text = f.read_text(encoding="utf-8", errors="ignore")
    print(f"[{i}/{len(files)}] {f.name}")
    try:
        r = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":PROMPT},
                      {"role":"user","content":text[:6000]}],
            max_tokens=1000,
            temperature=0.2,
        )
        raw = r.choices[0].message.content.strip()
        raw = raw.replace("```json","").replace("```","").strip()
        data = json.loads(raw)
    except Exception as e:
        print(f"  Error: {e}")
        data = {"bugs":[],"quality":"UNKNOWN","summary":"Analysis failed"}

    bugs = data.get("bugs",[])
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

high = [b for b in all_bugs if b.get("severity")=="HIGH"]
med  = [b for b in all_bugs if b.get("severity")=="MEDIUM"]
low  = [b for b in all_bugs if b.get("severity")=="LOW"]

report  = f"# Bug Report\n\n"
report += f"Calls analyzed: {len(files)}\n"
report += f"Total bugs: {len(all_bugs)} — HIGH: {len(high)} | MEDIUM: {len(med)} | LOW: {len(low)}\n\n---\n\n"
report += "## Call Summaries\n\n| # | File | Quality | Bugs | Summary |\n|---|---|---|---|---|\n"
for i,s in enumerate(summaries,1):
    report += f"| {i} | {s['file']} | {s['quality']} | {s['bugs']} | {s['summary']} |\n"

report += "\n---\n\n## Bugs\n\n"
for sev, bugs, icon in [("HIGH",high,"🔴"),("MEDIUM",med,"🟡"),("LOW",low,"🟢")]:
    if not bugs: continue
    report += f"### {icon} {sev} ({len(bugs)})\n\n"
    for b in bugs:
        report += f"**Type:** {b.get('type')}  \n"
        report += f"**File:** {b.get('file')} at {b.get('timestamp','?')}  \n"
        report += f"**Agent said:** {b.get('agent_said')}  \n"
        report += f"**Problem:** {b.get('problem')}  \n"
        report += f"**Expected:** {b.get('expected')}  \n\n---\n\n"

Path("reports/bug_report.md").write_text(report, encoding="utf-8")
json.dump(all_bugs, open("reports/bugs.json","w"), indent=2)
print(f"\nDone! Report saved: reports/bug_report.md")
print(f"HIGH: {len(high)}  MEDIUM: {len(med)}  LOW: {len(low)}")