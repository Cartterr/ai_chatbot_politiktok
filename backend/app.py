# backend/app.py

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
import httpx
import os
from pydantic import BaseModel, Field # Added Field for better validation/docs
from typing import List, Dict, Any, Optional
import logging
import re
import asyncio

# Import local modules
from data_loader import load_all_data, get_data_summary
# Assuming embeddings are not the primary search method for now based on previous prompt structure
# from embeddings import create_embeddings, semantic_search
from visualization import generate_visualization
from ollama_client import generate_response, get_models, check_ollama_status

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API Chatbot Investigación TikTok", # Spanish Title
    description="API para interactuar con el chatbot de investigación sobre TikTok, jóvenes y política en Chile.", # Spanish Desc
    version="1.0.0"
)

# --- CORS Configuration ---
# Allow all origins for development ease, restrict in production!
origins = ["*"]
# Example for production:
# origins = [
#    "http://localhost",
#    "http://localhost:8080", # If serving frontend build locally
#    "https://your-frontend-domain.com",
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)

# --- Global Data Store ---
# Using a simple dictionary to hold loaded data
# In a real application, consider a more robust state management or database
app_state: Dict[str, Any] = {"data": None, "embeddings_ready": False}

# --- Pydantic Models for Request/Response ---
class QueryModel(BaseModel):
    query: str = Field(..., description="La pregunta o consulta del usuario.", min_length=1)
    generate_visualization: bool = Field(False, description="Indica si se debe generar una visualización.")
    visualization_type: Optional[str] = Field(None, description="Tipo específico de visualización solicitada (opcional).")
    model: Optional[str] = Field(None, description="Nombre del modelo LLM a utilizar (opcional, usa predeterminado si es None).")

class VisualizeRequest(BaseModel):
    query: str = Field(..., description="La consulta relacionada con la visualización.", min_length=1)
    visualization_type: Optional[str] = Field(None, description="Tipo específico de visualización (opcional, intentará autodetectar).")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="La respuesta generada por el LLM.")
    relevant_data: Optional[Dict[str, Any]] = Field(None, description="Datos relevantes utilizados para generar la respuesta (puede ser resumen).")
    visualization: Optional[Dict[str, Any]] = Field(None, description="Datos de visualización generados (si se solicitaron).")
    visualization_error: Optional[str] = Field(None, description="Mensaje de error si la visualización falló.")

class VisualizationResponse(BaseModel):
    visualization: Dict[str, Any] = Field(..., description="Los datos de la visualización generada.")

class DataInsightsRequest(BaseModel):
    insight_type: str = Field(..., description="Tipo de insight a generar: 'overview', 'trends', 'sentiment', 'demographics', 'engagement'")
    focus_area: Optional[str] = Field(None, description="Área específica de enfoque (opcional)")

class DataInsightsResponse(BaseModel):
    insights: List[Dict[str, Any]] = Field(..., description="Lista de insights generados por IA")
    summary: str = Field(..., description="Resumen general de los insights")
    data_used: Dict[str, Any] = Field(..., description="Información sobre los datos utilizados")

# --- Helper Functions ---
def clean_llm_response(response: str) -> str:
    """Clean up LLM response by removing unwanted formatting"""
    # Remove thinking tags and their content
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove common unwanted prefixes/suffixes
    unwanted_patterns = [
        r"^RESPUESTA:\s*",
        r"^Respuesta:\s*",
        r"^Según los datos disponibles,?\s*",
        r"\s*\[FIN\]\s*$",
        r"\s*\[END\]\s*$"
    ]

    cleaned = response
    for pattern in unwanted_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)

    return cleaned.strip()

