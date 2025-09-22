#!/usr/bin/env python3

import asyncio
import httpx
import json
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_ollama_connection():
    """Test connection to Ollama using the exact same logic as the project"""

    # Use EXACT same logic as ollama_client.py
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL")

    if OLLAMA_BASE_URL:
        ollama_api_base = f"{OLLAMA_BASE_URL}/api"
        logger.info(f"Using Ollama Base URL from environment: {ollama_api_base}")
    else:
        # Try multiple common WSL IP addresses (same as check_ollama_status)
        common_ips = [
            "172.28.80.1",   # Detected by start.sh
            "172.28.93.1",   # Current fallback
            "172.19.16.1",   # Previous fallback
            "172.17.0.1",    # Common Docker/WSL IP
            "172.20.0.1",    # Another common WSL IP
        ]

        # Test each IP to find the working one
        working_ip = None
        for ip in common_ips:
            test_url = f"http://{ip}:11434/api/tags"
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    response = await client.get(test_url)
                    if response.status_code == 200:
                        working_ip = ip
                        logger.info(f"Found working Ollama at: {ip}")
                        break
            except:
                continue

        if working_ip:
            ollama_api_base = f"http://{working_ip}:11434/api"
        else:
            # Fallback to detected IP from start.sh logic
            import subprocess
            try:
                result = subprocess.run(['ip', 'route', 'show'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'default' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            detected_ip = parts[2]
                            ollama_api_base = f"http://{detected_ip}:11434/api"
                            logger.info(f"Using detected IP from route: {detected_ip}")
                            break
            except:
                ollama_api_base = "http://172.28.80.1:11434/api"  # Final fallback

        logger.info(f"Using Ollama Base URL: {ollama_api_base}")

    ollama_api_base = os.environ.get("OLLAMA_API_BASE", ollama_api_base)
    logger.info(f"Final Ollama Base URL: {ollama_api_base}")

    # Test connection
    print("🔌 Testing Ollama connection...")
    url = f"{ollama_api_base}/tags"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            models = response.json().get("models", [])
            print(f"✅ Connected successfully!")
            print(f"📚 Available models ({len(models)}):")

            target_model = "mistral:latest"
            model_found = False

            for model in models:
                model_name = model.get('name', '')
                print(f"   • {model_name}")
                if target_model in model_name or "phi3" in model_name.lower():
                    model_found = True
                    target_model = model_name  # Use the exact name found
                    print(f"   ✅ Will use: {target_model}")

            if not model_found:
                print(f"⚠️  Target model {target_model} not found!")
                return False

            # Test a simple classification
            print(f"\n🧠 Testing AI classification with {target_model}...")

            # Test with Spanish content
            test_prompt_spanish = """Analyze this TikTok content and determine if it is primarily in Spanish language. Be strict in your evaluation.

CONTENT:
TITLE: Hola amigos, como estan hoy?
TRANSCRIPTION: Buenos dias a todos, espero que tengan un excelente dia. Hoy vamos a hablar sobre la politica en Chile.

INSTRUCTIONS:
- Examine the title and transcription text carefully
- Ignore hashtags (#), mentions (@), and international terms
- Focus ONLY on the actual spoken/written content
- If the main content uses Spanish grammar, vocabulary, and sentence structure, it's Spanish
- If the main content uses English, Portuguese, or any other language grammar/vocabulary, it's NOT Spanish
- If you cannot clearly determine the language or if it's mixed/unclear, it's NOT Spanish

Be decisive. Answer with exactly ONE WORD:
SPANISH or NOT_SPANISH

Answer:"""

            # Test with English content
            test_prompt_english = """Analyze this TikTok content and determine if it is primarily in Spanish language. Be strict in your evaluation.

CONTENT:
TITLE: Hello everyone, how are you today?
TRANSCRIPTION: Good morning everyone, I hope you have an excellent day. Today we are going to talk about politics in Chile.

INSTRUCTIONS:
- Examine the title and transcription text carefully
- Ignore hashtags (#), mentions (@), and international terms
- Focus ONLY on the actual spoken/written content
- If the main content uses Spanish grammar, vocabulary, and sentence structure, it's Spanish
- If the main content uses English, Portuguese, or any other language grammar/vocabulary, it's NOT Spanish
- If you cannot clearly determine the language or if it's mixed/unclear, it's NOT Spanish

Be decisive. Answer with exactly ONE WORD:
SPANISH or NOT_SPANISH

Answer:"""

            # Test Spanish content
            print("📝 Testing with Spanish content...")
            generate_url = f"{ollama_api_base}/generate"
            payload = {
                "model": target_model,
                "prompt": test_prompt_spanish,
                "stream": False,
                "options": {
                    "temperature": 0.0,  # Deterministic
                    "top_p": 0.1,        # Very focused
                    "top_k": 1,          # Only best option
                    "num_predict": 5     # Very short response
                }
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(generate_url, json=payload)
                response.raise_for_status()

                result = response.json()
                spanish_response = result.get("response", "").strip()
                print(f"🤖 Spanish test response: '{spanish_response}'")

                # Test English content
                print("📝 Testing with English content...")
                payload["prompt"] = test_prompt_english
                response = await client.post(generate_url, json=payload)
                response.raise_for_status()

                result = response.json()
                english_response = result.get("response", "").strip()
                print(f"🤖 English test response: '{english_response}'")

                # Check results
                spanish_correct = "SPANISH" in spanish_response.upper()
                english_correct = "NOT_SPANISH" in english_response.upper()

                if spanish_correct and english_correct:
                    print("✅ AI correctly identified both Spanish and English content!")
                    return True
                elif spanish_correct:
                    print("✅ AI correctly identified Spanish, ⚠️  but may be too lenient with English")
                    return True
                elif english_correct:
                    print("⚠️  AI correctly identified English as NOT Spanish, but may be too strict with Spanish")
                    return True
                else:
                    print(f"⚠️  AI responses need improvement - Spanish: {spanish_response}, English: {english_response}")
                    return True  # Still connected

    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Ollama AI Connection")
    print("=" * 40)

    success = asyncio.run(test_ollama_connection())

    if success:
        print("\n🎉 Connection test successful!")
        print("✅ Ready to run the main language filter script")
    else:
        print("\n❌ Connection test failed!")
        print("🔧 Please check your Ollama setup and try again")
