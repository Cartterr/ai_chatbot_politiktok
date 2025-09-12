import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

def analyze_user_activity_by_perspective(data: Dict[str, Any], perspective: str) -> Dict[str, Any]:
    """
    Analyze when users of a specific political perspective were most active
    """
    try:
        if "videos" not in data or data["videos"].empty:
            return {"error": "No video data available"}
        
        df = data["videos"].copy()
        
        if "perspective" not in df.columns or "date" not in df.columns:
            return {"error": "Missing perspective or date columns"}
        
        # Filter by perspective
        perspective_df = df[df["perspective"] == perspective].copy()
        
        if perspective_df.empty:
            return {"error": f"No videos found for perspective: {perspective}"}
        
        # Parse dates
        perspective_df["date"] = pd.to_datetime(perspective_df["date"], errors='coerce')
        perspective_df = perspective_df.dropna(subset=["date"])
        
        if perspective_df.empty:
            return {"error": "No valid dates found"}
        
        # Analyze temporal patterns
        perspective_df["year"] = perspective_df["date"].dt.year
        perspective_df["month"] = perspective_df["date"].dt.to_period('M')
        perspective_df["date_only"] = perspective_df["date"].dt.date
        
        # Get patterns
        yearly_counts = perspective_df["year"].value_counts().sort_index()
        monthly_counts = perspective_df["month"].value_counts().sort_index()
        daily_counts = perspective_df["date_only"].value_counts().sort_index()
        
        # Get peak periods
        peak_year = yearly_counts.idxmax()
        peak_month = monthly_counts.idxmax()
        peak_day = daily_counts.idxmax()
        
        return {
            "perspective": perspective,
            "total_videos": len(perspective_df),
            "date_range": {
                "earliest": str(perspective_df["date"].min()),
                "latest": str(perspective_df["date"].max())
            },
            "peak_year": {
                "year": int(peak_year),
                "count": int(yearly_counts[peak_year])
            },
            "peak_month": {
                "month": str(peak_month),
                "count": int(monthly_counts[peak_month])
            },
            "peak_day": {
                "date": str(peak_day),
                "count": int(daily_counts[peak_day])
            },
            "yearly_distribution": yearly_counts.to_dict(),
            "top_months": {str(k): v for k, v in monthly_counts.nlargest(5).items()},
            "top_days": {str(k): v for k, v in daily_counts.nlargest(5).items()}
        }
        
    except Exception as e:
        logger.error(f"Error in perspective analysis: {e}")
        return {"error": str(e)}

def analyze_user_activity_by_type(data: Dict[str, Any], user_type_pattern: str) -> Dict[str, Any]:
    """
    Analyze when users of a specific type were most active
    """
    try:
        if "videos" not in data or data["videos"].empty:
            return {"error": "No video data available"}
        
        df = data["videos"].copy()
        
        if "user_type" not in df.columns or "date" not in df.columns:
            return {"error": "Missing user_type or date columns"}
        
        # Filter by user type pattern
        type_df = df[df["user_type"].str.contains(user_type_pattern, na=False, case=False)].copy()
        
        if type_df.empty:
            return {"error": f"No videos found for user type pattern: {user_type_pattern}"}
        
        # Parse dates
        type_df["date"] = pd.to_datetime(type_df["date"], errors='coerce')
        type_df = type_df.dropna(subset=["date"])
        
        if type_df.empty:
            return {"error": "No valid dates found"}
        
        # Analyze temporal patterns
        type_df["year"] = type_df["date"].dt.year
        type_df["month"] = type_df["date"].dt.to_period('M')
        type_df["date_only"] = type_df["date"].dt.date
        
        # Get patterns
        yearly_counts = type_df["year"].value_counts().sort_index()
        monthly_counts = type_df["month"].value_counts().sort_index()
        daily_counts = type_df["date_only"].value_counts().sort_index()
        
        # Get peak periods
        peak_year = yearly_counts.idxmax()
        peak_month = monthly_counts.idxmax()
        peak_day = daily_counts.idxmax()
        
        return {
            "user_type_pattern": user_type_pattern,
            "total_videos": len(type_df),
            "date_range": {
                "earliest": str(type_df["date"].min()),
                "latest": str(type_df["date"].max())
            },
            "peak_year": {
                "year": int(peak_year),
                "count": int(yearly_counts[peak_year])
            },
            "peak_month": {
                "month": str(peak_month),
                "count": int(monthly_counts[peak_month])
            },
            "peak_day": {
                "date": str(peak_day),
                "count": int(daily_counts[peak_day])
            },
            "yearly_distribution": yearly_counts.to_dict(),
            "top_months": {str(k): v for k, v in monthly_counts.nlargest(5).items()},
            "top_days": {str(k): v for k, v in daily_counts.nlargest(5).items()}
        }
        
    except Exception as e:
        logger.error(f"Error in user type analysis: {e}")
        return {"error": str(e)}

