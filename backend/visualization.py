# backend/visualization.py

import pandas as pd
import numpy as np
import json
import re
from typing import Dict, Any, List, Optional
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# --- Global Data Filtering Functions ---
def filter_data_by_query(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Filter all datasets based on the search query.
    Returns filtered datasets that contain the query term.
    """
    if not query or not query.strip():
        return data  # Return original data if no query
    
    # Skip filtering for generic analysis queries
    generic_queries = ['análisis de datos', 'analysis', 'resumen', 'summary', 'datos', 'data']
    query_lower = query.lower().strip()
    
    # If it's a generic query, return original data
    for generic in generic_queries:
        if query_lower.startswith(generic) or query_lower == generic:
            return data
    
    filtered_data = {}
    
    # Filter accounts
    if "accounts" in data and not data["accounts"].empty:
        accounts_df = data["accounts"].copy()
        mask = pd.Series(False, index=accounts_df.index)
        
        # Search in username (more flexible matching)
        if "username" in accounts_df.columns:
            mask |= accounts_df["username"].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
        
        # Search in perspective
        if "perspective" in accounts_df.columns:
            mask |= accounts_df["perspective"].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
        
        # Search in themes if available
        if "themes" in accounts_df.columns:
            mask |= accounts_df["themes"].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
        
        filtered_data["accounts"] = accounts_df[mask]
    
    # Filter videos
    if "videos" in data and not data["videos"].empty:
        videos_df = data["videos"].copy()
        mask = pd.Series(False, index=videos_df.index)
        
        # Search in username
        if "username" in videos_df.columns:
            mask |= videos_df["username"].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
        
        # Search in description
        if "desc" in videos_df.columns:
            mask |= videos_df["desc"].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
        
        # Search in URL
        if "url" in videos_df.columns:
            mask |= videos_df["url"].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
        
        # NEW: Also search in video titles if available
        if "title" in videos_df.columns:
            mask |= videos_df["title"].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
        
        filtered_data["videos"] = videos_df[mask]
    
    # Filter words
    if "words" in data and not data["words"].empty:
        words_df = data["words"].copy()
        mask = pd.Series(False, index=words_df.index)
        
        # Search in word text
        if "word" in words_df.columns:
            mask |= words_df["word"].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
        
        # Search in type_1
        if "type_1" in words_df.columns:
            mask |= words_df["type_1"].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
        
        filtered_data["words"] = words_df[mask]
    
    # Filter subtitles
    if "subtitles" in data and not data["subtitles"].empty:
        subtitles_df = data["subtitles"].copy()
        mask = pd.Series(False, index=subtitles_df.index)
        
        # Search in text content
        if "text" in subtitles_df.columns:
            mask |= subtitles_df["text"].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
        
        # Search in username
        if "username" in subtitles_df.columns:
            mask |= subtitles_df["username"].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
        
        filtered_data["subtitles"] = subtitles_df[mask]
    
    # Enhanced cross-dataset filtering
    try:
        # SPECIAL CASE: If we have filtered words but no videos, find videos with subtitles containing those words
        if ("words" in filtered_data and not filtered_data["words"].empty and 
            ("videos" not in filtered_data or filtered_data["videos"].empty)):
            
            logger.info(f"Word search detected - looking for videos with subtitles containing: '{query_lower}'")
            
            # Find subtitles containing the query term (if not already filtered)
            if "subtitles" in data and not data["subtitles"].empty:
                subtitles_df = data["subtitles"].copy()
                if "text" in subtitles_df.columns:
                    subtitle_mask = subtitles_df["text"].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
                    matching_subtitles = subtitles_df[subtitle_mask]
                    
                    if not matching_subtitles.empty and "url" in matching_subtitles.columns:
                        # Get URLs from matching subtitles
                        subtitle_urls = set(matching_subtitles["url"].dropna().astype(str).tolist())
                        
                        # Find videos with these URLs
                        if "videos" in data and not data["videos"].empty and subtitle_urls:
                            videos_df = data["videos"].copy()
                            if "url" in videos_df.columns:
                                url_mask = videos_df["url"].astype(str).isin(subtitle_urls)
                                word_related_videos = videos_df[url_mask]
                                
                                if not word_related_videos.empty:
                                    filtered_data["videos"] = word_related_videos
                                    # Also update subtitles to the matching ones
                                    filtered_data["subtitles"] = matching_subtitles
                                    logger.info(f"Found {len(word_related_videos)} videos with subtitles containing '{query_lower}'")
        
        # If we have filtered accounts, also filter related data
        if "accounts" in filtered_data and not filtered_data["accounts"].empty:
            filtered_usernames = set(filtered_data["accounts"]["username"].dropna().astype(str).tolist())
            
            # Filter videos by these usernames
            if "videos" in data and not data["videos"].empty and filtered_usernames:
                videos_df = data["videos"].copy()
                if "username" in videos_df.columns:
                    username_mask = videos_df["username"].astype(str).isin(filtered_usernames)
                    related_videos = videos_df[username_mask]
                    
                    if "videos" in filtered_data and not filtered_data["videos"].empty:
                        # Combine with existing filter
                        try:
                            combined_videos = pd.concat([filtered_data["videos"], related_videos], ignore_index=True, sort=False).drop_duplicates()
                            filtered_data["videos"] = combined_videos
                        except Exception as concat_err:
                            logger.warning(f"Error combining videos data: {concat_err}, using related videos only")
                            filtered_data["videos"] = related_videos
                    elif not related_videos.empty:
                        filtered_data["videos"] = related_videos
        
        # NEW: If we have filtered subtitles, include related videos
        if "subtitles" in filtered_data and not filtered_data["subtitles"].empty:
            # Get URLs from filtered subtitles
            if "url" in filtered_data["subtitles"].columns:
                subtitle_urls = set(filtered_data["subtitles"]["url"].dropna().astype(str).tolist())
                
                # Find videos with matching URLs
                if "videos" in data and not data["videos"].empty and subtitle_urls:
                    videos_df = data["videos"].copy()
                    if "url" in videos_df.columns:
                        url_mask = videos_df["url"].astype(str).isin(subtitle_urls)
                        subtitle_related_videos = videos_df[url_mask]
                        
                        if "videos" in filtered_data and not filtered_data["videos"].empty:
                            # Combine with existing videos
                            try:
                                combined_videos = pd.concat([filtered_data["videos"], subtitle_related_videos], ignore_index=True, sort=False).drop_duplicates()
                                filtered_data["videos"] = combined_videos
                            except Exception as concat_err:
                                logger.warning(f"Error combining subtitle-related videos: {concat_err}")
                        elif not subtitle_related_videos.empty:
                            filtered_data["videos"] = subtitle_related_videos
            
        # If we have filtered accounts, also filter subtitles by usernames
        if "accounts" in filtered_data and not filtered_data["accounts"].empty:
            filtered_usernames = set(filtered_data["accounts"]["username"].dropna().astype(str).tolist())
            
            # Filter subtitles by these usernames
            if "subtitles" in data and not data["subtitles"].empty and filtered_usernames:
                subtitles_df = data["subtitles"].copy()
                if "username" in subtitles_df.columns:
                    username_mask = subtitles_df["username"].astype(str).isin(filtered_usernames)
                    related_subtitles = subtitles_df[username_mask]
                    
                    if "subtitles" in filtered_data and not filtered_data["subtitles"].empty:
                        # Combine with existing filter
                        try:
                            combined_subtitles = pd.concat([filtered_data["subtitles"], related_subtitles], ignore_index=True, sort=False).drop_duplicates()
                            filtered_data["subtitles"] = combined_subtitles
                        except Exception as concat_err:
                            logger.warning(f"Error combining subtitles data: {concat_err}, using related subtitles only")
                            filtered_data["subtitles"] = related_subtitles
                    elif not related_subtitles.empty:
                        filtered_data["subtitles"] = related_subtitles
    except Exception as e:
        logger.warning(f"Error in cross-dataset filtering: {e}")
    
    # Ensure we return something for each dataset, even if empty
    for key in ["accounts", "videos", "words", "subtitles"]:
        if key not in filtered_data and key in data:
            filtered_data[key] = pd.DataFrame()  # Empty dataframe
    
    # Check if filtering resulted in completely empty data
    total_filtered_records = sum(len(v) if hasattr(v, '__len__') and v is not None else 0 for v in filtered_data.values() if v is not None)
    
    # Log filtering results for debugging
    filter_summary = {}
    for key in ["accounts", "videos", "words", "subtitles"]:
        original_count = len(data.get(key, [])) if key in data and hasattr(data[key], '__len__') else 0
        filtered_count = len(filtered_data.get(key, [])) if key in filtered_data and hasattr(filtered_data[key], '__len__') else 0
        filter_summary[key] = f"{original_count} -> {filtered_count}"
    
    logger.info(f"Query '{query}' filtering results: {filter_summary}")
    
    # If no data found, return original data to avoid empty visualizations
    if total_filtered_records == 0:
        logger.warning(f"No data found for query '{query}', returning original data")
        return data
    
    return filtered_data

# --- Helper Functions ---
def safe_float(value, default=0.0):
    """Safely convert value to float, returning default on failure."""
    try:
        # Handle potential strings like '1,234.5' if needed, though pandas usually handles this
        if isinstance(value, str):
             value = value.replace(',', '') # Basic comma removal if present
        return float(value) if pd.notna(value) else default
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Safely convert value to int, returning default on failure."""
    try:
        # Handle potential float inputs before converting to int
        if pd.notna(value):
             return int(float(value)) # Convert to float first handles '10.0' etc.
        else:
            return default
    except (ValueError, TypeError):
        return default

# --- Main Generation Function ---
def generate_visualization(data: Dict[str, Any], query: str, viz_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Genera visualizaciones basadas en la consulta y el tipo solicitado.
    Filtra los datos según la consulta antes de generar la visualización.
    Devuelve datos en formato JSON adecuados para el frontend.
    """
    # Apply global filtering based on query
    try:
        filtered_data = filter_data_by_query(data, query)
        
        # Log filtering results
        if query and query.strip():
            original_counts = {k: len(v) if hasattr(v, '__len__') else 0 for k, v in data.items()}
            filtered_counts = {k: len(v) if hasattr(v, '__len__') else 0 for k, v in filtered_data.items()}
            logger.info(f"Query '{query}' filtered data: {original_counts} -> {filtered_counts}")
            
            # CHECK: If the query is specific but found no meaningful data, don't show visualization
            total_original = sum(original_counts.values())
            total_filtered = sum(filtered_counts.values())
            
            # If we filtered to the same amount as original, it means no real filtering happened
            # This suggests the query term doesn't exist in the data
            if total_filtered == total_original and query.strip() and len(query.strip()) > 3:
                # Check if the query is a specific word (not a generic query)
                query_lower = query.lower().strip()
                generic_terms = ['datos', 'información', 'análisis', 'resumen', 'gráfico', 'visualización']
                
                if not any(generic in query_lower for generic in generic_terms):
                    logger.warning(f"Specific query '{query}' found no filtered data (same as original). Not showing visualization.")
                    return {
                        "type": "no_data",
                        "title": "Sin Datos Disponibles",
                        "message": f"No se encontraron datos relevantes para '{query}' en el conjunto de datos disponible.",
                        "suggestion": "Intenta con una palabra diferente o consulta términos más generales.",
                        "filter_info": {"filtered": False}
                    }
            
    except Exception as e:
        logger.error(f"Error in data filtering for query '{query}': {e}")
        # Fallback to original data if filtering fails
        filtered_data = data
    
    if viz_type is None:
        if re.search(r'(tiempo|temporal|evoluci[oó]n|tendencia)', query, re.IGNORECASE): viz_type = 'time_series'
        elif re.search(r'(comparar|versus|vs|diferencia)', query, re.IGNORECASE): viz_type = 'comparison'
        elif re.search(r'(distribuci[oó]n|histograma)', query, re.IGNORECASE): viz_type = 'distribution'
        elif re.search(r'(red|conexi[oó]n|relaci[oó]n)', query, re.IGNORECASE): viz_type = 'network'
        elif re.search(r'(sentimiento|emoci[oó]n)', query, re.IGNORECASE): viz_type = 'sentiment'
        else: viz_type = 'summary'
    logger.info(f"Generando visualización tipo '{viz_type}' para consulta: '{query}'")

    generators = {
        'time_series': generate_time_series,
        'comparison': generate_comparison,
        'distribution': generate_distribution,
        'network': generate_network, # Consider if you have a network component later
        'sentiment': generate_sentiment_analysis,
        'summary': generate_summary_visualization,
        'focused_chart': generate_focused_chart  # New individual chart generator
    }
    generator_func = generators.get(viz_type, generate_summary_visualization)

    try:
        visualization_data = generator_func(filtered_data, query)
        if "type" not in visualization_data: visualization_data["type"] = viz_type
        
        # Add filtering information to the result
        try:
            if query and query.strip():
                original_total = sum(len(v) if hasattr(v, '__len__') and v is not None else 0 for v in data.values() if v is not None)
                filtered_total = sum(len(v) if hasattr(v, '__len__') and v is not None else 0 for v in filtered_data.values() if v is not None)
                visualization_data["filter_info"] = {
                    "query": query,
                    "original_records": original_total,
                    "filtered_records": filtered_total,
                    "filtered": True
                }
                
                # Update title to reflect filtering
                base_title = visualization_data.get("title", f"Visualización ({viz_type})")
                if not base_title.startswith("Error"):
                    visualization_data["title"] = f"{base_title} - Filtrado: '{query}'"
            else:
                visualization_data["filter_info"] = {"filtered": False}
        except Exception as e:
            logger.warning(f"Error adding filter info: {e}")
            visualization_data["filter_info"] = {"filtered": False}
        
        # Ensure a meaningful title, even for errors originating within the generator
        if "title" not in visualization_data or not visualization_data["title"]:
             visualization_data["title"] = f"Visualización ({viz_type})"
        # If the generator internally set an error, ensure the title reflects it
        if visualization_data.get("error"):
             visualization_data["title"] = f"Error al Generar Visualización ({viz_type})"

        return visualization_data
    except Exception as e:
         logger.error(f"Excepción no controlada al generar visualización tipo '{viz_type}': {e}", exc_info=True)
         return { "type": viz_type, "title": f"Error al Generar Visualización ({viz_type})", "error": f"Error interno del servidor: {str(e)}" }

# --- Specific Visualization Generators ---

def generate_time_series(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    result = { "type": "time_series", "title": "Evolución Temporal de Videos", "data": [], "views_data": [], "stats": {} }
    try:
        # Debug logging
        logger.debug(f"Time series generation for query: '{query}'")
        logger.debug(f"Data keys: {list(data.keys())}")
        
        if 'videos' in data:
            videos_data = data['videos']
            logger.debug(f"Videos data type: {type(videos_data)}, empty: {videos_data.empty if hasattr(videos_data, 'empty') else 'N/A'}")
            if hasattr(videos_data, 'columns'):
                logger.debug(f"Videos columns: {list(videos_data.columns)}")
        
        if 'videos' in data and not data['videos'].empty:
            df = data['videos'].copy()
            
            # Check if date column exists and has valid data
            if 'date' not in df.columns:
                logger.warning(f"No date column in videos data. Available columns: {list(df.columns)}")
                result["error"] = "No hay columna de fecha en los datos de videos."
                return result
            
            # Debug date column before conversion
            logger.debug(f"Date column sample before conversion: {df['date'].head().tolist()}")
            logger.debug(f"Date column data types: {df['date'].dtype}")
                
            # Convert dates and filter out invalid ones
            try:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                logger.debug(f"Date column sample after conversion: {df['date'].head().tolist()}")
            except Exception as date_err:
                logger.error(f"Error converting dates: {date_err}")
                result["error"] = f"Error procesando fechas: {str(date_err)}"
                return result
                
            df = df.dropna(subset=['date'])
            
            if df.empty:
                logger.warning(f"No valid dates found after filtering for query: '{query}'")
                result["error"] = "No se encontraron fechas válidas en los videos."
                return result
            
            # Apply username filtering if specified
            username_pattern = re.compile(r'@(\w+)', re.IGNORECASE)
            usernames = username_pattern.findall(query)
            if usernames and 'username' in df.columns:
                df = df[df['username'].isin(usernames)]
                if df.empty:
                    result["error"] = f"No se encontraron videos para los usuarios: {', '.join(usernames)}"
                    return result

            # Generate time series data
            df['year_month'] = df['date'].dt.strftime('%Y-%m')
            monthly_counts = df.groupby('year_month').size().reset_index(name='count').sort_values('year_month')
            
            if monthly_counts.empty:
                result["error"] = "No se pudieron generar datos temporales."
                return result
                
            result["data"] = [{"date": row['year_month'], "count": safe_int(row['count'])} for _, row in monthly_counts.iterrows()]

            # Generate stats
            result["stats"] = { 
                "Total Videos": safe_int(monthly_counts['count'].sum()), 
                "Promedio Mensual": safe_float(monthly_counts['count'].mean()), 
                "Mes Pico": monthly_counts.loc[monthly_counts['count'].idxmax(), 'year_month'], 
                "Máximo Mensual": safe_int(monthly_counts['count'].max()) 
            }

            # Add views data if available
            if 'views' in df.columns:
                try:
                    df['views'] = pd.to_numeric(df['views'], errors='coerce')
                    df_views = df.dropna(subset=['views'])
                    if not df_views.empty:
                        views_by_month = df_views.groupby('year_month')['views'].mean().reset_index()
                        result["views_data"] = [{"date": row['year_month'], "avg_views": safe_float(row['views'])} for _, row in views_by_month.iterrows()]
                except Exception as views_err:
                    logger.warning(f"Error processing views data: {views_err}")
                    
        else: 
            result["error"] = "No hay datos de videos disponibles."
    except Exception as e: 
        logger.error(f"Error en generate_time_series: {e}", exc_info=True)
        result["error"] = f"Error interno: {e}"
    return result

def generate_comparison(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    result = { "type": "comparison", "title": "Comparativas", "follower_comparison": [], "perspective_comparison": [], "theme_comparison": [], "views_comparison": [] }
    try:
        # Check if we have any data at all
        accounts_df_orig = data.get('accounts')
        videos_df_orig = data.get('videos')
        
        if ((accounts_df_orig is None or accounts_df_orig.empty) and 
            (videos_df_orig is None or videos_df_orig.empty)):
            result["error"] = "No hay datos de cuentas o videos disponibles para comparar."
            return result
        
        username_pattern = re.compile(r'@(\w+)', re.IGNORECASE)
        usernames = username_pattern.findall(query)

        if accounts_df_orig is not None and not accounts_df_orig.empty:
            accounts_df = accounts_df_orig.copy()
            if usernames:
                filtered_acc = accounts_df[accounts_df['username'].isin(usernames)]
                if not filtered_acc.empty: accounts_df = filtered_acc

            if 'followers_num' in accounts_df.columns:
                comp_df = accounts_df.nlargest(10, 'followers_num')
                result["follower_comparison"] = [{"name": row['username'], "value": safe_float(row['followers_num'])} for _, row in comp_df.iterrows()] # Use name/value
            if 'perspective' in accounts_df.columns:
                counts = accounts_df.dropna(subset=['perspective'])['perspective'].value_counts().reset_index()
                counts.columns = ['name', 'value'] # Use name/value
                result["perspective_comparison"] = counts.to_dict('records')
            if 'themes' in accounts_df.columns:
                themes = [t.strip() for themes_str in accounts_df['themes'].dropna() for t in str(themes_str).split(',') if t.strip()]
                counts = Counter(themes).most_common(10)
                result["theme_comparison"] = [{"name": name, "value": value} for name, value in counts] # Use name/value

        if videos_df_orig is not None and not videos_df_orig.empty and 'views' in videos_df_orig.columns:
             videos_df = videos_df_orig.copy()
             if usernames:
                 filtered_vid = videos_df[videos_df['username'].isin(usernames)]
                 if not filtered_vid.empty: videos_df = filtered_vid

             if 'username' in videos_df.columns and pd.api.types.is_numeric_dtype(videos_df['views']):
                 df_cleaned = videos_df.dropna(subset=['username', 'views'])
                 if not df_cleaned.empty:
                     avg_views = df_cleaned.groupby('username')['views'].agg(['mean', 'count', 'sum']).reset_index().sort_values('mean', ascending=False).head(10)
                     # Use name/value structure where appropriate for consistency? Or keep specific keys? Let's keep specific for this one.
                     result["views_comparison"] = [{
                         "username": row['username'], "avg_views": safe_float(row['mean']),
                         "total_videos": safe_int(row['count']), "total_views": safe_float(row['sum'])
                     } for _, row in avg_views.iterrows()]

        if not any(result.get(key) for key in result if isinstance(result.get(key), list)):
             result["error"] = "No se generaron comparaciones con los datos/consulta proporcionados."
    except Exception as e: logger.error(f"Error en generate_comparison: {e}", exc_info=True); result["error"] = f"Error interno: {e}"
    return result

def generate_distribution(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    result = { "type": "distribution", "title": "Distribuciones", "perspective_distribution": [], "age_distribution": [], "theme_distribution": [], "views_distribution": [], "sentiment_distribution": [] }
    try:
        if 'accounts' in data and not data['accounts'].empty:
            accounts_df = data['accounts']
            if 'perspective' in accounts_df.columns:
                counts = accounts_df.dropna(subset=['perspective'])['perspective'].value_counts().reset_index()
                counts.columns = ['name', 'value'] # Use name/value
                result["perspective_distribution"] = counts.to_dict('records')
            if 'age' in accounts_df.columns:
                counts = accounts_df.dropna(subset=['age'])['age'].value_counts().reset_index()
                counts.columns = ['name', 'value'] # Use name/value
                result["age_distribution"] = counts.to_dict('records')
            if 'themes' in accounts_df.columns:
                themes = [t.strip() for themes_str in accounts_df['themes'].dropna() for t in str(themes_str).split(',') if t.strip()]
                counts = Counter(themes).most_common(15)
                result["theme_distribution"] = [{"name": name, "value": value} for name, value in counts] # Use name/value

        if 'videos' in data and not data['videos'].empty and 'views' in data['videos'].columns:
            videos_df = data['videos'].copy(); videos_df['views'] = pd.to_numeric(videos_df['views'], errors='coerce').dropna()
            if not videos_df.empty:
                bins = [0, 1000, 10000, 100000, 1000000, float('inf')]
                labels = ['<1K', '1K-10K', '10K-100K', '100K-1M', '>1M']
                videos_df['view_bin'] = pd.cut(videos_df['views'], bins=bins, labels=labels, right=False, include_lowest=True)
                counts = videos_df['view_bin'].value_counts().reset_index(); counts.columns = ['name', 'value'] # Use name/value
                counts['name'] = pd.Categorical(counts['name'], categories=labels, ordered=True); counts = counts.sort_values('name')
                result["views_distribution"] = counts.to_dict('records')

        if 'words' in data and not data['words'].empty and 'sentimiento' in data['words'].columns:
            words_df = data['words'].copy(); words_df['sentimiento'] = pd.to_numeric(words_df['sentimiento'], errors='coerce').dropna()
            if not words_df.empty:
                counts = words_df['sentimiento'].value_counts().reset_index(); counts.columns = ['sentiment', 'value'] # Keep sentiment for mapping
                sentiment_map = {-1.0: "Negativo", 0.0: "Neutral", 1.0: "Positivo"}
                counts['name'] = counts['sentiment'].map(lambda x: sentiment_map.get(x, f"Otro ({x})")) # Map to name
                result["sentiment_distribution"] = counts[['name', 'value']].to_dict('records') # Select name/value

        if not any(result.get(key) for key in result if isinstance(result.get(key), list)):
            result["error"] = "No se generaron distribuciones con los datos disponibles."
    except Exception as e: logger.error(f"Error en generate_distribution: {e}", exc_info=True); result["error"] = f"Error interno: {e}"
    return result

# --- generate_network --- (Keep previous version or implement using a graph library if needed)
def generate_network(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    """Generate a simple network visualization based on user connections"""
    result = { "type": "network", "title": "Red de Usuarios y Conexiones", "nodes": [], "links": [] }
    
    try:
        if "accounts" in data and not data["accounts"].empty:
            accounts_df = data["accounts"]
            
            # Create nodes from accounts
            nodes = []
            for _, row in accounts_df.head(20).iterrows():  # Limit to 20 for performance
                nodes.append({
                    "id": row["username"],
                    "label": row["username"],
                    "group": row.get("perspective", "Sin clasificar"),
                    "size": int(row.get("followers_num", 1000)) // 10000,  # Scale down followers for node size
                    "color": get_color_for_perspective(row.get("perspective", "Sin clasificar"))
                })
            
            # Create simple links based on shared perspectives
            links = []
            perspectives = accounts_df["perspective"].value_counts()
            for perspective in perspectives.index[:5]:  # Top 5 perspectives
                users_in_perspective = accounts_df[accounts_df["perspective"] == perspective]["username"].tolist()[:5]
                # Connect users within the same perspective
                for i, user1 in enumerate(users_in_perspective):
                    for user2 in users_in_perspective[i+1:]:
                        links.append({
                            "source": user1,
                            "target": user2,
                            "strength": 1,
                            "label": f"Misma perspectiva: {perspective}"
                        })
            
            result["nodes"] = nodes
            result["links"] = links
            result["summary"] = f"Red de {len(nodes)} usuarios con {len(links)} conexiones basadas en perspectivas políticas"
            
        else:
            result["error"] = "No hay datos de cuentas disponibles para generar la red"
            
    except Exception as e:
        logger.error(f"Error generando visualización de red: {e}")
        result["error"] = f"Error al generar la red: {str(e)}"
    
    return result

def get_color_for_perspective(perspective):
    """Get color for political perspective"""
    colors = {
        "Izquierda": "#ef4444",
        "Derecha": "#3b82f6", 
        "Central": "#10b981",
        "Periodista": "#f59e0b",
        "Sin clasificar": "#6b7280"
    }
    return colors.get(perspective, "#6b7280")


def generate_sentiment_analysis(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    result = { "type": "sentiment", "title": "Análisis de Sentimiento", "data": [], "by_user": [] }
    try:
        # Check if we have the required data
        if ('subtitles' not in data or data['subtitles'].empty or
            'words' not in data or data['words'].empty):
            result["error"] = "Datos insuficientes: se requieren subtítulos y léxico para análisis de sentimiento."
            return result
            
        if 'sentimiento' not in data['words'].columns:
            result["error"] = "No hay datos de sentimiento en el léxico."
            return result
        
        username_pattern = re.compile(r'@(\w+)', re.IGNORECASE)
        usernames = username_pattern.findall(query)
        
        # Process the data
        subtitles_df = data['subtitles'].copy().dropna(subset=['username', 'subtitles'])
        words_df = data['words'].copy().dropna(subset=['word', 'sentimiento'])
        
        if subtitles_df.empty:
            result["error"] = "No hay subtítulos válidos para analizar."
            return result
            
        if words_df.empty:
            result["error"] = "No hay palabras con sentimiento válidas."
            return result

        # Process sentiment data
        words_df['sentimiento'] = pd.to_numeric(words_df['sentimiento'], errors='coerce').dropna()
        word_sentiment_map = {str(row['word']).lower(): row['sentimiento'] for _, row in words_df.iterrows()}

        if usernames: 
            subtitles_df = subtitles_df[subtitles_df['username'].isin(usernames)]

        if not subtitles_df.empty and word_sentiment_map:
            sentiment_scores = []
            by_user = {}
            word_pattern = re.compile(r'\b\w+\b')
            
            for _, row in subtitles_df.iterrows():
                subtitle = str(row['subtitles']).lower()
                username = str(row['username'])
                url = str(row.get('url', ''))
                pos = 0
                neg = 0
                subtitle_words = set(word_pattern.findall(subtitle))
                
                for word in subtitle_words:
                    sentiment = word_sentiment_map.get(word)
                    if sentiment is not None:
                        if sentiment > 0: 
                            pos += 1
                        elif sentiment < 0: 
                            neg += 1
                            
                total = pos + neg
                ratio = (pos - neg) / total if total > 0 else 0
                score_data = {
                    "username": username, 
                    "url": url, 
                    "positive_words": pos, 
                    "negative_words": neg, 
                    "sentiment_ratio": ratio
                }
                sentiment_scores.append(score_data)
                
                user_stats = by_user.setdefault(username, {
                    "username": username, 
                    "positive_total": 0, 
                    "negative_total": 0, 
                    "videos_analyzed": 0
                })
                user_stats["positive_total"] += pos
                user_stats["negative_total"] += neg
                user_stats["videos_analyzed"] += 1

            for stats in by_user.values():
                total = stats["positive_total"] + stats["negative_total"]
                stats["avg_sentiment"] = safe_float((stats["positive_total"] - stats["negative_total"]) / total if total > 0 else 0)

            result["data"] = sorted(sentiment_scores, key=lambda x: x['sentiment_ratio'], reverse=True)[:50]
            result["by_user"] = sorted(list(by_user.values()), key=lambda x: x['avg_sentiment'], reverse=True)

        if not result["data"] and not result["by_user"]: 
            result["error"] = "No se encontraron datos de sentimiento para la consulta."
    except Exception as e: logger.error(f"Error en generate_sentiment_analysis: {e}", exc_info=True); result["error"] = f"Error interno: {e}"
    return result

def generate_summary_visualization(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    result = { "type": "summary", "title": "Resumen General de Datos", "charts": [], "stats": {} }
    chart_functions = [ _add_perspective_pie, _add_themes_bar, _add_top_accounts_bar, _add_timeline_line, _add_top_creators_bar, _add_sentiment_pie, _add_word_types_bar ]
    
    try:
        # Check if we have any data at all
        total_records = 0
        for key in ['accounts', 'videos', 'words', 'subtitles']:
            df = data.get(key)
            if df is not None and hasattr(df, '__len__'):
                total_records += len(df)
        
        if total_records == 0:
            result["error"] = "No hay datos disponibles para generar un resumen."
            return result
        
        # Generate charts
        for func in chart_functions:
            try:
                chart = func(data)
                if chart and chart.get('data'):  # Only add charts with actual data
                    result["charts"].append(chart)
            except Exception as chart_err: 
                logger.warning(f"Error al generar sub-gráfico en resumen ({func.__name__}): {chart_err}", exc_info=False)
        
        # Generate stats
        result["stats"] = { 
            "Cuentas": len(data.get('accounts', pd.DataFrame())), 
            "Videos": len(data.get('videos', pd.DataFrame())), 
            "Palabras Léxico": len(data.get('words', pd.DataFrame())), 
            "Con Subtítulos": len(data.get('subtitles', pd.DataFrame())) 
        }
        
        # Check if we have meaningful results
        if not result["charts"] and not any(result["stats"].values()): 
            result["error"] = "No se pudo generar un resumen con los datos disponibles."
        elif not result["charts"]:
            # If we have stats but no charts, that's still okay - show the stats
            logger.info("Resumen generado solo con estadísticas, sin gráficos")
            
    except Exception as e: 
        logger.error(f"Error en generate_summary_visualization: {e}", exc_info=True)
        result["error"] = f"Error interno: {e}"
    
    return result

# --- Helper functions for Summary --- (Using name/value consistently)
def _add_perspective_pie(data):
    if 'accounts' in data and not data['accounts'].empty and 'perspective' in data['accounts'].columns:
        df = data['accounts'].dropna(subset=['perspective'])
        if not df.empty: counts = df['perspective'].value_counts().reset_index(); counts.columns = ['name', 'value']; return {"id": "perspective_pie", "type": "pie", "title": "Distribución por Perspectiva", "data": counts.to_dict('records')}
    return None
def _add_themes_bar(data):
    if 'accounts' in data and not data['accounts'].empty and 'themes' in data['accounts'].columns:
        themes = [t.strip() for themes_str in data['accounts']['themes'].dropna() for t in str(themes_str).split(',') if t.strip()]
        if themes: counts = Counter(themes).most_common(10); return {"id": "themes_bar", "type": "bar", "title": "Top 10 Temas", "data": [{"name": name, "value": value} for name, value in counts]}
    return None
def _add_top_accounts_bar(data):
     if 'accounts' in data and not data['accounts'].empty and 'followers_num' in data['accounts'].columns and 'username' in data['accounts'].columns:
        df = data['accounts'].dropna(subset=['username', 'followers_num'])
        if not df.empty: top = df.nlargest(10, 'followers_num'); return {"id": "top_accounts_bar", "type": "bar", "title": "Top 10 Cuentas (Seguidores)", "data": [{"name": row['username'], "value": safe_float(row['followers_num'])} for _, row in top.iterrows()]}
     return None
def _add_timeline_line(data):
    if 'videos' in data and not data['videos'].empty and 'date' in data['videos'].columns:
        df = data['videos'].copy(); df['date'] = pd.to_datetime(df['date'], errors='coerce'); df = df.dropna(subset=['date'])
        if not df.empty: df['year_month'] = df['date'].dt.strftime('%Y-%m'); counts = df.groupby('year_month').size().reset_index(name='value').sort_values('year_month'); return {"id": "timeline_line", "type": "line", "title": "Videos Publicados (Mensual)", "data": [{"date": row['year_month'], "value": safe_int(row['value'])} for _, row in counts.iterrows()]}
    return None
def _add_top_creators_bar(data):
    if 'videos' in data and not data['videos'].empty and 'username' in data['videos'].columns:
        df = data['videos'].dropna(subset=['username'])
        if not df.empty: counts = df['username'].value_counts().reset_index().head(10); counts.columns = ['name', 'value']; return {"id": "top_creators_bar", "type": "bar", "title": "Top 10 Creadores (Videos)", "data": counts.to_dict('records')}
    return None
def _add_sentiment_pie(data):
    if 'words' in data and not data['words'].empty and 'sentimiento' in data['words'].columns:
        df = data['words'].copy(); df['sentimiento'] = pd.to_numeric(df['sentimiento'], errors='coerce').dropna()
        if not df.empty:
            counts = df['sentimiento'].value_counts().reset_index(); counts.columns = ['sentiment', 'value']
            sentiment_map = {-1.0: "Negativo", 0.0: "Neutral", 1.0: "Positivo"}
            counts['name'] = counts['sentiment'].map(lambda x: sentiment_map.get(x, f"Otro ({x})"))
            return {"id": "sentiment_pie", "type": "pie", "title": "Distribución Sentimiento (Palabras)", "data": counts[['name', 'value']].to_dict('records')}
    return None
def _add_word_types_bar(data):
    if 'words' in data and not data['words'].empty and 'type_1' in data['words'].columns:
         df = data['words'].dropna(subset=['type_1'])
         if not df.empty: counts = df['type_1'].value_counts().reset_index().head(10); counts.columns = ['name', 'value']; return {"id": "word_types_bar", "type": "bar", "title": "Top 10 Tipos de Palabra (Tipo 1)", "data": counts.to_dict('records')}
    return None

def generate_focused_chart(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Generate a single, focused chart instead of multiple summary charts.
    Perfect for when users ask for "one individual chart" or similar.
    """
    result = {
        "type": "focused_chart",
        "title": "Gráfico Enfocado",
        "chart": None,
        "stats": {}
    }
    
    try:
        # Prioritize chart types based on available data and query content
        query_lower = query.lower()
        
        # 1. If query mentions specific words, show word-related chart
        if any(word in query_lower for word in ['palabra', 'término', 'vocabulario', 'léxico']):
            chart = _add_word_types_bar(data)
            if chart:
                result["chart"] = chart
                result["title"] = f"Análisis de Palabras - {chart['title']}"
                
        # 2. If query mentions users/creators, show top creators
        elif any(word in query_lower for word in ['usuario', 'creador', 'cuenta', 'perfil']):
            chart = _add_top_creators_bar(data)
            if chart:
                result["chart"] = chart
                result["title"] = f"Análisis de Creadores - {chart['title']}"
                
        # 3. If query mentions sentiment/opinion, show sentiment
        elif any(word in query_lower for word in ['sentimiento', 'opinión', 'emocional']):
            chart = _add_sentiment_pie(data)
            if chart:
                result["chart"] = chart
                result["title"] = f"Análisis de Sentimiento - {chart['title']}"
                
        # 4. If query mentions perspective/political, show perspectives
        elif any(word in query_lower for word in ['perspectiva', 'político', 'política', 'izquierda', 'derecha']):
            chart = _add_perspective_pie(data)
            if chart:
                result["chart"] = chart
                result["title"] = f"Análisis Político - {chart['title']}"
                
        # 5. Default: Show the most interesting available chart
        else:
            # Try charts in order of preference
            chart_functions = [
                _add_top_accounts_bar,    # Most followers
                _add_top_creators_bar,    # Most videos
                _add_perspective_pie,     # Political distribution
                _add_sentiment_pie,       # Sentiment distribution
                _add_word_types_bar       # Word types
            ]
            
            for func in chart_functions:
                try:
                    chart = func(data)
                    if chart and chart.get('data'):
                        result["chart"] = chart
                        result["title"] = f"Gráfico Individual - {chart['title']}"
                        break
                except Exception as e:
                    logger.debug(f"Error trying chart function {func.__name__}: {e}")
                    continue
        
        # Add basic stats
        result["stats"] = {
            "Cuentas": len(data.get('accounts', pd.DataFrame())),
            "Videos": len(data.get('videos', pd.DataFrame())),
            "Palabras": len(data.get('words', pd.DataFrame())),
            "Subtítulos": len(data.get('subtitles', pd.DataFrame()))
        }
        
        # Check if we got a chart
        if not result["chart"]:
            result["error"] = "No se pudo generar un gráfico individual con los datos disponibles."
            
    except Exception as e:
        logger.error(f"Error en generate_focused_chart: {e}", exc_info=True)
        result["error"] = f"Error generando gráfico individual: {e}"
    
    return result