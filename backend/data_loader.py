import pandas as pd
import numpy as np
import os
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime
import re
from collections import Counter

logger = logging.getLogger(__name__)

DATA_DIR = "../data"
OUTPUT_DIR = "../data/output"
CLEAN_OUTPUT_DIR = "../data/output/clean"

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
        
        # Load ULTIMATE TEMPORAL dataset - combines all data sources with dates
        try:
            ultimate_path = os.path.join(CLEAN_OUTPUT_DIR, "ultimate_temporal_dataset.parquet")
            if os.path.exists(ultimate_path):
                data["videos"] = pd.read_parquet(ultimate_path)
            else:
                data["videos"] = pd.read_csv(os.path.join(CLEAN_OUTPUT_DIR, "ultimate_temporal_dataset.csv"))
                logger.info(f"Loaded ULTIMATE TEMPORAL dataset: {len(data['videos'])} rows with comprehensive temporal data")
        except Exception as e:
            logger.error(f"Error loading ultimate temporal dataset: {str(e)}")
            try:
                # Fallback to main core
                data["videos"] = pd.read_csv(os.path.join(CLEAN_OUTPUT_DIR, "main_tiktok_data_clean.csv"))
                logger.info("Loaded main core as fallback")
            except Exception as e2:
                logger.error(f"Error loading fallback data: {str(e2)}")
                data["videos"] = pd.DataFrame()
        
        # Load additional dates data for temporal analysis
        try:
            dates_path = os.path.join(CLEAN_OUTPUT_DIR, "combined_tiktok_data_with_dates_clean.parquet")
            if os.path.exists(dates_path):
                data["dates"] = pd.read_parquet(dates_path)
            else:
                data["dates"] = pd.read_csv(os.path.join(CLEAN_OUTPUT_DIR, "combined_tiktok_data_with_dates_clean.csv"))
                logger.info(f"Loaded DATES data: {len(data['dates'])} rows for temporal analysis")
        except Exception as e:
            logger.error(f"Error loading dates data: {str(e)}")
            try:
                data["dates"] = pd.read_csv(os.path.join(DATA_DIR, "combined_tiktok_data_cleaned_with_date.csv"))
                logger.info("Loaded dates data from original file")
            except Exception as e2:
                logger.error(f"Error loading fallback dates data: {str(e2)}")
                data["dates"] = pd.DataFrame()
        
        # Load subtitles data from clean version
        try:
            clean_subtitles_path = os.path.join(CLEAN_OUTPUT_DIR, "subtitles_clean.parquet")
            if os.path.exists(clean_subtitles_path):
                data["subtitles"] = pd.read_parquet(clean_subtitles_path)
            else:
                data["subtitles"] = pd.read_csv(os.path.join(CLEAN_OUTPUT_DIR, "subtitles_clean.csv"))
                logger.info(f"Loaded CLEAN SUBTITLES data: {len(data['subtitles'])} rows")
        except Exception as e:
            logger.error(f"Error loading clean subtitles data: {str(e)}")
            try:
                data["subtitles"] = pd.read_csv(os.path.join(DATA_DIR, "subtitulos_videos_v3.csv"), low_memory=False)
                logger.info("Loaded subtitles data from original file")
            except Exception as e2:
                logger.error(f"Error loading fallback subtitles data: {str(e2)}")
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
            "filename": "ultimate_temporal_dataset.csv",
            "description": "Dataset temporal completo con información de usuarios, perspectivas políticas y fechas",
            "contains": "Videos con fechas, tipos de usuario, perspectivas políticas, actividad temporal, engagement"
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
            elif dataset_name == "videos":
                # Enhanced temporal statistics for videos dataset
                if "views" in df.columns:
                    data_summary[dataset_name]["avg_views"] = float(df["views"].mean())
                    data_summary[dataset_name]["total_views"] = float(df["views"].sum())
                
                # Add temporal information
                if "date" in df.columns:
                    df_temp = df.copy()
                    df_temp["date"] = pd.to_datetime(df_temp["date"], errors='coerce')
                    data_summary[dataset_name]["date_range"] = {
                        "earliest": str(df_temp["date"].min()),
                        "latest": str(df_temp["date"].max()),
                        "total_with_dates": int(df_temp["date"].notna().sum())
                    }
                    
                    # Add yearly distribution
                    if df_temp["date"].notna().any():
                        yearly_counts = df_temp["date"].dt.year.value_counts().sort_index()
                        data_summary[dataset_name]["yearly_distribution"] = yearly_counts.to_dict()
                
                # Add user type and perspective information
                if "user_type" in df.columns:
                    user_type_counts = df["user_type"].value_counts()
                    data_summary[dataset_name]["user_type_counts"] = user_type_counts.to_dict()
                
                if "perspective" in df.columns:
                    perspective_counts = df["perspective"].value_counts()
                    data_summary[dataset_name]["perspective_counts"] = perspective_counts.to_dict()
                
                # Add activity metrics
                if "daily_post_count" in df.columns:
                    data_summary[dataset_name]["max_daily_posts"] = int(df["daily_post_count"].max())
                    top_days = df.nlargest(3, "daily_post_count")[["date", "daily_post_count"]].drop_duplicates()
                    data_summary[dataset_name]["top_activity_days"] = [
                        {"date": str(row["date"]), "posts": int(row["daily_post_count"])} 
                        for _, row in top_days.iterrows()
                    ]
                    
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