def analyze_data_for_insights(data: Dict[str, Any], insight_type: str, focus_area: Optional[str] = None) -> Dict[str, Any]:
    """Analyze the actual data to extract relevant statistics for AI insights"""
    analysis = {
        "data_summary": {},
        "key_metrics": {},
        "patterns": {},
        "sample_data": {}
    }

    try:
        # Analyze accounts data
        if "accounts" in data and not data["accounts"].empty:
            accounts_df = data["accounts"]
            analysis["data_summary"]["accounts"] = {
                "total_accounts": len(accounts_df),
                "columns": accounts_df.columns.tolist()
            }

            # Political perspective analysis
            if "perspective" in accounts_df.columns:
                perspective_counts = accounts_df["perspective"].value_counts().to_dict()
                analysis["key_metrics"]["political_perspectives"] = perspective_counts

            # Follower analysis
            if "followers_num" in accounts_df.columns:
                followers_stats = {
                    "avg_followers": float(accounts_df["followers_num"].mean()),
                    "max_followers": float(accounts_df["followers_num"].max()),
                    "min_followers": float(accounts_df["followers_num"].min())
                }
                analysis["key_metrics"]["follower_stats"] = followers_stats

            # Sample data
            analysis["sample_data"]["accounts"] = accounts_df.head(3).to_dict(orient="records")

        # Analyze videos data
        if "videos" in data and not data["videos"].empty:
            videos_df = data["videos"]
            analysis["data_summary"]["videos"] = {
                "total_videos": len(videos_df),
                "columns": videos_df.columns.tolist()
            }

            # Views analysis
            if "views" in videos_df.columns:
                views_stats = {
                    "total_views": float(videos_df["views"].sum()),
                    "avg_views": float(videos_df["views"].mean()),
                    "max_views": float(videos_df["views"].max())
                }
                analysis["key_metrics"]["engagement_stats"] = views_stats

            # Date analysis
            if "date" in videos_df.columns:
                videos_df["date"] = pd.to_datetime(videos_df["date"], errors="coerce")
                date_range = {
                    "earliest": videos_df["date"].min().isoformat() if not pd.isna(videos_df["date"].min()) else None,
                    "latest": videos_df["date"].max().isoformat() if not pd.isna(videos_df["date"].max()) else None
                }
                analysis["key_metrics"]["date_range"] = date_range

                # Monthly trends
                if not videos_df["date"].isna().all():
                    monthly_counts = videos_df.groupby(videos_df["date"].dt.to_period("M")).size().to_dict()
                    analysis["patterns"]["monthly_video_trends"] = {str(k): v for k, v in monthly_counts.items()}

            analysis["sample_data"]["videos"] = videos_df.head(3).to_dict(orient="records")

        # Analyze subtitles data
        if "subtitles" in data and not data["subtitles"].empty:
            subtitles_df = data["subtitles"]
            analysis["data_summary"]["subtitles"] = {
                "total_videos_with_subtitles": len(subtitles_df),
                "columns": subtitles_df.columns.tolist()
            }
            analysis["sample_data"]["subtitles"] = subtitles_df.head(2).to_dict(orient="records")

        # Analyze sentiment words data
        if "words" in data and not data["words"].empty:
            words_df = data["words"]
            analysis["data_summary"]["words"] = {
                "total_words": len(words_df),
                "columns": words_df.columns.tolist()
            }

            if "sentimiento" in words_df.columns:
                sentiment_counts = words_df["sentimiento"].value_counts().to_dict()
                analysis["key_metrics"]["sentiment_distribution"] = {str(k): v for k, v in sentiment_counts.items()}

            analysis["sample_data"]["words"] = words_df.head(5).to_dict(orient="records")

    except Exception as e:
        logger.error(f"Error analyzing data for insights: {e}", exc_info=True)
        analysis["error"] = str(e)

    return analysis

