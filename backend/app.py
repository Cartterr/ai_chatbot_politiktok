# backend/app.py

from fastapi import FastAPI, HTTPException, Body, Query
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
from data_loader import load_all_data, get_data_summary, determine_relevant_datasets, get_relevant_data_summary, analyze_word_usage_by_date
from smart_agent import search_with_agent, get_agent_info
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
    data_sources: Optional[List[Dict[str, Any]]] = Field(None, description="Lista de fuentes de datos utilizadas con detalles específicos.")
    query_analysis: Optional[str] = Field(None, description="Análisis de la consulta y fuentes relevantes.")
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

def extract_word_with_ai_parsing(query: str) -> str:
    """
    Use smart regex patterns to extract the main target word, avoiding articles.
    This is more reliable and faster than calling the AI model.
    """
    return extract_word_with_regex_fallback(query)

def extract_word_with_regex_fallback(query: str) -> str:
    """Smart regex-based word extraction that avoids articles"""
    import re
    
    query_lower = query.lower()
    logger.debug(f"🔍 Regex fallback para: '{query_lower}'")
    
    # STEP 1: Comprehensive patterns that capture the target word correctly
    patterns = [
        # "palabra X" patterns - capture X, not articles before it
        r'palabra\s+(?:la\s+|el\s+|una\s+|un\s+)?([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',
        r'sobre\s+la\s+palabra\s+([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',
        r'datos\s+relevantes\s+sobre\s+la\s+palabra\s+([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',
        r'relevantes\s+sobre\s+la\s+palabra\s+([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',
        
        # "sobre X" patterns
        r'sobre\s+(?:la\s+|el\s+|una\s+|un\s+)?([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',
        r'datos\s+sobre\s+(?:la\s+|el\s+|una\s+|un\s+)?([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',
        r'información\s+sobre\s+(?:la\s+|el\s+|una\s+|un\s+)?([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',
        
        # "de X" patterns
        r'datos\s+de\s+(?:la\s+|el\s+|una\s+|un\s+)?([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',
        r'información\s+de\s+(?:la\s+|el\s+|una\s+|un\s+)?([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',
        r'análisis\s+de\s+(?:la\s+|el\s+|una\s+|un\s+)?([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',
        
        # Direct word patterns with articles
        r'(?:la\s+|el\s+|una\s+|un\s+)([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]{4,})',
    ]
    
    # HARDCODED BLACKLIST: Spanish words that should NEVER be target words
    spanish_meaningless_words = {
        # Articles
        'la', 'el', 'una', 'un', 'las', 'los', 'unas', 'unos',
        
        # Prepositions
        'de', 'del', 'en', 'con', 'por', 'para', 'sin', 'sobre', 'bajo', 'ante', 'tras', 
        'desde', 'hasta', 'hacia', 'contra', 'entre', 'mediante', 'durante', 'según',
        
        # Conjunctions
        'y', 'o', 'u', 'e', 'ni', 'pero', 'mas', 'sino', 'aunque', 'porque', 'pues', 
        'que', 'si', 'como', 'cuando', 'donde', 'mientras', 'entonces',
        
        # Pronouns
        'yo', 'tú', 'él', 'ella', 'nosotros', 'vosotros', 'ellos', 'ellas',
        'me', 'te', 'se', 'nos', 'os', 'le', 'les', 'lo', 'los', 'la', 'las',
        'mi', 'tu', 'su', 'nuestro', 'vuestro', 'suyo', 'mío', 'tuyo',
        'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
        'aquel', 'aquella', 'aquellos', 'aquellas', 'esto', 'eso', 'aquello',
        
        # Adverbs
        'muy', 'más', 'menos', 'mucho', 'poco', 'bastante', 'demasiado', 'tan', 'tanto',
        'sí', 'no', 'también', 'tampoco', 'además', 'incluso', 'solo', 'solamente',
        'bien', 'mal', 'mejor', 'peor', 'así', 'aquí', 'ahí', 'allí', 'acá', 'allá',
        'hoy', 'ayer', 'mañana', 'ahora', 'luego', 'después', 'antes', 'siempre', 'nunca',
        
        # Verbs (common auxiliary and meaningless ones)
        'ser', 'estar', 'tener', 'haber', 'hacer', 'ir', 'venir', 'dar', 'ver', 'saber',
        'poder', 'querer', 'decir', 'poner', 'salir', 'llegar', 'pasar', 'quedar',
        'es', 'son', 'está', 'están', 'tiene', 'tienen', 'hay', 'había', 'habrá',
        'hace', 'hacen', 'va', 'van', 'viene', 'vienen', 'da', 'dan', 've', 'ven',
        
        # Common question words
        'qué', 'quién', 'quiénes', 'cuál', 'cuáles', 'cómo', 'cuándo', 'dónde', 'por qué',
        'cuánto', 'cuántos', 'cuánta', 'cuántas',
        
        # Common filler/context words
        'hola', 'dime', 'datos', 'información', 'relevantes', 'palabra', 'palabras', 
        'término', 'términos', 'análisis', 'general', 'específico', 'particular',
        'cosa', 'cosas', 'algo', 'nada', 'todo', 'todos', 'todas', 'otro', 'otra', 'otros', 'otras',
        'mismo', 'misma', 'mismos', 'mismas', 'tal', 'tales', 'cada', 'cualquier', 'cualquiera',
        
        # Action words (verbs that don't represent content)
        'dame', 'muestra', 'muéstrame', 'genera', 'generar', 'crear', 'hacer', 'hacen',
        'obtener', 'conseguir', 'buscar', 'encontrar', 'mostrar', 'enseñar', 'explicar',
        
        # Chart/visualization related words (not content)
        'gráfico', 'gráficos', 'grafico', 'graficos', 'chart', 'charts', 'visualización',
        'visualizaciones', 'diagrama', 'diagramas', 'tabla', 'tablas', 'resumen', 'resúmen',
        
        # Numbers and quantifiers
        'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'diez',
        'primero', 'segundo', 'tercero', 'último', 'varios', 'algunas', 'algunos', 'muchas', 'muchos',
        
        # Time expressions
        'día', 'días', 'semana', 'semanas', 'mes', 'meses', 'año', 'años', 'tiempo', 'vez', 'veces',
        
        # Size/quantity expressions
        'grande', 'pequeño', 'mayor', 'menor', 'alto', 'bajo', 'largo', 'corto', 'nuevo', 'viejo'
    }
    
    # STEP 1: PRIORITY EXTRACTION - Political/Social terms first (they're always meaningful)
    important_terms = [
        # Political terms
        'revolución', 'democracia', 'justicia', 'libertad', 'igualdad', 'política', 'gobierno',
        'corrupción', 'protesta', 'manifestación', 'derecho', 'derechos', 'social', 'económico',
        'economía', 'educación', 'salud', 'trabajo', 'empleo', 'pobreza', 'riqueza', 'clase',
        'feminismo', 'machismo', 'género', 'violencia', 'paz', 'guerra', 'conflicto', 'crisis',
        'cambio', 'reforma', 'transformación', 'progreso', 'conservador', 'liberal', 'izquierda',
        'derecha', 'centro', 'partido', 'elecciones', 'voto', 'candidato', 'presidente', 'congreso',
        'senado', 'diputado', 'alcalde', 'gobernador', 'constitución', 'ley', 'norma', 'decreto',
        # Also include versions without accents
        'revolucion', 'democracia', 'politica', 'educacion', 'economia'
    ]
    
    words_in_query = re.findall(r'\b([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)\b', query_lower)
    logger.info(f"   🔍 Palabras encontradas en query: {words_in_query}")
    
    # First priority: Look for important political/social terms
    for word in words_in_query:
        if word in important_terms:
            logger.info(f"   🎯 TÉRMINO POLÍTICO/SOCIAL ENCONTRADO: '{word}' ✅")
            return word
    
    # STEP 2: Try each contextual pattern
    for i, pattern in enumerate(patterns):
        matches = re.findall(pattern, query_lower)
        logger.info(f"   📝 Patrón {i+1}: '{pattern}' → {matches}")
        
        for match in matches:
            word = match.strip()
            if word and word not in spanish_meaningless_words and len(word) > 3:
                logger.info(f"   🎯 PALABRA CONTEXTUAL VÁLIDA: '{word}' ✅")
                return word
    
    # STEP 3: Extract any meaningful word that's not meaningless
    logger.info(f"   🔍 Buscando palabras significativas en: {words_in_query}")
    for word in words_in_query:
        if (word not in spanish_meaningless_words and 
            len(word) > 3 and 
            not word.isdigit()):
            logger.info(f"   🎯 PALABRA SIGNIFICATIVA ENCONTRADA: '{word}' ✅")
            return word
    
    logger.warning(f"   ❌ NO SE ENCONTRÓ NINGUNA PALABRA SIGNIFICATIVA en: '{query_lower}'")
    return None