def analyze_word_usage_by_date(data: Dict[str, Any], word: str) -> Dict[str, Any]:
    """
    Analyze when a specific word and its derivatives were used most frequently
    """
    try:
        # Use the dates dataset primarily, fall back to videos if needed
        if "dates" in data and not data["dates"].empty:
            df = data["dates"].copy()
            logger.info(f"Using dates dataset for temporal analysis: {len(df)} rows")
        elif "videos" in data and not data["videos"].empty:
            df = data["videos"].copy()
            logger.info(f"Using videos dataset for temporal analysis: {len(df)} rows")
        else:
            return {"error": "No video or dates data available for date analysis"}
        
        # Ensure we have the necessary columns
        if "transcription" not in df.columns and "title" not in df.columns:
            return {"error": "No text content available for word analysis"}
        
        # Combine text fields for analysis
        df["combined_text"] = ""
        if "transcription" in df.columns:
            df["combined_text"] += df["transcription"].fillna("")
        if "title" in df.columns:
            df["combined_text"] += " " + df["title"].fillna("")
        
        # Clean and prepare the word for search
        word_clean = word.lower().strip()
        
        # Create derivative patterns for the word
        derivatives = generate_word_derivatives(word_clean)
        
        # Find videos containing the word or its derivatives
        pattern = "|".join([re.escape(deriv) for deriv in derivatives])
        mask = df["combined_text"].str.lower().str.contains(pattern, na=False, regex=True)
        
        matching_videos = df[mask].copy()
        
        if matching_videos.empty:
            return {
                "word": word,
                "derivatives_searched": derivatives,
                "total_matches": 0,
                "message": f"No se encontraron videos que contengan la palabra '{word}' o sus derivadas"
            }
        
        # Process dates - prioritize 'date' column from temporal dataset
        date_column = None
        if "date" in matching_videos.columns:
            date_column = "date"
        elif "upload_date" in matching_videos.columns:
            date_column = "upload_date"
        
        if date_column is None:
            return {
                "word": word,
                "derivatives_searched": derivatives,
                "total_matches": len(matching_videos),
                "message": "No hay información de fechas disponible en los datos"
            }
        
        # Clean and parse dates
        matching_videos[date_column] = pd.to_datetime(matching_videos[date_column], errors='coerce')
        matching_videos = matching_videos.dropna(subset=[date_column])
        
        if matching_videos.empty:
            return {
                "word": word,
                "derivatives_searched": derivatives,
                "total_matches": len(df[mask]),
                "message": "No hay fechas válidas en los videos que contienen la palabra"
            }
        
        # Analyze by different time periods
        matching_videos["year"] = matching_videos[date_column].dt.year
        matching_videos["month"] = matching_videos[date_column].dt.to_period('M')
        matching_videos["date_only"] = matching_videos[date_column].dt.date
        
        # Count occurrences by time period
        yearly_counts = matching_videos["year"].value_counts().sort_index()
        monthly_counts = matching_videos["month"].value_counts().sort_index()
        daily_counts = matching_videos["date_only"].value_counts().sort_index()
        
        # Get top dates
        top_years = yearly_counts.head(5).to_dict()
        top_months = monthly_counts.head(10).to_dict()
        top_days = daily_counts.head(10).to_dict()
        
        # Convert Period objects to strings for JSON serialization
        top_months_str = {str(k): v for k, v in top_months.items()}
        top_days_str = {str(k): v for k, v in top_days.items()}
        
        # Get sample videos from top dates
        top_day = daily_counts.index[0] if len(daily_counts) > 0 else None
        sample_videos = []
        
        if top_day:
            day_videos = matching_videos[matching_videos["date_only"] == top_day]
            for _, video in day_videos.head(3).iterrows():
                sample_videos.append({
                    "username": video.get("username", ""),
                    "date": str(video[date_column]),
                    "title": video.get("title", "")[:100] + "..." if len(str(video.get("title", ""))) > 100 else video.get("title", ""),
                    "views": video.get("views", 0)
                })
        
        return {
            "word": word,
            "derivatives_searched": derivatives,
            "total_matches": len(matching_videos),
            "date_range": {
                "earliest": str(matching_videos[date_column].min()),
                "latest": str(matching_videos[date_column].max())
            },
            "top_years": top_years,
            "top_months": top_months_str,
            "top_days": top_days_str,
            "most_active_day": str(top_day) if top_day else None,
            "most_active_day_count": int(daily_counts.iloc[0]) if len(daily_counts) > 0 else 0,
            "sample_videos": sample_videos
        }
        
    except Exception as e:
        logger.error(f"Error analyzing word usage by date: {str(e)}")
        return {"error": f"Error en el análisis: {str(e)}"}

def generate_word_derivatives(word: str) -> List[str]:
    """
    Generate common derivatives of a word for more comprehensive search
    """
    derivatives = [word]
    
    # Common Spanish word endings and variations
    if word.endswith("cia"):
        base = word[:-3]
        derivatives.extend([
            base + "cia",
            base + "cias", 
            base + "cio",
            base + "cios"
        ])
    elif word.endswith("ncia"):
        base = word[:-4]
        derivatives.extend([
            base + "ncia",
            base + "ncias",
            base + "ncio", 
            base + "ncios"
        ])
    elif word.endswith("o"):
        base = word[:-1]
        derivatives.extend([
            base + "o",
            base + "a", 
            base + "os",
            base + "as"
        ])
    elif word.endswith("a"):
        base = word[:-1]
        derivatives.extend([
            base + "a",
            base + "o",
            base + "as", 
            base + "os"
        ])
    
    # Add plurals
    if not word.endswith("s"):
        derivatives.append(word + "s")
    
    # Add common prefixes for negative/positive forms
    prefixes = ["anti", "no", "pro", "contra"]
    for prefix in prefixes:
        derivatives.append(prefix + word)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_derivatives = []
    for item in derivatives:
        if item not in seen:
            seen.add(item)
            unique_derivatives.append(item)
    
    return unique_derivatives