async def generate_ai_insights(data_analysis: Dict[str, Any], insight_type: str, focus_area: Optional[str] = None) -> Dict[str, Any]:
    """Generate AI insights using Ollama based on data analysis"""

    # Create focused prompt based on insight type
    prompts = {
        "overview": "Proporciona un resumen general de los datos de TikTok sobre jóvenes chilenos y política. Identifica los hallazgos más importantes.",
        "trends": "Analiza las tendencias temporales y patrones en los datos. ¿Qué cambios se observan a lo largo del tiempo?",
        "sentiment": "Examina el análisis de sentimientos en los datos. ¿Qué emociones y actitudes predominan?",
        "demographics": "Analiza las características demográficas y de audiencia. ¿Qué perfiles de usuarios son más activos?",
        "engagement": "Estudia los patrones de engagement y popularidad. ¿Qué contenido genera más interacción?"
    }

    base_prompt = prompts.get(insight_type, prompts["overview"])

    if focus_area:
        base_prompt += f" Enfócate especialmente en: {focus_area}"

    prompt = f"""
CONTEXTO: Eres un experto en análisis de datos de redes sociales y comportamiento político juvenil en Chile. Analiza los siguientes datos de TikTok.

DATOS ANALIZADOS:
```json
{json.dumps(data_analysis, ensure_ascii=False, indent=2, default=str)}
```

TAREA: {base_prompt}

INSTRUCCIONES:
1. Responde ÚNICAMENTE en ESPAÑOL
2. Genera exactamente 3-5 insights específicos y accionables
3. Cada insight debe incluir:
   - Un título descriptivo
   - Una explicación clara basada en los datos
   - Una métrica o estadística relevante cuando sea posible
4. Proporciona también un resumen general de 2-3 oraciones
5. Sé específico y usa los números reales de los datos
6. NO incluyas formato markdown, solo texto plano

FORMATO DE RESPUESTA (JSON):
{{
    "insights": [
        {{
            "title": "Título del insight",
            "description": "Explicación detallada",
            "metric": "Estadística relevante",
            "category": "categoría del insight"
        }}
    ],
    "summary": "Resumen general de los hallazgos"
}}

RESPUESTA:
"""

    try:
        response = await generate_response(prompt, "qwen3:4b")

        # Try to parse as JSON
        try:
            # Extract JSON from response if it's wrapped in text
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                parsed_response = json.loads(json_str)
                return parsed_response
        except json.JSONDecodeError:
            pass

        # Fallback: parse manually if JSON parsing fails
        insights = []
        lines = response.split('\n')
        current_insight = {}
        summary = ""

        for line in lines:
            line = line.strip()
            if line.startswith('Título:') or line.startswith('Title:'):
                if current_insight:
                    insights.append(current_insight)
                current_insight = {"title": line.split(':', 1)[1].strip()}
            elif line.startswith('Descripción:') or line.startswith('Description:'):
                current_insight["description"] = line.split(':', 1)[1].strip()
            elif line.startswith('Métrica:') or line.startswith('Metric:'):
                current_insight["metric"] = line.split(':', 1)[1].strip()
            elif line.startswith('Resumen:') or line.startswith('Summary:'):
                summary = line.split(':', 1)[1].strip()

        if current_insight:
            insights.append(current_insight)

        if not insights:
            # Create a single insight from the response
            insights = [{
                "title": "Análisis General",
                "description": response[:500] + "..." if len(response) > 500 else response,
                "metric": "Basado en datos disponibles",
                "category": insight_type
            }]

        return {
            "insights": insights,
            "summary": summary or "Análisis completado basado en los datos de TikTok disponibles."
        }

    except Exception as e:
        logger.error(f"Error generating AI insights: {e}", exc_info=True)
        return {
            "insights": [{
                "title": "Error en el análisis",
                "description": f"No se pudo generar el análisis: {str(e)}",
                "metric": "N/A",
                "category": "error"
            }],
            "summary": "Error al procesar los datos para generar insights."
        }

# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    logger.info("Iniciando la aplicación API...")
    try:
        app_state["data"] = load_all_data()
        if not app_state["data"]:
             logger.warning("No se cargaron datos. Algunas funcionalidades pueden no estar disponibles.")
        else:
             logger.info(f"Datos cargados exitosamente. Claves: {list(app_state['data'].keys())}")
             # Optional: Create embeddings if your semantic_search requires them
             # try:
             #     create_embeddings(app_state["data"])
             #     app_state["embeddings_ready"] = True
             #     logger.info("Embeddings creados exitosamente.")
             # except Exception as emb_err:
             #     logger.error(f"Error al crear embeddings: {emb_err}")
             #     app_state["embeddings_ready"] = False

        # Check Ollama status on startup
        ollama_status = await check_ollama_status()
        logger.info(f"Estado de Ollama al inicio: {ollama_status}")
        if ollama_status.get("status") != "available":
            logger.warning("El servidor Ollama parece no estar disponible o accesible.")

    except Exception as e:
        logger.error(f"Error crítico durante el inicio: {e}", exc_info=True)
        # Decide how to handle this - maybe app shouldn't fully start?
        # For now, log the error and continue, endpoints will fail if data is None.
        app_state["data"] = None


