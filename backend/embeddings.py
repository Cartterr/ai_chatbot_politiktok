import numpy as np
import pandas as pd
import re
import logging
from typing import Dict, Any, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Global variables to store embeddings
tfidf_vectorizer = None
account_embeddings = None
video_embeddings = None
subtitle_embeddings = None

def preprocess_text(text):
    """Clean and preprocess text for embedding"""
    if not isinstance(text, str):
        return ""
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove hashtags but keep the text
    text = re.sub(r'#(\w+)', r'\1', text)
    # Remove special characters but keep accented letters for Spanish
    text = re.sub(r'[^\w\s\u00C0-\u017F]', ' ', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip().lower()
    
    return text

def create_embeddings(data: Dict[str, Any]) -> None:
    """Create TF-IDF embeddings for all textual data"""
    global tfidf_vectorizer, account_embeddings, video_embeddings, subtitle_embeddings
    
    try:
        # Initialize the TF-IDF vectorizer
        tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words=['de', 'la', 'el', 'y', 'a', 'en', 'que', 'los', 'se', 'del', 'las', 'un', 'por', 'con', 'no', 'una', 'su', 'para', 'es', 'al'],
            ngram_range=(1, 2)
        )
        
        # Create account corpus - combine available textual fields
        if 'accounts' in data and not data['accounts'].empty:
            account_corpus = []
            for _, row in data['accounts'].iterrows():
                text = f"{row.get('username', '')} {row.get('perspective', '')} {row.get('themes', '')}"
                account_corpus.append(preprocess_text(text))
            
            # Fit and transform account data
            account_embeddings = tfidf_vectorizer.fit_transform(account_corpus)
        
        # Transform other data using the fitted vectorizer
        # Video data
        if 'videos' in data and not data['videos'].empty:
            video_corpus = []
            for _, row in data['videos'].iterrows():
                text = f"{row.get('username', '')} {row.get('title', '')}"
                video_corpus.append(preprocess_text(text))
            
            video_embeddings = tfidf_vectorizer.transform(video_corpus)
        
        # Subtitle data
        if 'subtitles' in data and not data['subtitles'].empty:
            subtitle_corpus = []
            for _, row in data['subtitles'].iterrows():
                text = f"{row.get('username', '')} {row.get('subtitles', '')}"
                subtitle_corpus.append(preprocess_text(text))
            
            subtitle_embeddings = tfidf_vectorizer.transform(subtitle_corpus)
        
        logger.info("Embeddings created successfully")
    
    except Exception as e:
        logger.error(f"Error creating embeddings: {str(e)}")

def semantic_search(query: str, data: Dict[str, Any], top_k: int = 10) -> Dict[str, Any]:
    """
    Search for relevant data using semantic similarity with the query
    """
    global tfidf_vectorizer, account_embeddings, video_embeddings, subtitle_embeddings
    
    # Create embeddings if they don't exist yet
    if tfidf_vectorizer is None:
        create_embeddings(data)
    
    # Preprocess the query
    query_processed = preprocess_text(query)
    
    # Transform the query into the same vector space
    query_vector = tfidf_vectorizer.transform([query_processed])
    
    results = {}
    
    # Search in accounts data
    if account_embeddings is not None and 'accounts' in data:
        similarities = cosine_similarity(query_vector, account_embeddings).flatten()
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        # Only include results with some similarity
        relevant_accounts = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Minimum similarity threshold
                relevant_accounts.append(data['accounts'].iloc[idx].to_dict())
        
        results['accounts'] = relevant_accounts
    
    # Search in videos data
    if video_embeddings is not None and 'videos' in data:
        similarities = cosine_similarity(query_vector, video_embeddings).flatten()
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        # Only include results with some similarity
        relevant_videos = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Minimum similarity threshold
                relevant_videos.append(data['videos'].iloc[idx].to_dict())
        
        results['videos'] = relevant_videos
    
    # Search in subtitles data
    if subtitle_embeddings is not None and 'subtitles' in data:
        similarities = cosine_similarity(query_vector, subtitle_embeddings).flatten()
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        # Only include results with some similarity
        relevant_subtitles = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Minimum similarity threshold
                relevant_subtitles.append(data['subtitles'].iloc[idx].to_dict())
        
        results['subtitles'] = relevant_subtitles
    
    # Include a small sample of word sentiment data if relevant
    if 'words' in data and not data['words'].empty:
        # Extract keywords from the query (simple approach)
        keywords = set(re.findall(r'\b\w{3,}\b', query_processed.lower()))
        
        # Find words in the sentiment lexicon that match the query keywords
        relevant_words = data['words'][
            data['words']['word'].str.lower().apply(lambda x: any(kw in x for kw in keywords))
        ].head(20).to_dict(orient='records')
        
        if relevant_words:
            results['sentiment_words'] = relevant_words
    
    return results