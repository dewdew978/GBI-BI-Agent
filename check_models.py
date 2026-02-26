# check_models.py
import os
from dotenv import load_dotenv
from google.genai import Client

load_dotenv(dotenv_path='bi_agent/.env')
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ The API Key was not found in bi_agent/.env.")
else:
    print(f"✅ API Key found: {api_key[:5]}...")
    try:
        client = Client(api_key=api_key)
        print("\n Retrieving a list of available models...")
        # ดึงรายชื่อโมเดลทั้งหมด
        models = client.models.list()
        
        print("\n=== List of Recommended Models (Guaranteed to work) ===")
        found_flash = False
        for m in models:
            # Filter to show only the interesting ones.
            if "flash" in m.name.lower() or "gemini-1.5" in m.name.lower():
                print(f"- {m.name.replace('models/', '')}")
                found_flash = True
        
        if not found_flash:
            print("(No Flash models found. Please see the full list below.)")
            for m in models:
                print(f"- {m.name}")

    except Exception as e:
        print(f"\n❌ Error: {e}")