def analyze_daily_activity_peaks(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze which days had the most publications
    """
    try:
        if "videos" not in data or data["videos"].empty:
            return {"error": "No video data available"}
        
        df = data["videos"].copy()
        
        if "date" not in df.columns:
            return {"error": "Missing date column"}
        
        # Parse dates
        df["date"] = pd.to_datetime(df["date"], errors='coerce')
        df = df.dropna(subset=["date"])
        
        if df.empty:
            return {"error": "No valid dates found"}
        
        # Get daily counts
        df["date_only"] = df["date"].dt.date
        daily_counts = df["date_only"].value_counts().sort_values(ascending=False)
        
        # Get top days
        top_days = daily_counts.head(10)
        
        # Get additional stats
        max_posts = daily_counts.max()
        avg_posts = daily_counts.mean()
        
        return {
            "total_days": len(daily_counts),
            "max_posts_per_day": int(max_posts),
            "avg_posts_per_day": round(float(avg_posts), 2),
            "top_10_days": {str(k): int(v) for k, v in top_days.items()},
            "peak_day": {
                "date": str(daily_counts.index[0]),
                "posts": int(daily_counts.iloc[0])
            }
        }
        
    except Exception as e:
        logger.error(f"Error in daily activity analysis: {e}")
        return {"error": str(e)}

def analyze_high_engagement_dates(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze which dates had videos with highest views
    """
    try:
        if "videos" not in data or data["videos"].empty:
            return {"error": "No video data available"}
        
        df = data["videos"].copy()
        
        if "views" not in df.columns or "date" not in df.columns:
            return {"error": "Missing views or date columns"}
        
        # Parse dates and views
        df["date"] = pd.to_datetime(df["date"], errors='coerce')
        df["views"] = pd.to_numeric(df["views"], errors='coerce')
        df = df.dropna(subset=["date", "views"])
        
        if df.empty:
            return {"error": "No valid data found"}
        
        # Get top videos by views
        top_videos = df.nlargest(10, "views")
        
        # Get daily view aggregations
        df["date_only"] = df["date"].dt.date
        daily_views = df.groupby("date_only")["views"].agg(['sum', 'mean', 'max', 'count']).sort_values('sum', ascending=False)
        
        return {
            "total_videos": len(df),
            "total_views": int(df["views"].sum()),
            "avg_views": round(float(df["views"].mean()), 2),
            "max_views": int(df["views"].max()),
            "top_10_videos": [
                {
                    "date": str(row["date"]),
                    "views": int(row["views"]),
                    "username": row.get("username", ""),
                    "title": str(row.get("title", ""))[:100] + "..." if len(str(row.get("title", ""))) > 100 else str(row.get("title", ""))
                }
                for _, row in top_videos.iterrows()
            ],
            "top_10_days_by_total_views": {
                str(k): {
                    "total_views": int(v["sum"]),
                    "avg_views": round(float(v["mean"]), 2),
                    "max_views": int(v["max"]),
                    "video_count": int(v["count"])
                }
                for k, v in daily_views.head(10).iterrows()
            }
        }
        
    except Exception as e:
        logger.error(f"Error in engagement analysis: {e}")
        return {"error": str(e)}
