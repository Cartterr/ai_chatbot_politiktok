#!/usr/bin/env python3

import pandas as pd
import re
import os

def load_english_words():
    """Load common English words for detection"""
    common_english_words = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
        'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him',
        'know', 'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then', 'now', 'look',
        'only', 'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way',
        'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us', 'is', 'was', 'are', 'been', 'has', 'had', 'were',
        'said', 'each', 'which', 'their', 'time', 'will', 'about', 'if', 'up', 'out', 'many', 'then', 'them', 'these', 'so', 'some',
        'her', 'would', 'make', 'like', 'into', 'him', 'has', 'two', 'more', 'very', 'what', 'know', 'just', 'first', 'get', 'over',
        'think', 'where', 'much', 'go', 'well', 'were', 'me', 'back', 'call', 'came', 'each', 'she', 'may', 'say', 'which', 'their',
        'use', 'her', 'than', 'now', 'its', 'our', 'out', 'day', 'had', 'up', 'his', 'your', 'way', 'too', 'any', 'may', 'new', 'want',
        'these', 'give', 'most', 'tell', 'very', 'when', 'much', 'before', 'move', 'right', 'boy', 'old', 'too', 'same', 'she', 'all',
        'there', 'when', 'up', 'use', 'word', 'how', 'said', 'an', 'each', 'which', 'do', 'their', 'time', 'if', 'will', 'way', 'about',
        'man', 'find', 'here', 'thing', 'give', 'many', 'well', 'only', 'those', 'tell', 'one', 'type', 'her', 'have', 'sit', 'now',
        'set', 'run', 'eat', 'far', 'sea', 'eye', 'bag', 'job', 'lot', 'fun', 'sun', 'cut', 'yes', 'yet', 'arm', 'off', 'bad', 'age',
        'end', 'why', 'let', 'try', 'ask', 'men', 'car', 'war', 'own', 'say', 'she', 'may', 'use', 'her', 'him', 'oil', 'sit', 'set',
        'hot', 'but', 'cut', 'let', 'run', 'got', 'lot', 'too', 'old', 'any', 'app', 'add', 'its', 'our', 'out', 'day', 'way',
        'new', 'now', 'get', 'has', 'had', 'his', 'her', 'you', 'all', 'can', 'did', 'not', 'who', 'put', 'big', 'boy', 'see', 'him',
        'two', 'how', 'top', 'own', 'under', 'last', 'right', 'move', 'thing', 'general', 'school', 'never', 'same', 'another', 'begin',
        'while', 'number', 'part', 'turn', 'real', 'leave', 'might', 'great', 'little', 'world', 'still', 'every', 'large', 'must',
        'big', 'group', 'those', 'often', 'run', 'important', 'until', 'children', 'side', 'feet', 'car', 'mile', 'night', 'walk',
        'white', 'sea', 'began', 'grow', 'took', 'river', 'four', 'carry', 'state', 'once', 'book', 'hear', 'stop', 'without', 'second',
        'later', 'miss', 'idea', 'enough', 'eat', 'face', 'watch', 'far', 'really', 'almost', 'let', 'above', 'girl', 'sometimes',
        'mountain', 'cut', 'young', 'talk', 'soon', 'list', 'song', 'leave', 'family'
    }
    
    # Add contractions and social media terms
    social_terms = {
        'video', 'like', 'follow', 'share', 'comment', 'subscribe', 'viral', 'trending', 'hashtag', 'post', 'story', 'live',
        'content', 'creator', 'followers', 'views', 'likes', 'duet', 'filter', 'effect', 'sound', 'music', 'dance', 'challenge',
        'trend', 'fyp', 'foryou', 'profile', 'amazing', 'awesome', 'cool', 'nice', 'great', 'love', 'funny', 'lol', 'omg', 'wow',
        'yes', 'no', 'ok', 'okay', 'thanks', 'thank', 'please', 'sorry', 'hello', 'hi', 'hey', 'bye', 'morning', 'today',
        'happy', 'beautiful', 'pretty', 'cute', 'smart', 'crazy', 'weird', 'different', 'easy', 'hard', 'simple', 'basic'
    }
    
    contractions = {
        "it's", "i'm", "don't", "can't", "won't", "you're", "they're", "we're", "isn't", "aren't", "wasn't", "weren't",
        "haven't", "hasn't", "hadn't", "wouldn't", "shouldn't", "couldn't"
    }
    
    return common_english_words.union(social_terms).union(contractions)

