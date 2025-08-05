# backend/ollama_client.py
import httpx
import logging
import json
import os # Import os for environment variable option
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# --- Configuration ---

# Get Windows host IP dynamically or use environment variable
# The start.sh script will set OLLAMA_BASE_URL environment variable
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL")

if OLLAMA_BASE_URL:
    # Use the URL provided by environment variable (from start.sh)
    OLLAMA_API_BASE = f"{OLLAMA_BASE_URL}/api"
    logger.info(f"Using Ollama Base URL from environment: {OLLAMA_API_BASE}")
else:
    # Fallback to hardcoded WSL interface IP
    # Updated based on common WSL2 network configuration
    WINDOWS_HOST_IP = "172.28.93.1"  # Updated from 172.19.16.1
    OLLAMA_API_BASE = f"http://{WINDOWS_HOST_IP}:11434/api"
    logger.info(f"Using fallback Ollama Base URL: {OLLAMA_API_BASE}")

# Allow further overriding via OLLAMA_API_BASE environment variable
OLLAMA_API_BASE = os.environ.get("OLLAMA_API_BASE", OLLAMA_API_BASE)
logger.info(f"Final Ollama Base URL: {OLLAMA_API_BASE}")

# Default model updated to Qwen2.5-Coder:32B
DEFAULT_MODEL = "Qwen2.5-Coder:32B"

# --- Functions ---

async def generate_response(prompt: str, model: Optional[str] = None) -> str: # Allow model to be None initially
    """Generate a response from Ollama API"""
    model_to_use = model or DEFAULT_MODEL # Use provided model or fallback to default
    url = f"{OLLAMA_API_BASE}/generate"
    logger.info(f"Sending request to Ollama Generate: {url} | Model: {model_to_use}")
    try:
        payload = {
            "model": model_to_use, # Ensure this is never None/empty
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 1024 # Max tokens
            }
        }
        # Log payload without potentially large prompt for cleaner logs
        # logger.debug(f"Request payload (excluding prompt): {json.dumps({k: v for k, v in payload.items() if k != 'prompt'})}")

        # Increase timeout slightly, Ollama can be slow
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            logger.info(f"Ollama Generate response status: {response.status_code}")
            response.raise_for_status() # Raises exception for 4xx/5xx errors

            result = response.json()
            # Log response structure if debugging is needed
            # logger.debug(f"Ollama Generate response JSON: {result}")
            return result.get("response", "").strip() # Return the generated text, stripped of whitespace

    except httpx.HTTPStatusError as e:
        error_text = e.response.text
        logger.error(f"Ollama HTTP error: {e.response.status_code} - Body: {error_text} - URL: {e.request.url}")
        # Provide a more specific Spanish error message if possible
        if e.response.status_code == 404:
             raise Exception(f"Modelo Ollama '{model_to_use}' no encontrado o URL base '{OLLAMA_API_BASE}' incorrecta.")
        elif "contain prompt" in error_text.lower():
             raise Exception("Error de Ollama: La solicitud no contenía un prompt válido.")
        else:
             raise Exception(f"Error HTTP de Ollama: {e.response.status_code}. Revisa los logs del backend para más detalles.") # Spanish

    except httpx.RequestError as e:
        logger.error(f"Ollama Request error: {str(e)} - URL: {e.request.url}")
        # Spanish error message
        raise Exception(f"No se pudo conectar a Ollama en {OLLAMA_API_BASE}. ¿Está Ollama ejecutándose y accesible en esa IP y puerto?")

    except Exception as e:
        logger.error(f"Error inesperado generando respuesta de Ollama: {str(e)}", exc_info=True)
        # Spanish error message
        raise Exception(f"Error inesperado al generar respuesta: {str(e)}")


async def get_models() -> Dict[str, Any]:
    """Get available models from Ollama API"""
    # First, ensure we can connect to Ollama and have the right URL
    status = await check_ollama_status()
    if status.get("status") != "available":
        raise Exception(f"Ollama no está disponible: {status.get('message', 'Error desconocido')}")

    url = f"{OLLAMA_API_BASE}/tags"
    logger.info(f"Obteniendo modelos desde: {url}")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client: # Slightly longer timeout
            response = await client.get(url)
            logger.info(f"Ollama Tags response status: {response.status_code}")
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"Ollama HTTP error obteniendo modelos: {e.response.status_code} - {e.response.text} - URL: {e.request.url}")
        # Spanish error message
        raise Exception(f"Error HTTP de Ollama al obtener modelos: {e.response.status_code}.")

    except httpx.RequestError as e:
        logger.error(f"Ollama Request error obteniendo modelos: {str(e)} - URL: {e.request.url}")
        # Spanish error message
        raise Exception(f"No se pudo conectar a Ollama ({OLLAMA_API_BASE}) para obtener modelos.")

    except Exception as e:
        logger.error(f"Error inesperado obteniendo modelos de Ollama: {str(e)}", exc_info=True)
        # Spanish error message
        raise Exception(f"Error inesperado al obtener modelos: {str(e)}")