# --- API Endpoints ---
@app.get("/", summary="Verificar Estado", description="Endpoint simple para verificar si la API está en ejecución.")
async def read_root():
    # Spanish message
    return {"message": "API del Chatbot de Investigación TikTok está funcionando"}

@app.get("/status/ollama", summary="Verificar Estado de Ollama", description="Verifica si el servidor Ollama es accesible desde la API.")
async def get_ollama_status():
    status = await check_ollama_status()
    if status.get("status") != "available":
        # Return 503 Service Unavailable if Ollama isn't ready
        raise HTTPException(status_code=503, detail=f"Ollama no está disponible: {status.get('message', 'Error desconocido')}")
    return status


@app.get("/data/summary", summary="Obtener Resumen de Datos", description="Devuelve un resumen de los datos cargados actualmente.")
async def get_summary():
    if not app_state.get("data"):
        # Spanish detail
        raise HTTPException(status_code=503, detail="Los datos no están disponibles o no se cargaron correctamente.")
    try:
        summary = get_data_summary(app_state["data"])
        return summary
    except Exception as e:
        logger.error(f"Error generando resumen de datos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al generar el resumen de datos.")


@app.post("/data/insights", response_model=DataInsightsResponse, summary="Generar Insights Inteligentes", description="Genera insights inteligentes usando IA basados en los datos reales disponibles.")
async def generate_data_insights(request: DataInsightsRequest):
    if not app_state.get("data"):
        raise HTTPException(status_code=503, detail="Los datos no están disponibles o no se cargaron correctamente.")

    logger.info(f"Generando insights de tipo '{request.insight_type}' con enfoque: {request.focus_area}")

    try:
        # Analyze the actual data
        data_analysis = analyze_data_for_insights(app_state["data"], request.insight_type, request.focus_area)

        # Generate AI insights
        ai_insights = await generate_ai_insights(data_analysis, request.insight_type, request.focus_area)

        # Prepare response
        response = DataInsightsResponse(
            insights=ai_insights.get("insights", []),
            summary=ai_insights.get("summary", ""),
            data_used={
                "accounts_count": data_analysis.get("data_summary", {}).get("accounts", {}).get("total_accounts", 0),
                "videos_count": data_analysis.get("data_summary", {}).get("videos", {}).get("total_videos", 0),
                "subtitles_count": data_analysis.get("data_summary", {}).get("subtitles", {}).get("total_videos_with_subtitles", 0),
                "words_count": data_analysis.get("data_summary", {}).get("words", {}).get("total_words", 0),
                "analysis_type": request.insight_type,
                "focus_area": request.focus_area
            }
        )

        return response

    except Exception as e:
        logger.error(f"Error generando insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno al generar insights: {str(e)}")


