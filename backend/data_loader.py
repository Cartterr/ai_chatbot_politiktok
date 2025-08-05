import pandas as pd
import numpy as np
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

DATA_DIR = "../data"

def load_all_data() -> Dict[str, Any]:
    """
    Load all data files into memory
    """
    try:
        # Try to load parquet files first (faster), fall back to CSV if needed
        data = {}
        
        # Load accounts info
        try:
            accounts_path = os.path.join(DATA_DIR, "cuentas_info.parquet")
            if os.path.exists(accounts_path):
                data["accounts"] = pd.read_parquet(accounts_path)
            else:
                data["accounts"] = pd.read_csv(
                    os.path.join(DATA_DIR, "cuentas_info.csv"),
                    on_bad_lines='skip',  # Skip problematic rows
                    escapechar='\\',      # Handle escaped characters
                    quotechar='"'         # Specify quote character
                )
        except Exception as e:
            logger.error(f"Error loading accounts data: {str(e)}")
            data["accounts"] = pd.DataFrame()
        
        # Load TikTok videos data
        try:
            videos_path = os.path.join(DATA_DIR, "combined_tiktok_data_cleaned_with_date.parquet")
            if os.path.exists(videos_path):
                data["videos"] = pd.read_parquet(videos_path)
            else:
                data["videos"] = pd.read_csv(os.path.join(DATA_DIR, "combined_tiktok_data_cleaned_with_date.csv"))
        except Exception as e:
            logger.error(f"Error loading videos data: {str(e)}")
            data["videos"] = pd.DataFrame()
        
        # Load word sentiment data
        try:
            words_path = os.path.join(DATA_DIR, "data.parquet")
            if os.path.exists(words_path):
                data["words"] = pd.read_parquet(words_path)
            else:
                data["words"] = pd.read_csv(os.path.join(DATA_DIR, "data.csv"))
        except Exception as e:
            logger.error(f"Error loading word data: {str(e)}")
            data["words"] = pd.DataFrame()
        
        # Load subtitles data
        try:
            subtitles_path = os.path.join(DATA_DIR, "subtitulos_videos_v3.parquet")
            if os.path.exists(subtitles_path):
                data["subtitles"] = pd.read_parquet(subtitles_path)
            else:
                data["subtitles"] = pd.read_csv(os.path.join(DATA_DIR, "subtitulos_videos_v3.csv"))
        except Exception as e:
            logger.error(f"Error loading subtitles data: {str(e)}")
            data["subtitles"] = pd.DataFrame()
        
        # Process data after loading
        process_data(data)
        
        return data
    
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return {}

def process_data(data: Dict[str, Any]) -> None:
    """
    Perform initial data processing after loading
    """
    # Process accounts data
    if "accounts" in data and not data["accounts"].empty:
        # Clean followers column (convert K and M notation to numbers)
        if "followers" in data["accounts"].columns:
            data["accounts"]["followers_num"] = data["accounts"]["followers"].apply(
                lambda x: float(str(x).replace("M", "000000").replace("K", "000").replace(".", "")) 
                if isinstance(x, str) 
                else float(x or 0)
            )
    
    # Process videos data
    if "videos" in data and not data["videos"].empty:
        # Convert date to datetime
        if "date" in data["videos"].columns:
            data["videos"]["date"] = pd.to_datetime(data["videos"]["date"], errors="coerce")
        
        # Convert views to numeric
        if "views" in data["videos"].columns:
            data["videos"]["views"] = pd.to_numeric(data["videos"]["views"], errors="coerce")
    
    # Process word sentiment data
    if "words" in data and not data["words"].empty:
        # Ensure sentiment is numeric
        if "sentimiento" in data["words"].columns:
            data["words"]["sentimiento"] = pd.to_numeric(data["words"]["sentimiento"], errors="coerce")
    
    # Process subtitles data - no special processing needed for now
    pass

def get_data_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a summary of the loaded data
    """
    summary = {}
    
    for key, df in data.items():
        if not df.empty:
            summary[key] = {
                "rows": len(df),
                "columns": df.columns.tolist(),
                "sample": df.head(5).replace([pd.NA, np.nan], [None, None]).to_dict(orient="records")
            }
            
            # Add specific statistics for each dataframe
            if key == "accounts":
                if "perspective" in df.columns:
                    perspective_counts = df["perspective"].value_counts().to_dict()
                    summary[key]["perspective_counts"] = perspective_counts
                
                if "followers_num" in df.columns:
                    summary[key]["avg_followers"] = float(df["followers_num"].mean())
                    summary[key]["max_followers"] = float(df["followers_num"].max())
            
            elif key == "videos":
                if "views" in df.columns:
                    summary[key]["avg_views"] = float(df["views"].mean())
                    summary[key]["total_views"] = float(df["views"].sum())
                    summary[key]["max_views"] = float(df["views"].max())
                
                if "date" in df.columns:
                    summary[key]["date_range"] = [
                        df["date"].min().isoformat() if not pd.isna(df["date"].min()) else None,
                        df["date"].max().isoformat() if not pd.isna(df["date"].max()) else None
                    ]
            
            elif key == "words":
                if "sentimiento" in df.columns:
                    sentiment_counts = df["sentimiento"].value_counts().to_dict()
                    summary[key]["sentiment_counts"] = {str(k): v for k, v in sentiment_counts.items()}
    
    return summary

def filter_data_by_query(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Filter data based on a simple text query
    """
    filtered_data = {}
    query = query.lower()
    
    # Filter accounts
    if "accounts" in data and not data["accounts"].empty:
        filtered_accounts = data["accounts"][
            data["accounts"].apply(
                lambda row: any(query in str(val).lower() for val in row), 
                axis=1
            )
        ]
        if not filtered_accounts.empty:
            filtered_data["accounts"] = filtered_accounts
    
    # Filter videos
    if "videos" in data and not data["videos"].empty:
        filtered_videos = data["videos"][
            data["videos"].apply(
                lambda row: any(query in str(val).lower() for val in row), 
                axis=1
            )
        ]
        if not filtered_videos.empty:
            filtered_data["videos"] = filtered_videos
    
    # Filter subtitles
    if "subtitles" in data and not data["subtitles"].empty:
        filtered_subtitles = data["subtitles"][
            data["subtitles"].apply(
                lambda row: any(query in str(val).lower() for val in row), 
                axis=1
            )
        ]
        if not filtered_subtitles.empty:
            filtered_data["subtitles"] = filtered_subtitles
    
    # Filter words
    if "words" in data and not data["words"].empty:
        filtered_words = data["words"][
            data["words"].apply(
                lambda row: any(query in str(val).lower() for val in row), 
                axis=1
            )
        ]
        if not filtered_words.empty:
            filtered_data["words"] = filtered_words
    
    return filtered_data