def extract_key_terms_from_query(query: str) -> dict:
    """
    Extract key terms, words, and entities from user query for smart filtering.
    Uses AI-powered parsing to intelligently identify the target words.
    Returns a dictionary with extracted information.
    """
    import re
    
    query_lower = query.lower()
    extracted = {
        'target_words': [],
        'usernames': [],
        'entities': [],
        'intent': 'general'
    }
    
    logger.info(f"🔍 INICIANDO extracción para: '{query}'")
    
    # SMART WORD EXTRACTION
    # Use improved regex patterns to extract the main word, avoiding articles
    logger.info(f"   🔧 Calling extract_word_with_ai_parsing for: '{query}'")
    smart_extracted_word = extract_word_with_ai_parsing(query)
    logger.info(f"   🔧 extract_word_with_ai_parsing returned: '{smart_extracted_word}'")
    
    # CRITICAL DEBUG: Test if "revolución" exists in the dataset
    if smart_extracted_word and smart_extracted_word.lower() == 'revolución':
        logger.info(f"   🔍 TESTING: Checking if 'revolución' exists in dataset...")
        if 'words' in app_state.get('data', {}):
            words_df = app_state['data']['words']
            if not words_df.empty and 'word' in words_df.columns:
                revolucion_count = words_df[words_df['word'].str.lower() == 'revolución'].shape[0]
                logger.info(f"   📊 Found {revolucion_count} instances of 'revolución' in words dataset")
                if revolucion_count == 0:
                    logger.warning(f"   ⚠️  'revolución' NOT FOUND in dataset - this explains the filtering issue!")
        else:
            logger.warning(f"   ⚠️  No 'words' dataset available for testing")
    
    if smart_extracted_word:
        # SAFETY CHECK: Never allow meaningless Spanish words
        spanish_meaningless_words = {
            'la', 'el', 'una', 'un', 'las', 'los', 'de', 'del', 'en', 'con', 'por', 'para', 'sin', 'sobre',
            'y', 'o', 'que', 'si', 'como', 'cuando', 'donde', 'muy', 'más', 'menos', 'mucho', 'poco',
            'ser', 'estar', 'tener', 'haber', 'hacer', 'ir', 'es', 'son', 'está', 'están', 'tiene', 'hay',
            'hola', 'dime', 'datos', 'información', 'relevantes', 'palabra', 'palabras', 'gráfico', 'gráficos',
            'uno', 'dos', 'tres', 'tiempo', 'día', 'días', 'año', 'años', 'grande', 'pequeño', 'nuevo', 'viejo'
        }
        
        if smart_extracted_word.lower() not in spanish_meaningless_words:
            extracted['target_words'].append(smart_extracted_word)
            logger.info(f"   🎯 SMART EXTRACTION extrajo: '{smart_extracted_word}' de query: '{query}'")
        else:
            logger.warning(f"   ⚠️  BLOCKED meaningless word: '{smart_extracted_word}' from query: '{query}'")
    
    # Extract words mentioned after "palabra", "término", etc.
    word_patterns = [
        r'palabra\s+"([^"]+)"',  # "palabra 'revolución'"
        r"palabra\s+'([^']+)'",  # "palabra 'revolución'"
        r'palabra\s+([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',  # "palabra revolución"
        r'término\s+"([^"]+)"',
        r"término\s+'([^']+)'",
        r'término\s+([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',
        r'sobre\s+la\s+palabra\s+([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',  # "sobre la palabra revolución"
        r'sobre\s+"([^"]+)"',  # "sobre 'democracia'"
        r"sobre\s+'([^']+)'",
        r'sobre\s+([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',  # "sobre democracia"
        r'de\s+la\s+palabra\s+([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',  # "de la palabra revolución"
        r'de\s+"([^"]+)"',
        r"de\s+'([^']+)'",
        r'análisis\s+de\s+([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',
        r'datos\s+de\s+([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',
        r'información\s+de\s+([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',
        r'datos\s+relevantes\s+sobre\s+la\s+palabra\s+([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)',  # "datos relevantes sobre la palabra revolución"
        r'relevantes\s+sobre\s+la\s+palabra\s+([a-záéíóúñüA-ZÁÉÍÓÚÑÜ]+)'  # "relevantes sobre la palabra revolución"
    ]
    
    for pattern in word_patterns:
        matches = re.findall(pattern, query_lower)
        extracted['target_words'].extend(matches)
        logger.debug(f"   📝 Patrón '{pattern}' encontró: {matches}")
    
    # AGGRESSIVE EXTRACTION: Look for "revolución" specifically in the user's example
    if 'revolución' in query_lower:
        extracted['target_words'].append('revolución')
        logger.debug(f"   🎯 ENCONTRADO 'revolución' directamente en query")
    
    if 'democracia' in query_lower:
        extracted['target_words'].append('democracia')
        logger.debug(f"   🎯 ENCONTRADO 'democracia' directamente en query")
    
    # Extract usernames (with @)
    username_pattern = r'@([a-zA-Z0-9_\.]+)'
    usernames = re.findall(username_pattern, query)
    extracted['usernames'].extend(usernames)
    
    # Extract quoted words/phrases
    quoted_patterns = [
        r'"([^"]+)"',  # "revolución"
        r"'([^']+)'"   # 'revolución'
    ]
    
    for pattern in quoted_patterns:
        matches = re.findall(pattern, query)
        extracted['target_words'].extend(matches)
    
    # Look for standalone important words (nouns that could be search terms)
    # Common political/social terms that are likely search targets
    important_terms = [
        'revolución', 'revolucion', 'democracia', 'justicia', 'libertad', 'igualdad', 'política', 'politica', 'gobierno',
        'corrupción', 'corrupcion', 'protesta', 'manifestación', 'manifestacion', 'derecho', 'derechos', 'social', 'económico', 'economico',
        'educación', 'educacion', 'salud', 'trabajo', 'empleo', 'crisis', 'reforma', 'cambio', 'progreso',
        'conservador', 'liberal', 'izquierda', 'derecha', 'centro', 'feminismo', 'machismo',
        'violencia', 'paz', 'guerra', 'conflicto', 'unión', 'union', 'diversidad', 'inclusión', 'inclusion',
        'presidente', 'congreso', 'senado', 'diputado', 'diputados', 'senador', 'senadores',
        'elección', 'eleccion', 'elecciones', 'voto', 'votos', 'campaña', 'campana', 'candidato', 'candidatos',
        'partido', 'partidos', 'oposición', 'oposicion', 'oficialismo', 'coalición', 'coalicion'
    ]
    
    # Find important terms in the query
    words_in_query = re.findall(r'\b([a-záéíóúñü]{4,})\b', query_lower)
    for word in words_in_query:
        if word in important_terms:
            extracted['target_words'].append(word)
    
    # Remove duplicates and clean
    extracted['target_words'] = list(set([w.strip() for w in extracted['target_words'] if w.strip()]))
    extracted['usernames'] = list(set([u.strip() for u in extracted['usernames'] if u.strip()]))
    
    # Debug logging
    logger.debug(f"🔍 Extracción de términos para query: '{query}'")
    logger.debug(f"   🎯 Palabras encontradas: {extracted['target_words']}")
    logger.debug(f"   👤 Usuarios encontrados: {extracted['usernames']}")
    
    return extracted