@app.post("/chat", response_model=ChatResponse, summary="Interactuar con el Chatbot", description="Envía una consulta al LLM, opcionalmente generando una visualización.")
async def chat(query_model: QueryModel):
    if not app_state.get("data"):
         # Spanish detail
        raise HTTPException(status_code=503, detail="Los datos no están disponibles o no se cargaron correctamente.")

    query = query_model.query
    logger.info(f"Consulta recibida: '{query}' | Generar Viz: {query_model.generate_visualization} | Tipo Viz: {query_model.visualization_type} | Modelo: {query_model.model}")

    # --- Context Preparation ---
    # Using summary as context for now, replace with semantic_search if embeddings are ready
    relevant_data_summary = {}
    try:
        relevant_data_summary = get_data_summary(app_state["data"]) # Provide general context
        # If using embeddings:
        # if app_state["embeddings_ready"]:
        #     relevant_data_details = semantic_search(query, app_state["data"])
        #     context = json.dumps(relevant_data_details, ensure_ascii=False, default=str)
        # else:
        #     logger.warning("Embeddings no listos, usando resumen general como contexto.")
        #     context = json.dumps(relevant_data_summary, ensure_ascii=False, default=str)
        context = json.dumps(relevant_data_summary, ensure_ascii=False, default=str, indent=2) # Pretty print context

    except Exception as context_err:
        logger.error(f"Error preparando contexto para la consulta '{query}': {context_err}", exc_info=True)
        context = "{}" # Fallback to empty context


    # --- LLM Prompt Construction (Spanish) ---
    prompt = f"""
CONTEXTO: Eres un asistente de investigación IA experto en el análisis de datos sobre jóvenes chilenos y política en TikTok. Tu propósito es ayudar a entender cómo usan esta plataforma para discutir política, diversidad y justicia social.

DATOS DISPONIBLES (RESUMEN GENERAL):
```json
{context}
```

PREGUNTA DEL USUARIO: "{query}"

INSTRUCCIONES:
1. Responde ÚNICAMENTE en ESPAÑOL
2. Sé conciso y directo
3. Si usas los datos, menciona "Según los datos disponibles..."
4. Si no hay datos relevantes, indica "Los datos disponibles no especifican..."
5. NO incluyas etiquetas, marcadores o texto de formato adicional
6. Proporciona SOLO la respuesta final

RESPUESTA:
"""

    # --- Model Selection ---
    # Use model specified in request, fallback to environment variable or hardcoded default
    default_model = os.environ.get("DEFAULT_OLLAMA_MODEL", "qwen3:4b")
    model_to_use = query_model.model or default_model
    logger.info(f"Usando modelo LLM: {model_to_use}")

    # --- Call Ollama ---
    try:
        raw_llm_answer = await generate_response(prompt, model_to_use)

        # Post-process the response to clean up any unwanted formatting
        llm_answer = clean_llm_response(raw_llm_answer)

        response_payload = ChatResponse(
            answer=llm_answer,
            relevant_data=relevant_data_summary # Send back the summary used as context
            # visualization fields will be added below if requested
        )

    except Exception as e:
        logger.error(f"Error al llamar a Ollama para la consulta '{query}': {e}", exc_info=True)
        # Spanish detail
        raise HTTPException(status_code=503, detail=f"Error al comunicarse con el modelo de lenguaje: {str(e)}")

    # --- Generate Visualization (if requested) ---
    if query_model.generate_visualization:
        logger.info(f"Generando visualización para la consulta: '{query}', Tipo: {query_model.visualization_type}")
        try:
            visualization_data = generate_visualization(
                app_state["data"], # Pass the full dataset
                query,
                query_model.visualization_type
            )
            # Check if the visualization function itself returned an error message
            if "error" in visualization_data and visualization_data["error"]:
                 logger.warning(f"Error reportado por generate_visualization: {visualization_data['error']}")
                 response_payload.visualization_error = visualization_data["error"]
                 # Optionally clear the visualization data if it's just an error structure
                 # response_payload.visualization = None
            else:
                 response_payload.visualization = visualization_data

        except Exception as viz_err:
            logger.error(f"Error generando visualización para la consulta '{query}': {viz_err}", exc_info=True)
            # Spanish user-facing error
            response_payload.visualization_error = f"No se pudo generar la visualización: {str(viz_err)}"
            response_payload.visualization = None # Ensure visualization is null on error


    return response_payload


@app.post("/visualize", response_model=VisualizationResponse, summary="Generar Visualización Específica", description="Genera y devuelve datos para un tipo de visualización específico basado en una consulta.")
async def visualize(request: VisualizeRequest):
    if not app_state.get("data"):
        # Spanish detail
        raise HTTPException(status_code=503, detail="Los datos no están disponibles o no se cargaron correctamente.")

    logger.info(f"Solicitud de visualización recibida: '{request.query}', Tipo: {request.visualization_type}")

    try:
        # Pass the full dataset to the visualization function
        visualization_data = generate_visualization(app_state["data"], request.query, request.visualization_type)

        # Check if the visualization function returned an error
        if "error" in visualization_data and visualization_data["error"]:
            logger.error(f"Error devuelto por generate_visualization para '{request.query}': {visualization_data['error']}")
            # Return a 400 Bad Request or similar if the viz couldn't be made based on input/data
            raise HTTPException(status_code=400, detail=f"No se pudo generar la visualización: {visualization_data['error']}")

        return VisualizationResponse(visualization=visualization_data)

    except HTTPException as http_exc:
         raise http_exc # Re-raise known HTTP exceptions
    except Exception as e:
        logger.error(f"Error generando visualización para '{request.query}': {e}", exc_info=True)
        # Spanish detail for internal server error
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al generar la visualización: {str(e)}")


