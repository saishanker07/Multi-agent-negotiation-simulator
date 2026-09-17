import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: GEMINI_API_KEY is not set.")
    exit()

client = genai.Client(api_key=api_key)

print("\n===================================")
print("AVAILABLE GEMINI MODELS")
print("===================================\n")

try:
    for model in client.models.list():
        print(model.name)

except Exception as e:
    print("ERROR:")
    print(e)