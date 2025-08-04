import pandas as pd
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
                "sample": df.head(5).to_dict(orient="records")
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