@app.get("/models", summary="Listar Modelos LLM Disponibles", description="Obtiene la lista de modelos disponibles desde el servidor Ollama.")
async def list_models():
    """
    Obtiene la lista de modelos LLM disponibles desde Ollama.
    """
    try:
        models = await get_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Error fetching models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al obtener modelos: {str(e)}")

# --- New CSV Data Endpoints ---

def parse_followers(followers_str):
    """Parse follower count from string format (e.g., '56.1K' -> 56100)"""
    if pd.isna(followers_str) or followers_str == '':
        return 0

    followers_str = str(followers_str).strip()
    if followers_str.endswith('K'):
        return int(float(followers_str[:-1]) * 1000)
    elif followers_str.endswith('M'):
        return int(float(followers_str[:-1]) * 1000000)
    else:
        try:
            return int(float(followers_str))
        except:
            return 0

def clean_perspective(perspective):
    """Clean and standardize perspective values"""
    if pd.isna(perspective) or perspective == '':
        return 'Sin clasificar'

    perspective = str(perspective).strip()
    # Map common variations
    mapping = {
        'Izquierda': 'izquierda',
        'Derecha': 'derecha',
        'Central': 'centro',
        'Periodista': 'periodista',
        '?': 'Sin clasificar',
        '': 'Sin clasificar'
    }
    return mapping.get(perspective, perspective.lower())

@app.get("/data/creators", summary="Obtener Lista de Creadores", description="Devuelve la lista de creadores con información detallada.")
async def get_creators(page: int = 1, limit: int = 50, search: Optional[str] = None):
    """
    Obtiene la lista de creadores desde cuentas_info.csv
    """
    try:
        # Load creators data - use absolute path from project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(project_root, "data", "cuentas_info.csv")

        # Read CSV with error handling for malformed data
        creators_df = pd.read_csv(csv_path, on_bad_lines='skip', quoting=1)

        # Clean and process data
        creators_df['followers_num'] = creators_df['followers'].apply(parse_followers)
        creators_df['perspective_clean'] = creators_df['perspective'].apply(clean_perspective)

        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            mask = (
                creators_df['username'].str.lower().str.contains(search_lower, na=False) |
                creators_df['perspective_clean'].str.lower().str.contains(search_lower, na=False) |
                creators_df['themes'].str.lower().str.contains(search_lower, na=False)
            )
            creators_df = creators_df[mask]

        # Sort by followers (descending)
        creators_df = creators_df.sort_values('followers_num', ascending=False)

        # Calculate pagination
        total = len(creators_df)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit

        # Get page data
        page_data = creators_df.iloc[start_idx:end_idx]

        # Prepare response
        creators = []
        for _, row in page_data.iterrows():
            creator = {
                "username": row['username'],
                "followers": row['followers'],
                "followers_num": row['followers_num'],
                "age": row['age'] if pd.notna(row['age']) else 'No especificado',
                "perspective": row['perspective_clean'],
                "themes": row['themes'] if pd.notna(row['themes']) else 'Sin temas',
                "videos_count": 0  # Will be calculated from videos data if needed
            }
            creators.append(creator)

        return {
            "creators": creators,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }

    except Exception as e:
        logger.error(f"Error loading creators data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al cargar datos de creadores: {str(e)}")