def analyze_query_for_visualization_type(query: str, requested_type: str = None) -> tuple:
    """
    Analyze the user's query to intelligently suggest the best visualization type and extract key terms.
    Returns (visualization_type, extracted_terms, smart_query_for_filtering).
    """
    if requested_type:
        extracted = extract_key_terms_from_query(query)
        smart_query = extracted['target_words'][0] if extracted['target_words'] else query
        return requested_type, extracted, smart_query
    
    query_lower = query.lower()
    extracted = extract_key_terms_from_query(query)
    
    # Time-related keywords → time_series
    time_keywords = [
        'tiempo', 'temporal', 'evolución', 'evoluciona', 'cambio', 'cambios', 'tendencia', 'tendencias',
        'histórico', 'historia', 'cronología', 'desarrollo', 'progreso', 'antes', 'después',
        'periodo', 'fecha', 'fechas', 'año', 'años', 'mes', 'meses', 'día', 'días',
        'durante', 'a lo largo', 'timeline', 'serie temporal', 'línea de tiempo'
    ]
    
    # Comparison keywords → comparison
    comparison_keywords = [
        'comparar', 'comparación', 'comparativa', 'versus', 'vs', 'diferencia', 'diferencias',
        'contraste', 'entre', 'mejor', 'peor', 'mayor', 'menor', 'más', 'menos',
        'ranking', 'top', 'clasificación', 'competencia', 'frente a', 'contra'
    ]
    
    # Sentiment keywords → sentiment
    sentiment_keywords = [
        'sentimiento', 'sentimientos', 'opinión', 'opiniones', 'percepción', 'percepções',
        'positivo', 'negativo', 'neutral', 'emocional', 'emoción', 'emociones',
        'satisfacción', 'insatisfacción', 'feliz', 'triste', 'enojado', 'contento',
        'análisis de sentimiento', 'polaridad', 'actitud', 'reacción', 'reacciones'
    ]
    
    # Summary/overview keywords → summary
    summary_keywords = [
        'resumen', 'resúmen', 'general', 'panorama', 'overview', 'visión general',
        'total', 'totales', 'estadísticas', 'estadística', 'números', 'cifras',
        'datos generales', 'información general', 'cuántos', 'cuántas', 'cantidad',
        'distribución', 'proporción', 'porcentaje', 'estadísticas generales', 'gráficos'
    ]
    
    # Individual chart keywords → focused_chart (new type!)
    individual_keywords = [
        'individual', 'uno', 'una', 'gráfico', 'chart', 'simple', 'específico', 'enfocado',
        'solo', 'solamente', 'únicamente', 'particular', 'concreto', 'puntual'
    ]
    
    # User-specific keywords → comparison (to compare users)
    user_keywords = [
        'usuario', 'usuarios', 'creador', 'creadores', 'cuenta', 'cuentas',
        'perfil', 'perfiles', '@', 'influencer', 'influencers', 'tiktoker', 'tiktokers'
    ]
    
    # Word-specific keywords → could be sentiment or summary
    word_keywords = [
        'palabra', 'palabras', 'término', 'términos', 'vocabulario', 'léxico',
        'expresión', 'expresiones', 'frase', 'frases', 'texto', 'textos'
    ]
    
    # Count matches for each category
    time_score = sum(1 for keyword in time_keywords if keyword in query_lower)
    comparison_score = sum(1 for keyword in comparison_keywords if keyword in query_lower)
    sentiment_score = sum(1 for keyword in sentiment_keywords if keyword in query_lower)
    summary_score = sum(1 for keyword in summary_keywords if keyword in query_lower)
    individual_score = sum(1 for keyword in individual_keywords if keyword in query_lower)
    user_score = sum(1 for keyword in user_keywords if keyword in query_lower)
    word_score = sum(1 for keyword in word_keywords if keyword in query_lower)
    
    # Boost scores based on extracted terms
    if extracted['target_words']:
        word_score += 2  # Having specific words suggests word analysis
        if any(keyword in query_lower for keyword in sentiment_keywords):
            sentiment_score += 3  # Word + sentiment = strong sentiment analysis signal
        else:
            summary_score += 2  # Word analysis often means summary
    
    if extracted['usernames']:
        user_score += 3
        comparison_score += 2  # Users often compared
    
    # Specific patterns that strongly suggest certain visualizations
    if any(pattern in query_lower for pattern in ['evolución de', 'cambio en', 'a lo largo del tiempo', 'serie temporal']):
        viz_type = 'time_series'
    elif any(pattern in query_lower for pattern in ['comparar', 'vs', 'versus', 'diferencia entre', 'mejor que']):
        viz_type = 'comparison'
    elif any(pattern in query_lower for pattern in ['sentimiento', 'análisis de sentimiento', 'opinión']):
        viz_type = 'sentiment'
    elif any(pattern in query_lower for pattern in ['uno individual', 'gráfico individual', 'chart individual', 'uno solo']):
        viz_type = 'focused_chart'  # New type for individual charts
    else:
        # Determine best type based on scores
        scores = {
            'time_series': time_score,
            'comparison': comparison_score + user_score,  # Users often compared
            'sentiment': sentiment_score + (word_score * 0.3),  # Words often analyzed for sentiment
            'summary': summary_score + (word_score * 0.5),  # Words often summarized
            'focused_chart': individual_score * 2  # Strong preference for individual charts when requested
        }
        
        # Find the highest scoring type
        best_type = max(scores.items(), key=lambda x: x[1])
        
        # If no clear winner or very low scores, default to summary
        if best_type[1] == 0 or best_type[1] < 2:
            viz_type = 'summary'
        else:
            viz_type = best_type[0]
    
    # Determine the smart query for filtering
    if extracted['target_words']:
        smart_query = extracted['target_words'][0]  # Use the first/most relevant word
        logger.info(f"   🎯 Using extracted target word: '{smart_query}'")
    elif extracted['usernames']:
        smart_query = extracted['usernames'][0]  # Use the first username
        logger.info(f"   👤 Using extracted username: '{smart_query}'")
    else:
        # FALLBACK: Try to extract using the same robust logic from extract_word_with_regex_fallback
        logger.warning(f"   ⚠️  No target words extracted, trying fallback extraction...")
        fallback_word = extract_word_with_regex_fallback(query)
        
        if fallback_word:
            smart_query = fallback_word
            logger.info(f"   🔄 Fallback extraction found: '{smart_query}'")
        else:
            # FINAL FALLBACK: Don't use the full query, instead return None to trigger no-data handling
            logger.warning(f"   ❌ No meaningful word found for query: '{query}' - will trigger no-data response")
            smart_query = None  # This will trigger no-data handling in visualization
    
    return viz_type, extracted, smart_query

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
        response = await generate_response(prompt, "Qwen2.5-Coder:32B")

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

    # --- Smart Agent Analysis ---
    smart_agent_result = None
    date_analysis_result = None
    date_keywords = ["fecha", "fechas", "cuando", "cuándo", "momento", "tiempo", "temporal", "día", "días", "mes", "año", "periodo"]
    query_lower = query.lower()
    
    # Use smart agent for comprehensive search
    try:
        smart_agent_result = search_with_agent(query)
        logger.info(f"🤖 Smart agent found {smart_agent_result['summary']['total_matches']} matches across {smart_agent_result['summary']['datasets_with_matches']} datasets")
    except Exception as agent_err:
        logger.error(f"❌ Smart agent error: {agent_err}")
        smart_agent_result = None
    
    # Check if query is asking about dates/temporal patterns
    is_date_query = any(keyword in query_lower for keyword in date_keywords)
    
    if is_date_query:
        # Extract potential words to analyze
        word_patterns = re.findall(r'\b(?:palabra|término|concepto)\s+["\']?(\w+)["\']?', query_lower)
        if not word_patterns:
            # Look for specific words mentioned in quotes or after "de"
            word_patterns = re.findall(r'["\'](\w+)["\']', query)
            if not word_patterns:
                word_patterns = re.findall(r'\b(?:de\s+la?\s+)?(\w+)\s+y\s+sus\s+derivadas?', query_lower)
                if not word_patterns:
                    # Look for common political/social terms
                    political_terms = ["violencia", "política", "democracia", "justicia", "igualdad", "libertad", "derechos"]
                    word_patterns = [term for term in political_terms if term in query_lower]
        
        if word_patterns:
            target_word = word_patterns[0]
            logger.info(f"🗓️ Detectada consulta temporal sobre la palabra: '{target_word}'")
            try:
                date_analysis_result = analyze_word_usage_by_date(app_state["data"], target_word)
                logger.info(f"✅ Análisis temporal completado para '{target_word}': {date_analysis_result.get('total_matches', 0)} coincidencias")
            except Exception as date_err:
                logger.error(f"❌ Error en análisis temporal: {date_err}")
                date_analysis_result = {"error": f"Error en análisis temporal: {str(date_err)}"}

    # --- Context Preparation ---
    # Determine which datasets are relevant for this query
    relevant_data_summary = {}
    try:
        relevant_datasets = determine_relevant_datasets(query, app_state["data"])
        relevant_data_summary = get_relevant_data_summary(app_state["data"], relevant_datasets, query)
        context = json.dumps(relevant_data_summary["data_summary"], ensure_ascii=False, default=str, indent=2)

    except Exception as context_err:
        logger.error(f"Error preparando contexto para la consulta '{query}': {context_err}", exc_info=True)
        context = "{}" # Fallback to empty context
        relevant_data_summary = {"data_summary": {}, "sources": [], "query_analysis": ""}


    # --- Smart Query Analysis ---
    viz_context = ""
    smart_query = query
    extracted_terms = {}
    
    if query_model.generate_visualization:
        try:
            suggested_viz_type, extracted_terms, smart_query = analyze_query_for_visualization_type(query, query_model.visualization_type)
        except Exception as e:
            logger.error(f"❌ Error en análisis inteligente: {e}")
            suggested_viz_type = 'summary'
            extracted_terms = {}
            smart_query = query
        
        # Build context message
        if extracted_terms.get('target_words'):
            target_word = extracted_terms['target_words'][0]
            viz_context = f"\n\nNOTA: Se generará automáticamente una visualización tipo '{suggested_viz_type}' enfocada en '{target_word}' para complementar la respuesta."
        elif extracted_terms.get('usernames'):
            target_user = extracted_terms['usernames'][0]
            viz_context = f"\n\nNOTA: Se generará automáticamente una visualización tipo '{suggested_viz_type}' enfocada en el usuario '{target_user}' para complementar la respuesta."
        else:
            viz_context = f"\n\nNOTA: Se generará automáticamente una visualización tipo '{suggested_viz_type}' basada en tu consulta para complementar la respuesta."
        
        logger.info(f"🧠 ANÁLISIS SUPER INTELIGENTE:")
        logger.info(f"   📝 Query original: '{query}'")
        logger.info(f"   🎯 Palabras extraídas: {extracted_terms.get('target_words', [])}")
        logger.info(f"   👤 Usuarios extraídos: {extracted_terms.get('usernames', [])}")
        logger.info(f"   📊 Tipo sugerido: {suggested_viz_type}")
        logger.info(f"   🔍 Query filtrado FINAL: '{smart_query}'")
        if smart_query != query:
            logger.info(f"   ⚡ TRANSFORMACIÓN: '{query}' → '{smart_query}'")
        else:
            logger.info(f"   ⚡ SIN CAMBIOS: query mantenido como '{smart_query}'")
    
    # Add smart agent and enhanced temporal context
    agent_context = ""
    if smart_agent_result and smart_agent_result['summary']['total_matches'] > 0:
        agent_context = f"""

BÚSQUEDA INTELIGENTE AUTOMÁTICA:
```json
{json.dumps(smart_agent_result, ensure_ascii=False, default=str, indent=2)}
```"""
    
    # Add enhanced temporal context for better date analysis
    temporal_context = ""
    if "videos" in app_state["data"] and not app_state["data"]["videos"].empty:
        df = app_state["data"]["videos"]
        if "date" in df.columns and "user_type" in df.columns and "perspective" in df.columns:
            temporal_context = f"""

INFORMACIÓN TEMPORAL ADICIONAL DISPONIBLE:
- Dataset temporal completo con {len(df)} videos desde {df['date'].min()} hasta {df['date'].max()}
- Tipos de usuario disponibles: {', '.join(df['user_type'].dropna().unique()[:5])}
- Perspectivas políticas: {', '.join(df['perspective'].dropna().unique())}
- Métricas de actividad diaria y patrones temporales disponibles
- Análisis de engagement y visualizaciones por fechas disponible"""
    
    date_context = ""
    if date_analysis_result:
        if "error" not in date_analysis_result:
            date_context = f"""

ANÁLISIS TEMPORAL ESPECÍFICO:
```json
{json.dumps(date_analysis_result, ensure_ascii=False, default=str, indent=2)}
```"""
        else:
            date_context = f"\n\nNOTA: Error en análisis temporal: {date_analysis_result['error']}"

    prompt = f"""
CONTEXTO: Eres un asistente de investigación IA experto en el análisis de datos sobre jóvenes chilenos y política en TikTok. Tu propósito es ayudar a entender cómo usan esta plataforma para discutir política, diversidad y justicia social.

DATOS DISPONIBLES (RESUMEN GENERAL):
```json
{context}
```{temporal_context}{agent_context}{date_context}

PREGUNTA DEL USUARIO: "{query}"{viz_context}

INSTRUCCIONES:
1. Responde ÚNICAMENTE en ESPAÑOL
2. Sé conciso y directo
3. Si usas los datos, menciona "Según los datos disponibles..."
4. NUNCA digas "Los datos disponibles no especifican..." si hay INFORMACIÓN TEMPORAL ADICIONAL DISPONIBLE
5. Si hay BÚSQUEDA INTELIGENTE AUTOMÁTICA disponible, prioriza esa información para respuestas específicas
6. Si hay ANÁLISIS TEMPORAL ESPECÍFICO disponible, úsalo para responder preguntas sobre fechas y patrones temporales
7. Para preguntas sobre actividad de usuarios (izquierda, derecha, género, etc.), usa la información de user_type_counts y perspective_counts junto con yearly_distribution
8. Para preguntas sobre días con más publicaciones, usa top_activity_days y max_daily_posts
9. Para preguntas sobre fechas de alta visualización, combina date_range con avg_views y total_views
10. Proporciona fechas específicas, rangos de tiempo y ejemplos concretos siempre que sea posible
11. Combina información de múltiples fuentes cuando sea relevante (subtítulos, transcripciones, etc.)
12. NO incluyas etiquetas, marcadores o texto de formato adicional
13. Proporciona SOLO la respuesta final
14. Si se menciona que se generará una visualización, puedes hacer referencia a ella diciendo "La visualización adjunta muestra..." o similar

RESPUESTA:
"""

    # --- Model Selection ---
    # Use model specified in request, fallback to environment variable or hardcoded default
    default_model = os.environ.get("DEFAULT_OLLAMA_MODEL", "Qwen2.5-Coder:32B")
    model_to_use = query_model.model or default_model
    logger.info(f"Usando modelo LLM: {model_to_use}")

    # --- Call Ollama ---
    try:
        raw_llm_answer = await generate_response(prompt, model_to_use)

        # Post-process the response to clean up any unwanted formatting
        llm_answer = clean_llm_response(raw_llm_answer)

        response_payload = ChatResponse(
            answer=llm_answer,
            relevant_data=relevant_data_summary.get("data_summary", {}),
            data_sources=relevant_data_summary.get("sources", []),
            query_analysis=relevant_data_summary.get("query_analysis", "")
            # visualization fields will be added below if requested
        )

    except Exception as e:
        logger.error(f"Error al llamar a Ollama para la consulta '{query}': {e}", exc_info=True)
        # Spanish detail
        raise HTTPException(status_code=503, detail=f"Error al comunicarse con el modelo de lenguaje: {str(e)}")

    # --- Smart Visualization Generation ---
    if query_model.generate_visualization:
        # Check if we have a meaningful smart_query
        if smart_query is None:
            logger.warning(f"No meaningful word extracted from query '{query}' - returning no-data response")
            visualization_data = {
                "type": "no_data",
                "title": "Sin Datos Disponibles",
                "message": f"No se encontraron términos específicos para filtrar en la consulta '{query}'.",
                "suggestion": "Intenta usar palabras más específicas como nombres de conceptos políticos o sociales.",
                "filter_info": {"filtered": False}
            }
        else:
            logger.info(f"Generando visualización inteligente - Query original: '{query}', Query filtrado: '{smart_query}', Tipo: {suggested_viz_type}")
            
            try:
                visualization_data = generate_visualization(
                    app_state["data"], # Pass the full dataset
                    smart_query,  # Use the smart extracted query instead of the full query
                    suggested_viz_type
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
        
        # Handle the case where smart_query is None (no meaningful word found)
        if smart_query is None:
            response_payload.visualization = visualization_data


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
            logger.warning(f"Error devuelto por generate_visualization para '{request.query}': {visualization_data['error']}")
            # Instead of throwing 400, return the error in the response so frontend can handle it gracefully
            # This prevents the frontend from getting 400 errors and allows it to show user-friendly messages
            return VisualizationResponse(visualization=visualization_data)

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
        models_response = await get_models()
        return models_response
    except Exception as e:
        logger.error(f"Error fetching models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al obtener modelos: {str(e)}")

# --- Dataset Viewing Endpoints ---

@app.get("/dataset/{dataset_name}", summary="Ver Dataset Específico", description="Obtiene datos de un dataset específico con paginación.")
async def view_dataset(
    dataset_name: str, 
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=500, description="Elementos por página"),
    search: Optional[str] = Query(None, description="Término de búsqueda opcional")
):
    """
    Endpoint para ver los datos de un dataset específico
    """
    if not app_state.get("data"):
        raise HTTPException(status_code=503, detail="Los datos no están disponibles.")
    
    if dataset_name not in app_state["data"]:
        available_datasets = list(app_state["data"].keys())
        raise HTTPException(
            status_code=404, 
            detail=f"Dataset '{dataset_name}' no encontrado. Datasets disponibles: {available_datasets}"
        )
    
    df = app_state["data"][dataset_name]
    
    if df.empty:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_name}' está vacío.")
    
    # Apply search filter if provided
    if search:
        search_lower = search.lower()
        mask = df.astype(str).apply(
            lambda row: row.str.lower().str.contains(search_lower, na=False).any(), 
            axis=1
        )
        df = df[mask]
    
    # Calculate pagination
    total_rows = len(df)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Get paginated data
    paginated_df = df.iloc[start_idx:end_idx]
    
    # Clean NaN values for JSON serialization
    import numpy as np
    paginated_df = paginated_df.replace([np.nan], [None])
    
    # File mapping for metadata
    file_mapping = {
        "accounts": {
            "filename": "cuentas_info.csv",
            "description": "Información de cuentas de TikTok y creadores"
        },
        "videos": {
            "filename": "combined_tiktok_data_cleaned_with_date.csv",
            "description": "Datos de videos de TikTok con fechas"
        },
        "subtitles": {
            "filename": "subtitulos_videos_v3.csv",
            "description": "Subtítulos y transcripciones de videos"
        },
        "words": {
            "filename": "data.csv",
            "description": "Análisis de palabras y sentimientos"
        }
    }
    
    return {
        "dataset_name": dataset_name,
        "filename": file_mapping.get(dataset_name, {}).get("filename", "unknown.csv"),
        "description": file_mapping.get(dataset_name, {}).get("description", "Dataset sin descripción"),
        "total_rows": total_rows,
        "page": page,
        "per_page": per_page,
        "total_pages": (total_rows + per_page - 1) // per_page,
        "columns": df.columns.tolist(),
        "data": paginated_df.to_dict(orient="records"),
        "search_applied": search is not None,
        "search_term": search
    }

