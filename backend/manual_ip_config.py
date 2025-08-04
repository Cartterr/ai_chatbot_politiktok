import httpx
import logging
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# SUPER DIRECT HARDCODED APPROACH
# Find your Windows IP by running 'ipconfig' in CMD and look for 'IPv4 Address'
# Usually looks like 192.168.x.x or 10.0.x.x
YOUR_WINDOWS_IP = "YOUR_IP_HERE"  # <-- REPLACE THIS

# Ollama API settings - point directly to your Windows IP
OLLAMA_API_BASE = f"http://{YOUR_WINDOWS_IP}:11434/api"
logger.info(f"Using hardcoded Ollama API URL: {OLLAMA_API_BASE}")

DEFAULT_MODEL = "bsahane/Mistral-Small-3.1:24b"

async def generate_response(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Generate a response from Ollama API"""
    try:
        url = f"{OLLAMA_API_BASE}/generate"
        logger.info(f"Sending request to Ollama at: {url}")
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 1024
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise Exception(f"HTTP error: {e.response.status_code}")
    
    except httpx.RequestError as e:
        logger.error(f"Request error: {str(e)}")
        raise Exception(f"Request error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        raise Exception(f"Error generating response: {str(e)}")

async def get_models() -> Dict[str, Any]:
    """Get available models from Ollama API"""
    try:
        url = f"{OLLAMA_API_BASE}/tags"
        logger.info(f"Getting models from: {url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            return response.json()
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise Exception(f"HTTP error: {e.response.status_code}")
    
    except httpx.RequestError as e:
        logger.error(f"Request error: {str(e)}")
        raise Exception(f"Request error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error getting models: {str(e)}")
        raise Exception(f"Error getting models: {str(e)}")

async def generate_streaming_response(prompt: str, model: str = DEFAULT_MODEL):
    """Generate a streaming response from Ollama API"""
    try:
        url = f"{OLLAMA_API_BASE}/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 1024
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                
                async for chunk in response.aiter_text():
                    try:
                        # Each chunk is a JSON object
                        chunk_data = json.loads(chunk)
                        
                        # Extract and yield the response text
                        if "response" in chunk_data:
                            yield chunk_data["response"]
                        
                        # Stop if we've reached the end
                        if chunk_data.get("done", False):
                            break
                    
                    except json.JSONDecodeError:
                        # Skip invalid JSON chunks
                        continue
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise Exception(f"HTTP error: {e.response.status_code}")
    
    except httpx.RequestError as e:
        logger.error(f"Request error: {str(e)}")
        raise Exception(f"Request error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error generating streaming response: {str(e)}")
        raise Exception(f"Error generating streaming response: {str(e)}")

async def check_ollama_status() -> Dict[str, Any]:
    """Check if Ollama is running and available"""
    try:
        url = f"{OLLAMA_API_BASE}/tags"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                return {
                    "status": "available",
                    "models": response.json().get("models", [])
                }
            else:
                return {
                    "status": "error",
                    "message": f"HTTP status code: {response.status_code}"
                }
    
    except Exception as e:
        return {
            "status": "unavailable",
            "message": str(e)
        }