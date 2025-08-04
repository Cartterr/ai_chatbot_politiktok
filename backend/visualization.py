# backend/visualization.py

import pandas as pd
import numpy as np
import json
import re
from typing import Dict, Any, List, Optional
import logging
from collections import Counter

logger = logging.getLogger(__name__)

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
    Devuelve datos en formato JSON adecuados para el frontend.
    """
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
        'summary': generate_summary_visualization
    }
    generator_func = generators.get(viz_type, generate_summary_visualization)

    try:
        visualization_data = generator_func(data, query)
        if "type" not in visualization_data: visualization_data["type"] = viz_type
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
        if 'videos' in data and not data['videos'].empty and 'date' in data['videos'].columns:
            df = data['videos'].copy(); df['date'] = pd.to_datetime(df['date'], errors='coerce'); df = df.dropna(subset=['date'])
            username_pattern = re.compile(r'@(\w+)', re.IGNORECASE); usernames = username_pattern.findall(query)
            if usernames: df = df[df['username'].isin(usernames)]

            if not df.empty:
                df['year_month'] = df['date'].dt.strftime('%Y-%m')
                monthly_counts = df.groupby('year_month').size().reset_index(name='count').sort_values('year_month')
                result["data"] = [{"date": row['year_month'], "count": safe_int(row['count'])} for _, row in monthly_counts.iterrows()]

                if not monthly_counts.empty:
                    result["stats"] = { "Total Videos": safe_int(monthly_counts['count'].sum()), "Promedio Mensual": safe_float(monthly_counts['count'].mean()), "Mes Pico": monthly_counts.loc[monthly_counts['count'].idxmax(), 'year_month'], "Máximo Mensual": safe_int(monthly_counts['count'].max()) }

                if 'views' in df.columns and pd.api.types.is_numeric_dtype(df['views']):
                     df_views = df.dropna(subset=['views']);
                     if not df_views.empty:
                         views_by_month = df_views.groupby('year_month')['views'].mean().reset_index()
                         result["views_data"] = [{"date": row['year_month'], "avg_views": safe_float(row['views'])} for _, row in views_by_month.iterrows()]
            else: result["error"] = "No se encontraron videos para los criterios especificados."
        else: result["error"] = "No hay datos temporales de videos disponibles."
    except Exception as e: logger.error(f"Error en generate_time_series: {e}", exc_info=True); result["error"] = f"Error interno: {e}"
    return result

def generate_comparison(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    result = { "type": "comparison", "title": "Comparativas", "follower_comparison": [], "perspective_comparison": [], "theme_comparison": [], "views_comparison": [] }
    try:
        username_pattern = re.compile(r'@(\w+)', re.IGNORECASE); usernames = username_pattern.findall(query)
        accounts_df_orig = data.get('accounts'); videos_df_orig = data.get('videos')

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
    # Placeholder - Network graphs often require specific frontend libraries (like react-force-graph, vis.js, d3)
    # and the data structure (nodes, links) depends heavily on that library.
    # Returning an error or a simple message is safer for now.
    logger.warning("Generación de visualización de red no implementada completamente en el backend.")
    return { "type": "network", "title": "Análisis de Red (No Disponible)", "error": "La visualización de red requiere una implementación frontend específica." }


def generate_sentiment_analysis(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    result = { "type": "sentiment", "title": "Análisis de Sentimiento", "data": [], "by_user": [] }
    try:
        username_pattern = re.compile(r'@(\w+)', re.IGNORECASE); usernames = username_pattern.findall(query)
        if ('subtitles' in data and not data['subtitles'].empty and
            'words' in data and not data['words'].empty and 'sentimiento' in data['words'].columns):

            subtitles_df = data['subtitles'].copy().dropna(subset=['username', 'subtitles'])
            words_df = data['words'].copy().dropna(subset=['word', 'sentimiento'])
            words_df['sentimiento'] = pd.to_numeric(words_df['sentimiento'], errors='coerce').dropna()
            word_sentiment_map = {str(row['word']).lower(): row['sentimiento'] for _, row in words_df.iterrows()}

            if usernames: subtitles_df = subtitles_df[subtitles_df['username'].isin(usernames)]

            if not subtitles_df.empty and word_sentiment_map:
                sentiment_scores = []; by_user = {}; word_pattern = re.compile(r'\b\w+\b')
                for _, row in subtitles_df.iterrows():
                    subtitle = str(row['subtitles']).lower(); username = str(row['username']); url = str(row.get('url', ''))
                    pos = 0; neg = 0; subtitle_words = set(word_pattern.findall(subtitle))
                    for word in subtitle_words:
                        sentiment = word_sentiment_map.get(word)
                        if sentiment is not None:
                             if sentiment > 0: pos += 1
                             elif sentiment < 0: neg += 1
                    total = pos + neg; ratio = (pos - neg) / total if total > 0 else 0
                    score_data = {"username": username, "url": url, "positive_words": pos, "negative_words": neg, "sentiment_ratio": ratio}
                    sentiment_scores.append(score_data)
                    user_stats = by_user.setdefault(username, {"username": username, "positive_total": 0, "negative_total": 0, "videos_analyzed": 0})
                    user_stats["positive_total"] += pos; user_stats["negative_total"] += neg; user_stats["videos_analyzed"] += 1

                for stats in by_user.values():
                    total = stats["positive_total"] + stats["negative_total"]
                    stats["avg_sentiment"] = safe_float((stats["positive_total"] - stats["negative_total"]) / total if total > 0 else 0)

                result["data"] = sorted(sentiment_scores, key=lambda x: x['sentiment_ratio'], reverse=True)[:50]
                result["by_user"] = sorted(list(by_user.values()), key=lambda x: x['avg_sentiment'], reverse=True)

            if not result["data"] and not result["by_user"]: result["error"] = "No se encontraron datos de sentimiento para la consulta."
        else: result["error"] = "Datos insuficientes (subtítulos y léxico con sentimiento) para análisis."
    except Exception as e: logger.error(f"Error en generate_sentiment_analysis: {e}", exc_info=True); result["error"] = f"Error interno: {e}"
    return result

def generate_summary_visualization(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    result = { "type": "summary", "title": "Resumen General de Datos", "charts": [], "stats": {} }
    chart_functions = [ _add_perspective_pie, _add_themes_bar, _add_top_accounts_bar, _add_timeline_line, _add_top_creators_bar, _add_sentiment_pie, _add_word_types_bar ]
    try:
        for func in chart_functions:
            try:
                 chart = func(data)
                 if chart: result["charts"].append(chart)
            except Exception as chart_err: logger.warning(f"Error al generar sub-gráfico en resumen ({func.__name__}): {chart_err}", exc_info=False)
        result["stats"] = { "Cuentas": len(data.get('accounts', pd.DataFrame())), "Videos": len(data.get('videos', pd.DataFrame())), "Palabras Léxico": len(data.get('words', pd.DataFrame())), "Con Subtítulos": len(data.get('subtitles', pd.DataFrame())) }
        if not result["charts"] and not any(result["stats"].values()): result["error"] = "No se pudo generar un resumen con los datos disponibles."
    except Exception as e: logger.error(f"Error en generate_summary_visualization: {e}", exc_info=True); result["error"] = f"Error interno: {e}"
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