import openai, os
from dotenv import load_dotenv
load_dotenv()
c = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
r = c.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":"say hi"}], max_tokens=5)
print("SUCCESS:", r.choices[0].message.content)