@app.get("/datasets", summary="Listar Datasets Disponibles", description="Obtiene información sobre todos los datasets disponibles.")
async def list_datasets():
    """
    Endpoint para listar todos los datasets disponibles con información básica
    """
    if not app_state.get("data"):
        raise HTTPException(status_code=503, detail="Los datos no están disponibles.")
    
    file_mapping = {
        "accounts": {
            "filename": "cuentas_info.csv",
            "description": "Información de cuentas de TikTok y creadores",
            "contains": "Datos de perfiles, seguidores, perspectivas políticas"
        },
        "videos": {
            "filename": "combined_tiktok_data_cleaned_with_date.csv",
            "description": "Datos de videos de TikTok con fechas",
            "contains": "Información de videos, visualizaciones, fechas de publicación"
        },
        "subtitles": {
            "filename": "subtitulos_videos_v3.csv",
            "description": "Subtítulos y transcripciones de videos",
            "contains": "Texto hablado, transcripciones, contenido verbal"
        },
        "words": {
            "filename": "data.csv",
            "description": "Análisis de palabras y sentimientos",
            "contains": "Palabras, análisis de sentimientos, polaridad"
        }
    }
    
    datasets_info = []
    for dataset_name, df in app_state["data"].items():
        if not df.empty:
            info = {
                "dataset_name": dataset_name,
                "filename": file_mapping.get(dataset_name, {}).get("filename", "unknown.csv"),
                "description": file_mapping.get(dataset_name, {}).get("description", "Dataset sin descripción"),
                "contains": file_mapping.get(dataset_name, {}).get("contains", "Información no especificada"),
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist()
            }
            datasets_info.append(info)
    
    return {
        "datasets": datasets_info,
        "total_datasets": len(datasets_info)
    }

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
                creators_df['user_type'].str.lower().str.contains(search_lower, na=False)
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
                "themes": row['user_type'] if pd.notna(row['user_type']) else 'Sin temas',
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

