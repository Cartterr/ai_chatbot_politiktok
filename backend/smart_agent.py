import pandas as pd
import numpy as np
import os
import re
import json
from typing import Dict, Any, List, Tuple, Optional
import logging
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

class SmartDataAgent:
    """
    Intelligent agent that automatically searches, greps, and analyzes data across all CSV files
    """
    
    def __init__(self, data_dir: str = "../data/output"):
        self.data_dir = Path(data_dir)
        self.clean_dir = self.data_dir / "clean"
        self.loaded_datasets = {}
        self.dataset_info = {}
        self._initialize_datasets()
    
    def _initialize_datasets(self):
        """Load and catalog all available datasets"""
        print("🤖 Smart Agent initializing...")
        
        # Priority order for datasets (most comprehensive first) - ULTIMATE VERSION
        dataset_priorities = [
            "ultimate_temporal_dataset.csv",  # ULTIMATE - combines all sources with temporal data
            "main_tiktok_data_clean.csv",  # MAIN CORE - comprehensive user data
            "combined_tiktok_data_with_dates_clean.csv",  # DATES for temporal analysis
            "subtitles_clean.csv"  # SUBTITLES for additional content
        ]
        
        # Check clean directory first
        for dataset_name in dataset_priorities:
            clean_path = self.clean_dir / dataset_name
            if clean_path.exists():
                try:
                    df = pd.read_csv(clean_path, low_memory=False)
                    self.loaded_datasets[dataset_name] = df
                    self.dataset_info[dataset_name] = {
                        "path": str(clean_path),
                        "shape": df.shape,
                        "columns": list(df.columns),
                        "text_columns": self._identify_text_columns(df),
                        "date_columns": self._identify_date_columns(df),
                        "priority": len(dataset_priorities) - dataset_priorities.index(dataset_name)
                    }
                    print(f"✅ Loaded: {dataset_name} ({df.shape[0]:,} rows, {df.shape[1]} cols)")
                except Exception as e:
                    print(f"❌ Error loading {dataset_name}: {e}")
        
        # Also load original datasets if clean versions not available
        if not self.loaded_datasets:
            for csv_file in self.data_dir.glob("*.csv"):
                if csv_file.name not in self.loaded_datasets:
                    try:
                        df = pd.read_csv(csv_file, low_memory=False, nrows=1000)  # Sample first
                        self.dataset_info[csv_file.name] = {
                            "path": str(csv_file),
                            "shape": (len(df), len(df.columns)),
                            "columns": list(df.columns),
                            "text_columns": self._identify_text_columns(df),
                            "date_columns": self._identify_date_columns(df),
                            "priority": 0
                        }
                        print(f"📋 Cataloged: {csv_file.name}")
                    except Exception as e:
                        print(f"❌ Error cataloging {csv_file.name}: {e}")
        
        print(f"🎯 Agent ready with {len(self.loaded_datasets)} loaded datasets and {len(self.dataset_info)} cataloged files")
    
    def _identify_text_columns(self, df: pd.DataFrame) -> List[str]:
        """Identify columns that contain text data"""
        text_indicators = ['title', 'transcription', 'subtitle', 'text', 'content', 'description', 'combined']
        text_columns = []
        
        for col in df.columns:
            col_lower = col.lower()
            if any(indicator in col_lower for indicator in text_indicators):
                text_columns.append(col)
            elif df[col].dtype == 'object':
                # Check if it's actually text (not categorical)
                sample = df[col].dropna().head(10)
                if len(sample) > 0:
                    avg_length = sample.astype(str).str.len().mean()
                    if avg_length > 20:  # Likely text if average length > 20 chars
                        text_columns.append(col)
        
        return text_columns
    
    def _identify_date_columns(self, df: pd.DataFrame) -> List[str]:
        """Identify columns that contain date data"""
        date_indicators = ['date', 'time', 'timestamp', 'upload', 'created', 'published']
        date_columns = []
        
        for col in df.columns:
            col_lower = col.lower()
            if any(indicator in col_lower for indicator in date_indicators):
                date_columns.append(col)
        
        return date_columns
    
    def smart_search(self, query: str, search_type: str = "auto") -> Dict[str, Any]:
        """
        Intelligent search across all datasets
        """
        query_lower = query.lower()
        results = {
            "query": query,
            "search_type": search_type,
            "matches": [],
            "summary": {},
            "recommendations": []
        }
        
        # Determine search strategy
        if search_type == "auto":
            if any(word in query_lower for word in ["fecha", "cuando", "tiempo", "date"]):
                search_type = "temporal"
            elif any(word in query_lower for word in ["palabra", "menciona", "contiene", "dice"]):
                search_type = "text_content"
            elif any(word in query_lower for word in ["usuario", "cuenta", "creator"]):
                search_type = "user_analysis"
            else:
                search_type = "general"
        
        print(f"🔍 Smart search: '{query}' (type: {search_type})")
        
        # Search across all loaded datasets
        for dataset_name, df in self.loaded_datasets.items():
            dataset_matches = self._search_dataset(df, query, search_type, dataset_name)
            if dataset_matches["total_matches"] > 0:
                results["matches"].append(dataset_matches)
        
        # Generate summary and recommendations
        results["summary"] = self._generate_search_summary(results["matches"])
        results["recommendations"] = self._generate_recommendations(query, results["matches"])
        
        return results
    
    def _search_dataset(self, df: pd.DataFrame, query: str, search_type: str, dataset_name: str) -> Dict[str, Any]:
        """Search within a specific dataset"""
        info = self.dataset_info.get(dataset_name, {})
        text_cols = info.get("text_columns", [])
        date_cols = info.get("date_columns", [])
        
        matches = {
            "dataset": dataset_name,
            "dataset_info": info,
            "total_matches": 0,
            "column_matches": {},
            "sample_results": [],
            "temporal_analysis": None
        }
        
        # Extract search terms
        search_terms = self._extract_search_terms(query)
        
        # Search in text columns
        for col in text_cols:
            if col in df.columns:
                col_matches = self._search_column_text(df, col, search_terms)
                if len(col_matches) > 0:
                    matches["column_matches"][col] = len(col_matches)
                    matches["total_matches"] += len(col_matches)
                    
                    # Add sample results
                    sample_size = min(3, len(col_matches))
                    for idx in col_matches.head(sample_size).index:
                        sample = {
                            "column": col,
                            "content": str(df.loc[idx, col])[:200] + "..." if len(str(df.loc[idx, col])) > 200 else str(df.loc[idx, col]),
                            "row_data": {}
                        }
                        
                        # Add relevant context columns
                        context_cols = ['username', 'date', 'upload_date', 'title', 'views'] 
                        for ctx_col in context_cols:
                            if ctx_col in df.columns:
                                sample["row_data"][ctx_col] = df.loc[idx, ctx_col]
                        
                        matches["sample_results"].append(sample)
        
        # Temporal analysis if requested and date columns available
        if search_type == "temporal" and date_cols and matches["total_matches"] > 0:
            matches["temporal_analysis"] = self._analyze_temporal_patterns(
                df, search_terms, text_cols, date_cols[0]
            )
        
        return matches
    
    def _extract_search_terms(self, query: str) -> List[str]:
        """Extract meaningful search terms from query"""
        # Remove common Spanish stop words and question words
        stop_words = {'que', 'cuando', 'donde', 'como', 'por', 'para', 'con', 'en', 'de', 'la', 'el', 'y', 'o', 'a', 'un', 'una'}
        
        # Extract quoted terms first
        quoted_terms = re.findall(r'["\']([^"\']+)["\']', query)
        
        # Extract other meaningful words
        words = re.findall(r'\b\w+\b', query.lower())
        meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
        
        return quoted_terms + meaningful_words[:5]  # Limit to avoid too broad searches
    
    def _search_column_text(self, df: pd.DataFrame, column: str, search_terms: List[str]) -> pd.Series:
        """Search for terms within a text column"""
        if not search_terms:
            return pd.Series([], dtype=bool)
        
        # Create regex pattern for all terms
        pattern = '|'.join([re.escape(term) for term in search_terms])
        
        # Search (case insensitive)
        mask = df[column].astype(str).str.contains(pattern, case=False, na=False, regex=True)
        
        return df[mask]
    
    def _analyze_temporal_patterns(self, df: pd.DataFrame, search_terms: List[str], text_cols: List[str], date_col: str) -> Dict[str, Any]:
        """Analyze temporal patterns for search terms"""
        try:
            # Find rows matching search terms
            all_matches = pd.Series([False] * len(df))
            for col in text_cols:
                if col in df.columns:
                    col_matches = self._search_column_text(df, col, search_terms)
                    all_matches = all_matches | col_matches.index.isin(df.index)
            
            matching_df = df[all_matches].copy()
            
            if len(matching_df) == 0 or date_col not in matching_df.columns:
                return None
            
            # Parse dates
            matching_df[date_col] = pd.to_datetime(matching_df[date_col], errors='coerce')
            matching_df = matching_df.dropna(subset=[date_col])
            
            if len(matching_df) == 0:
                return None
            
            # Temporal analysis
            matching_df['year'] = matching_df[date_col].dt.year
            matching_df['month'] = matching_df[date_col].dt.to_period('M')
            
            yearly_counts = matching_df['year'].value_counts().sort_index().to_dict()
            monthly_counts = matching_df['month'].value_counts().sort_index()
            top_months = {str(k): v for k, v in monthly_counts.head(10).to_dict().items()}
            
            return {
                "total_matches": len(matching_df),
                "date_range": {
                    "earliest": str(matching_df[date_col].min()),
                    "latest": str(matching_df[date_col].max())
                },
                "yearly_distribution": yearly_counts,
                "top_months": top_months,
                "peak_year": max(yearly_counts.items(), key=lambda x: x[1]) if yearly_counts else None
            }
            
        except Exception as e:
            logger.error(f"Error in temporal analysis: {e}")
            return None
    
    def _generate_search_summary(self, matches: List[Dict]) -> Dict[str, Any]:
        """Generate summary of search results"""
        total_matches = sum(m["total_matches"] for m in matches)
        datasets_with_matches = len([m for m in matches if m["total_matches"] > 0])
        
        best_dataset = None
        if matches:
            best_dataset = max(matches, key=lambda x: x["total_matches"])
        
        return {
            "total_matches": total_matches,
            "datasets_searched": len(matches),
            "datasets_with_matches": datasets_with_matches,
            "best_dataset": best_dataset["dataset"] if best_dataset else None,
            "best_dataset_matches": best_dataset["total_matches"] if best_dataset else 0
        }
    
    def _generate_recommendations(self, query: str, matches: List[Dict]) -> List[str]:
        """Generate recommendations based on search results"""
        recommendations = []
        
        if not matches or sum(m["total_matches"] for m in matches) == 0:
            recommendations.append("No se encontraron coincidencias. Intenta con términos más generales o sinónimos.")
            recommendations.append("Verifica la ortografía de los términos de búsqueda.")
            return recommendations
        
        # Find best sources
        best_matches = sorted(matches, key=lambda x: x["total_matches"], reverse=True)[:3]
        
        for match in best_matches:
            if match["total_matches"] > 0:
                dataset_name = match["dataset"].replace("_clean.csv", "").replace("final_tiktok_data_", "")
                recommendations.append(f"Dataset '{dataset_name}' tiene {match['total_matches']} coincidencias")
                
                if match["temporal_analysis"]:
                    temp = match["temporal_analysis"]
                    if temp["peak_year"]:
                        year, count = temp["peak_year"]
                        recommendations.append(f"Pico de actividad en {year} con {count} menciones")
        
        return recommendations
    
    def get_dataset_info(self) -> Dict[str, Any]:
        """Get information about all available datasets"""
        return {
            "loaded_datasets": len(self.loaded_datasets),
            "cataloged_datasets": len(self.dataset_info),
            "dataset_details": self.dataset_info
        }

# Global instance
smart_agent = SmartDataAgent()

def search_with_agent(query: str, search_type: str = "auto") -> Dict[str, Any]:
    """Main function to search using the smart agent"""
    return smart_agent.smart_search(query, search_type)

def get_agent_info() -> Dict[str, Any]:
    """Get agent information"""
    return smart_agent.get_dataset_info()