# --- generate_streaming_response ---
async def generate_streaming_response(prompt: str, model: Optional[str] = None):
    """Generate a streaming response from Ollama API"""
    model_to_use = model or DEFAULT_MODEL
    url = f"{OLLAMA_API_BASE}/generate" # Ensure this uses the correct base URL
    logger.info(f"Iniciando stream de Ollama: {url} | Modelo: {model_to_use}")
    try:
        payload = {
            "model": model_to_use,
            "prompt": prompt,
            "stream": True, # Key difference
            "options": {
                "temperature": 0.7, "top_p": 0.9, "top_k": 40, "num_predict": 1024
            }
        }
        # Increase timeout for potentially long streams
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk_data = json.loads(line)
                            if "response" in chunk_data:
                                yield chunk_data["response"] # Yield the text part
                            if chunk_data.get("done", False):
                                break # Exit loop when Ollama signals completion
                        except json.JSONDecodeError:
                            logger.warning(f"Error decodificando JSON del stream chunk: {line}")
                            continue # Skip malformed lines

    except httpx.HTTPStatusError as e:
        error_text = e.response.text
        logger.error(f"Ollama HTTP error en stream: {e.response.status_code} - Body: {error_text} - URL: {e.request.url}")
        raise Exception(f"Error HTTP de Ollama en stream: {e.response.status_code}") # Spanish

    except httpx.RequestError as e:
        logger.error(f"Ollama Request error en stream: {str(e)} - URL: {e.request.url}")
        raise Exception(f"No se pudo conectar a Ollama para streaming en {OLLAMA_API_BASE}.") # Spanish

    except Exception as e:
        logger.error(f"Error inesperado generando respuesta streaming: {e}", exc_info=True)
        raise Exception(f"Error inesperado generando respuesta streaming: {str(e)}") # Spanish

# --- check_ollama_status ---
async def check_ollama_status() -> Dict[str, Any]:
    """Check if Ollama is running and available using the / (root) endpoint or /tags"""
    global OLLAMA_API_BASE, OLLAMA_BASE_URL

    # If we have an environment variable, use it
    if OLLAMA_BASE_URL:
        base_url = OLLAMA_BASE_URL
        urls_to_check = [f"{base_url}/", f"{base_url}/api/tags"]
    else:
        # Try multiple common WSL IP addresses
        common_ips = [
            "172.28.80.1",   # Detected by start.sh
            "172.28.93.1",   # Current fallback
            "172.19.16.1",   # Previous fallback
            "172.17.0.1",    # Common Docker/WSL IP
            "172.20.0.1",    # Another common WSL IP
            "localhost",     # Sometimes works
            "127.0.0.1"      # Local fallback
        ]

        urls_to_check = []
        for ip in common_ips:
            if ip in ["localhost", "127.0.0.1"]:
                base_url = f"http://{ip}:11434"
            else:
                base_url = f"http://{ip}:11434"
            urls_to_check.extend([f"{base_url}/", f"{base_url}/api/tags"])

    timeout = 5.0
    last_error = None

    for url in urls_to_check:
        logger.info(f"Verificando estado de Ollama en: {url}")
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                # For root endpoint, just check if it responds (might be "Ollama is running")
                # For /tags endpoint, check status 200
                if response.status_code == 200:
                    logger.info(f"Ollama está disponible (Respuesta de {url})")

                    # Update the global OLLAMA_API_BASE if we found a working URL
                    if not OLLAMA_BASE_URL:  # Only update if not set by environment
                        if "/api/tags" in url:
                            OLLAMA_API_BASE = url.replace("/tags", "")
                        else:
                            OLLAMA_API_BASE = f"{url.rstrip('/')}/api"
                        logger.info(f"Updated OLLAMA_API_BASE to: {OLLAMA_API_BASE}")

                    models = []
                    # If we checked /tags, try to get models
                    if "/tags" in url:
                         try:
                             models = response.json().get("models", [])
                         except json.JSONDecodeError:
                             logger.warning("Ollama /tags respondió 200 pero no es JSON válido.")
                    return { "status": "available", "models": models }
                else:
                    logger.warning(f"Ollama respondió con estado no-OK ({response.status_code}) en {url}")
                    last_error = f"Código de estado HTTP: {response.status_code}"
                    # Don't break, try next URL if available

        except httpx.RequestError as e:
             logger.warning(f"Fallo de conexión verificando Ollama en {url}: {e}")
             last_error = f"No se pudo conectar a {url}. Detalles: {str(e)}"
             # Don't break, try next URL

        except Exception as e:
            logger.error(f"Error inesperado verificando Ollama en {url}: {e}", exc_info=True)
            last_error = f"Error inesperado al verificar {url}: {str(e)}"
            # Don't break, try next URL

    # If loop finishes without returning success
    logger.error(f"Ollama no parece estar disponible después de verificar. Último error: {last_error}")
    return { "status": "unavailable", "message": last_error or "No se pudo determinar el estado." } # Spanish message in error