@app.get("/word-suggestions", summary="Obtener Sugerencias de Palabras", description="Devuelve sugerencias de palabras basadas en el término de búsqueda, ordenadas por popularidad.")
async def get_word_suggestions(q: str = Query(..., description="Término de búsqueda para sugerencias")):
    """
    Obtiene sugerencias de palabras desde los datasets basadas en el término de búsqueda.
    Busca en usernames, palabras del léxico y subtítulos, ordenando por frecuencia/popularidad.
    """
    try:
        if len(q.strip()) < 2:
            return {"suggestions": []}
        
        search_term = q.lower().strip()
        word_info = {}  # word -> {"count": real_count, "priority": source_priority}
        
        # Search in words/lexicon (highest priority - these are curated words)
        if "words" in app_state["data"] and not app_state["data"]["words"].empty:
            words_df = app_state["data"]["words"]
            if "word" in words_df.columns:
                matching_words = words_df["word"].dropna().astype(str)
                matching_words = matching_words[matching_words.str.lower().str.contains(search_term, na=False, regex=False)]
                
                # Count frequency of each word in the lexicon - use ACTUAL counts from dataset
                word_counts = matching_words.value_counts()
                for word, count in word_counts.head(15).items():
                    word_info[word] = {
                        "count": count,  # Real count from dataset
                        "priority": 3,   # Highest priority for lexicon words
                        "source": "lexicon"
                    }
        
        # Search in subtitles content (good source of real usage)
        if "subtitles" in app_state["data"] and not app_state["data"]["subtitles"].empty:
            subtitles_df = app_state["data"]["subtitles"]
            if "text" in subtitles_df.columns:
                # Get all subtitle text and count word occurrences
                subtitle_texts = subtitles_df["text"].dropna().astype(str)
                word_freq = {}
                
                for text in subtitle_texts.head(500):  # Process more subtitles for better frequency data
                    words_in_text = text.lower().split()
                    for word in words_in_text:
                        clean_word = word.strip('.,!?";()[]{}:-')
                        if len(clean_word) >= 2 and search_term in clean_word.lower():
                            word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
                
                # Add top frequent words from subtitles
                for word, count in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]:
                    if len(word) <= 50:  # Reasonable length
                        if word in word_info:
                            # If word already exists from lexicon, add subtitle count
                            word_info[word]["count"] += count
                            word_info[word]["source"] = "lexicon+subtitles"
                        else:
                            # New word from subtitles
                            word_info[word] = {
                                "count": count,
                                "priority": 2,  # Medium priority for subtitle words
                                "source": "subtitles"
                            }
        
        # Search in accounts usernames (lower priority but still relevant)
        if "accounts" in app_state["data"] and not app_state["data"]["accounts"].empty:
            accounts_df = app_state["data"]["accounts"]
            if "username" in accounts_df.columns:
                matching_usernames = accounts_df["username"].dropna().astype(str)
                matching_usernames = matching_usernames[matching_usernames.str.lower().str.contains(search_term, na=False, regex=False)]
                
                for username in matching_usernames.head(10):
                    if username not in word_info:  # Don't override lexicon/subtitle words
                        word_info[username] = {
                            "count": 1,  # Usernames appear once
                            "priority": 1,  # Lower priority
                            "source": "username"
                        }
        
        # Search in video descriptions/titles if available
        if "videos" in app_state["data"] and not app_state["data"]["videos"].empty:
            videos_df = app_state["data"]["videos"]
            for col in ["desc", "title"]:
                if col in videos_df.columns:
                    texts = videos_df[col].dropna().astype(str)
                    word_freq = {}
                    
                    for text in texts.head(200):  # Limit for performance
                        words_in_text = text.lower().split()
                        for word in words_in_text:
                            clean_word = word.strip('.,!?";()[]{}:-')
                            if len(clean_word) >= 2 and search_term in clean_word.lower():
                                word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
                    
                    # Add words from video content
                    for word, count in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]:
                        if len(word) <= 50:
                            if word in word_info:
                                # Add to existing count
                                word_info[word]["count"] += count
                            else:
                                # New word from video content
                                word_info[word] = {
                                    "count": count,
                                    "priority": 1,  # Lower priority
                                    "source": f"video_{col}"
                                }
        
        # Clean and sort suggestions by popularity
        clean_suggestions = []
        for word, info in word_info.items():
            if word and len(word) >= 2 and len(word) <= 50:
                clean_suggestions.append({
                    "word": word,
                    "count": info["count"],
                    "priority": info["priority"],
                    "source": info["source"],
                    "display": f"{word} ({info['count']})"
                })
        
        # Sort by count first (highest to lowest), then by other factors
        clean_suggestions.sort(key=lambda x: (
            -x["count"],     # PRIMARY: Higher count first (most important)
            not x["word"].lower().startswith(search_term),  # SECONDARY: Exact matches first
            -x["priority"],  # TERTIARY: Higher priority for ties (lexicon > subtitles > usernames/videos)
            len(x["word"])   # QUATERNARY: Shorter words first for final ties
        ))
        
        # Prepare final response
        final_suggestions = []
        seen_words = set()
        
        for item in clean_suggestions[:20]:  # Limit to top 20
            word = item["word"]
            if word.lower() not in seen_words:  # Avoid duplicates (case-insensitive)
                seen_words.add(word.lower())
                final_suggestions.append({
                    "text": word,
                    "count": item["count"],  # Real count from dataset
                    "source": item["source"],
                    "display": f"{word} ({item['count']})"
                })
        
        return {
            "suggestions": [s["text"] for s in final_suggestions],  # For backward compatibility
            "suggestions_with_counts": final_suggestions,  # New enhanced format
            "query": q,
            "total_found": len(final_suggestions)
        }
    
    except Exception as e:
        logger.error(f"Error getting word suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al obtener sugerencias: {str(e)}")

# --- Run the application ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)