def determine_relevant_datasets(query: str, data: Dict[str, Any]) -> Dict[str, float]:
    """
    Determine which datasets are relevant for a given query.
    Returns a dict with dataset names as keys and relevance scores as values.
    """
    query_lower = query.lower()
    relevance_scores = {}
    
    # Keywords that indicate which datasets might be relevant
    dataset_keywords = {
        "accounts": [
            "cuenta", "creador", "usuario", "perfil", "seguidor", "influencer", 
            "perspectiva", "ideología", "política", "orientación", "biografía",
            "followers", "creator", "account", "profile", "perspective", "ideology"
        ],
        "videos": [
            "video", "contenido", "publicación", "post", "views", "visualización",
            "fecha", "tiempo", "temporal", "evolución", "tendencia", "viral",
            "content", "publication", "date", "time", "trend", "evolution"
        ],
        "subtitles": [
            "subtítulo", "transcripción", "texto", "habla", "dice", "menciona",
            "palabra", "frase", "discurso", "conversación", "diálogo",
            "subtitle", "transcription", "text", "speech", "word", "phrase", "dialogue"
        ],
        "words": [
            "palabra", "término", "sentimiento", "emoción", "análisis", "semántico",
            "significado", "connotación", "polaridad", "positivo", "negativo",
            "word", "term", "sentiment", "emotion", "meaning", "positive", "negative"
        ]
    }
    
    # Calculate relevance scores
    for dataset_name, keywords in dataset_keywords.items():
        if dataset_name in data and not data[dataset_name].empty:
            score = 0
            for keyword in keywords:
                if keyword in query_lower:
                    score += 1
            
            # Normalize score (0-1 range)
            relevance_scores[dataset_name] = min(score / len(keywords), 1.0)
    
    # If no specific keywords found, include all datasets with lower relevance
    if not any(score > 0 for score in relevance_scores.values()):
        for dataset_name in data.keys():
            if not data[dataset_name].empty:
                relevance_scores[dataset_name] = 0.3  # Default relevance
    
    # Filter out datasets with zero relevance
    return {k: v for k, v in relevance_scores.items() if v > 0}

def get_relevant_data_summary(data: Dict[str, Any], relevant_datasets: Dict[str, float], query: str) -> Dict[str, Any]:
    """
    Generate a summary focused on the relevant datasets for a query.
    """
    # File mapping for display names
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
    
    # Generate summary for relevant datasets only
    data_summary = {}
    sources = []
    
    for dataset_name, relevance_score in sorted(relevant_datasets.items(), key=lambda x: x[1], reverse=True):
        if dataset_name in data and not data[dataset_name].empty:
            df = data[dataset_name]
            
            # Add to data summary
            data_summary[dataset_name] = {
                "rows": len(df),
                "columns": df.columns.tolist(),
                "relevance_score": relevance_score,
                "sample": df.head(3).replace([pd.NA, np.nan], [None, None]).to_dict(orient="records")  # Smaller sample for relevant data
            }
            
            # Add specific statistics
            if dataset_name == "accounts" and "perspective" in df.columns:
                data_summary[dataset_name]["perspective_counts"] = df["perspective"].value_counts().to_dict()
            elif dataset_name == "videos" and "views" in df.columns:
                data_summary[dataset_name]["avg_views"] = float(df["views"].mean())
                data_summary[dataset_name]["total_views"] = float(df["views"].sum())
            elif dataset_name == "words" and "sentimiento" in df.columns:
                sentiment_counts = df["sentimiento"].value_counts().to_dict()
                data_summary[dataset_name]["sentiment_counts"] = {str(k): v for k, v in sentiment_counts.items()}
            
            # Add to sources list
            if dataset_name in file_mapping:
                sources.append({
                    "dataset": dataset_name,
                    "filename": file_mapping[dataset_name]["filename"],
                    "description": file_mapping[dataset_name]["description"],
                    "contains": file_mapping[dataset_name]["contains"],
                    "relevance_score": relevance_score,
                    "rows": len(df),
                    "columns": len(df.columns)
                })
    
    # Generate query analysis
    query_analysis = f"Consulta: '{query}' - Se identificaron {len(sources)} fuentes de datos relevantes"
    
    return {
        "data_summary": data_summary,
        "sources": sources,
        "query_analysis": query_analysis
    }