def contains_english(text, english_words):
    """Check if text contains English words"""
    if pd.isna(text) or text == "":
        return False
    
    text_lower = str(text).lower()
    # Extract words (letters only, minimum 2 characters)
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text_lower)
    
    # Check if any word is English
    for word in words:
        if word in english_words:
            return True
    
    return False

def filter_spanish_content():
    """Filter dataset to keep only Spanish content"""
    
    # File paths (WSL paths)
    input_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/main_tiktok_data_clean.csv"
    output_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/main_tiktok_data_spanish_only.csv"
    removed_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/removed_english_videos.csv"
    report_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/english_filtering_report.txt"
    
    print("🔄 Loading dataset...")
    try:
        df = pd.read_csv(input_file, low_memory=False)
        print(f"✅ Loaded dataset: {len(df):,} rows")
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return
    
    # Load English words
    print("📚 Loading English words dictionary...")
    english_words = load_english_words()
    print(f"✅ Loaded {len(english_words):,} English words")
    
    # Check for English content
    print("🔍 Scanning for English content...")
    
    english_in_title = df['title'].apply(lambda x: contains_english(x, english_words))
    english_in_transcription = df['transcription'].apply(lambda x: contains_english(x, english_words))
    
    # Videos with English content (in title OR transcription)
    has_english = english_in_title | english_in_transcription
    
    # Separate datasets
    spanish_only = df[~has_english].copy()
    english_videos = df[has_english].copy()
    
    # Results
    original_count = len(df)
    title_english_count = english_in_title.sum()
    transcription_english_count = english_in_transcription.sum()
    total_english_count = has_english.sum()
    spanish_count = len(spanish_only)
    removal_percentage = (total_english_count / original_count * 100)
    
    print(f"\n📊 FILTERING RESULTS:")
    print(f"   📹 Original videos: {original_count:,}")
    print(f"   🔤 English in titles: {title_english_count:,}")
    print(f"   🗣️ English in transcriptions: {transcription_english_count:,}")
    print(f"   ❌ Total videos with English: {total_english_count:,}")
    print(f"   ✅ Spanish-only videos: {spanish_count:,}")
    print(f"   📉 Percentage removed: {removal_percentage:.1f}%")
    
    # Save Spanish-only dataset
    print(f"\n💾 Saving filtered datasets...")
    spanish_only.to_csv(output_file, index=False)
    print(f"✅ Spanish-only saved: {output_file}")
    
    # Save removed videos for review
    english_videos.to_csv(removed_file, index=False)
    print(f"✅ Removed videos saved: {removed_file}")
    
    # Create detailed report
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("ENGLISH CONTENT FILTERING REPORT\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Original dataset: {original_count:,} videos\n")
        f.write(f"Videos with English in titles: {title_english_count:,}\n")
        f.write(f"Videos with English in transcriptions: {transcription_english_count:,}\n")
        f.write(f"Total videos removed: {total_english_count:,}\n")
        f.write(f"Spanish-only videos remaining: {spanish_count:,}\n")
        f.write(f"Removal percentage: {removal_percentage:.2f}%\n\n")
        f.write("EXAMPLES OF REMOVED CONTENT:\n")
        f.write("-" * 30 + "\n")
        
        for i, (_, row) in enumerate(english_videos.head(10).iterrows()):
            f.write(f"\n{i+1}. @{row['username']}\n")
            if pd.notna(row['title']):
                f.write(f"   Title: {str(row['title'])[:150]}...\n")
            if pd.notna(row['transcription']):
                f.write(f"   Transcription: {str(row['transcription'])[:200]}...\n")
    
    print(f"✅ Report saved: {report_file}")
    
    # Show examples
    print(f"\n📋 EXAMPLES OF REMOVED CONTENT:")
    if len(english_videos) > 0:
        for i, (_, row) in enumerate(english_videos.head(3).iterrows()):
            print(f"\n{i+1}. @{row['username']}")
            if pd.notna(row['title']):
                title_preview = str(row['title'])[:80] + "..." if len(str(row['title'])) > 80 else str(row['title'])
                print(f"   📝 Title: {title_preview}")
            if pd.notna(row['transcription']):
                trans_preview = str(row['transcription'])[:100] + "..." if len(str(row['transcription'])) > 100 else str(row['transcription'])
                print(f"   🗣️ Transcription: {trans_preview}")
    
    print(f"\n🎉 FILTERING COMPLETE!")
    print(f"✅ Clean Spanish dataset: {spanish_count:,} videos")
    print(f"📁 Output file: {output_file}")

if __name__ == "__main__":
    filter_spanish_content()