@app.get("/data/videos", summary="Obtener Lista de Videos", description="Devuelve la lista de videos con información detallada.")
async def get_videos(page: int = 1, limit: int = 50, search: Optional[str] = None, creator: Optional[str] = None):
    """
    Obtiene la lista de videos desde combined_tiktok_data_cleaned_with_date.csv
    """
    try:
        # Load videos data (prefer the one with dates) - use absolute path
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            csv_path = os.path.join(project_root, "data", "combined_tiktok_data_cleaned_with_date.csv")
            videos_df = pd.read_csv(csv_path)
        except:
            csv_path = os.path.join(project_root, "data", "combined_tiktok_data_cleaned.csv")
            videos_df = pd.read_csv(csv_path)
            videos_df['date'] = None

        # Clean and process data
        videos_df['views'] = pd.to_numeric(videos_df['views'], errors='coerce').fillna(0)
        videos_df['followers'] = pd.to_numeric(videos_df['followers'], errors='coerce').fillna(0)

        # Parse dates if available
        if 'date' in videos_df.columns:
            videos_df['date'] = pd.to_datetime(videos_df['date'], errors='coerce')

        # Apply filters
        if search:
            search_lower = search.lower()
            mask = (
                videos_df['username'].str.lower().str.contains(search_lower, na=False) |
                videos_df['title'].str.lower().str.contains(search_lower, na=False)
            )
            videos_df = videos_df[mask]

        if creator:
            videos_df = videos_df[videos_df['username'].str.lower() == creator.lower()]

        # Sort by views (descending)
        videos_df = videos_df.sort_values('views', ascending=False)

        # Calculate pagination
        total = len(videos_df)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit

        # Get page data
        page_data = videos_df.iloc[start_idx:end_idx]

        # Prepare response
        videos = []
        for _, row in page_data.iterrows():
            # Calculate engagement rate
            engagement_rate = (row['views'] / max(row['followers'], 1)) * 100 if row['followers'] > 0 else 0

            video = {
                "username": row['username'],
                "title": row['title'][:100] + "..." if len(str(row['title'])) > 100 else row['title'],
                "full_title": row['title'],
                "views": int(row['views']),
                "followers": int(row['followers']),
                "engagement_rate": round(engagement_rate, 2),
                "url": row['url'],
                "date": row['date'].isoformat() if pd.notna(row.get('date')) else None,
                "duration": "N/A"  # Not available in current data
            }
            videos.append(video)

        return {
            "videos": videos,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }

    except Exception as e:
        logger.error(f"Error loading videos data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al cargar datos de videos: {str(e)}")

@app.get("/data/words", summary="Obtener Lista de Palabras", description="Devuelve la lista de palabras con análisis de sentimiento.")
async def get_words(page: int = 1, limit: int = 50, search: Optional[str] = None, sentiment: Optional[str] = None):
    """
    Obtiene la lista de palabras desde data.csv
    """
    try:
        # Load words data - use absolute path
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(project_root, "data", "data.csv")
        words_df = pd.read_csv(csv_path)

        # Clean and process data
        words_df['count'] = pd.to_numeric(words_df['count'], errors='coerce').fillna(0)
        words_df['sentimiento'] = pd.to_numeric(words_df['sentimiento'], errors='coerce').fillna(0)

        # Apply filters
        if search:
            search_lower = search.lower()
            mask = words_df['word'].str.lower().str.contains(search_lower, na=False)
            words_df = words_df[mask]

        if sentiment:
            if sentiment == 'positive':
                words_df = words_df[words_df['sentimiento'] > 0]
            elif sentiment == 'negative':
                words_df = words_df[words_df['sentimiento'] < 0]
            elif sentiment == 'neutral':
                words_df = words_df[words_df['sentimiento'] == 0]

        # Sort by count (descending)
        words_df = words_df.sort_values('count', ascending=False)

        # Calculate pagination
        total = len(words_df)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit

        # Get page data
        page_data = words_df.iloc[start_idx:end_idx]

        # Prepare response
        words = []
        for _, row in page_data.iterrows():
            # Determine sentiment label
            sentiment_value = row['sentimiento']
            if sentiment_value > 0:
                sentiment_label = 'Positivo'
            elif sentiment_value < 0:
                sentiment_label = 'Negativo'
            else:
                sentiment_label = 'Neutral'

            # Extract family information
            family_1 = row.get('type_1', 'Sin clasificar')
            family_2 = row.get('type_2', 'Sin clasificar')

            word = {
                "word": row['word'],
                "frequency": int(row['count']),
                "sentiment_score": float(sentiment_value),
                "sentiment_label": sentiment_label,
                "family_1": family_1,
                "family_2": family_2,
                "videos_count": int(row['count']),  # Using count as proxy for video appearances
                "engagement_score": int(row['count']) * abs(sentiment_value)  # Simple engagement calculation
            }
            words.append(word)

        return {
            "words": words,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }

    except Exception as e:
        logger.error(f"Error loading words data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al cargar datos de palabras: {str(e)}")

# --- Run the application ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)