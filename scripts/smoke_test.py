"""Smoke test: can we reach the model through the vendor SDK and through LiteLLM?
   Needs a real .env; not run in CI."""

import os
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
client = OpenAI(base_url=os.environ["ATLAS_API_BASE"], api_key=os.environ["ATLAS_API_KEY"])
r = client.chat.completions.create(model="gpt-5-mini", messages=[{"role": "user", "content": "Reply with one word: ready"}])
print(r.choices[0].message.content, r.usage)

import litellm
r = litellm.completion(
    model=os.environ["ATLAS_MODELS"],
    api_base=os.environ["ATLAS_API_BASE"],
    api_key=os.environ["ATLAS_API_KEY"],
    messages=[{"role": "user", "content": "Reply with one word: ready"}],
)
print(r.choices[0].message.content)
print(r.usage)
print(litellm.completion_cost(completion_response=r))