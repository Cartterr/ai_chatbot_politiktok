#!/usr/bin/env python3

import pandas as pd
import re
import os

def load_spanish_indicators():
    """Load Spanish words and patterns that indicate Spanish content"""
    spanish_words = {
        # Common Spanish words
        'que', 'de', 'la', 'el', 'en', 'y', 'a', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'una', 'su',
        'para', 'como', 'pero', 'muy', 'todo', 'mas', 'del', 'me', 'un', 'ya', 'mi', 'si', 'porque', 'cuando', 'donde', 'quien',
        'como', 'cual', 'tanto', 'poco', 'mucho', 'bien', 'mal', 'aqui', 'alli', 'este', 'esta', 'estos', 'estas', 'ese', 'esa',
        'esos', 'esas', 'aquel', 'aquella', 'aquellos', 'aquellas', 'mismo', 'misma', 'mismos', 'mismas', 'otro', 'otra', 'otros',
        'otras', 'alguno', 'alguna', 'algunos', 'algunas', 'ninguno', 'ninguna', 'ningunos', 'ningunas', 'todo', 'toda', 'todos',
        'todas', 'cada', 'cualquier', 'cualquiera', 'cualesquiera', 'tal', 'tales', 'tanto', 'tanta', 'tantos', 'tantas',
        
        # Verbs
        'ser', 'estar', 'tener', 'hacer', 'decir', 'dar', 'ir', 'ver', 'saber', 'poder', 'querer', 'venir', 'llegar', 'pasar',
        'deber', 'poner', 'parecer', 'quedar', 'creer', 'hablar', 'llevar', 'dejar', 'seguir', 'encontrar', 'llamar', 'volver',
        'empezar', 'conocer', 'sentir', 'vivir', 'morir', 'subir', 'bajar', 'salir', 'entrar', 'trabajar', 'estudiar', 'jugar',
        
        # Common expressions and words
        'hola', 'adios', 'gracias', 'por favor', 'perdon', 'disculpa', 'bueno', 'malo', 'grande', 'pequeno', 'nuevo', 'viejo',
        'joven', 'mayor', 'mejor', 'peor', 'primero', 'ultimo', 'proximo', 'anterior', 'siguiente', 'mismo', 'diferente',
        'igual', 'parecido', 'distinto', 'facil', 'dificil', 'posible', 'imposible', 'necesario', 'importante', 'interesante',
        'aburrido', 'divertido', 'feliz', 'triste', 'contento', 'enfadado', 'enojado', 'preocupado', 'tranquilo', 'nervioso',
        
        # Time and numbers
        'hoy', 'ayer', 'manana', 'ahora', 'antes', 'despues', 'siempre', 'nunca', 'a veces', 'muchas veces', 'pocas veces',
        'temprano', 'tarde', 'pronto', 'luego', 'entonces', 'mientras', 'durante', 'hasta', 'desde', 'hace', 'dentro',
        'fuera', 'encima', 'debajo', 'delante', 'detras', 'cerca', 'lejos', 'arriba', 'abajo', 'izquierda', 'derecha',
        
        # Chilean/Latin American specific
        'wea', 'weón', 'po', 'cachai', 'fome', 'bacán', 'choro', 'cuático', 'raja', 'pega', 'pololo', 'polola', 'carrete',
        'copete', 'once', 'tuto', 'guagua', 'cabro', 'cabra', 'compadre', 'comadre', 'palta', 'marraqueta', 'completo',
        'empanada', 'asado', 'chicha', 'terremoto', 'pisco', 'manjar', 'sopaipilla',
        
        # Social/political terms in Spanish
        'politica', 'gobierno', 'presidente', 'congreso', 'constitucion', 'derecho', 'izquierda', 'centro', 'sociedad',
        'comunidad', 'gente', 'pueblo', 'pais', 'nacion', 'estado', 'region', 'ciudad', 'comuna', 'barrio', 'vecino',
        'familia', 'amigo', 'companero', 'pareja', 'novio', 'novia', 'esposo', 'esposa', 'hijo', 'hija', 'padre', 'madre',
        'hermano', 'hermana', 'abuelo', 'abuela', 'tio', 'tia', 'primo', 'prima', 'sobrino', 'sobrina'
    }
    
    # Spanish verb conjugation patterns
    spanish_patterns = [
        r'\b\w+ando\b',  # gerundio (-ando)
        r'\b\w+iendo\b',  # gerundio (-iendo)
        r'\b\w+ado\b',    # participio (-ado)
        r'\b\w+ido\b',    # participio (-ido)
        r'\b\w+ar\b',     # infinitivo (-ar)
        r'\b\w+er\b',     # infinitivo (-er)
        r'\b\w+ir\b',     # infinitivo (-ir)
        r'\b\w+ción\b',   # sustantivos (-ción)
        r'\b\w+sión\b',   # sustantivos (-sión)
        r'\b\w+dad\b',    # sustantivos (-dad)
        r'\b\w+mente\b',  # adverbios (-mente)
    ]
    
    return spanish_words, spanish_patterns

def load_english_indicators():
    """Load strong English indicators"""
    strong_english = {
        # Strong English indicators (common function words)
        'the', 'and', 'that', 'have', 'for', 'not', 'with', 'you', 'this', 'but', 'his', 'from', 'they', 'she', 'been',
        'than', 'its', 'who', 'did', 'get', 'has', 'had', 'him', 'her', 'what', 'your', 'when', 'him', 'my', 'me',
        'will', 'there', 'can', 'said', 'each', 'which', 'their', 'time', 'will', 'about', 'if', 'up', 'out', 'many',
        'then', 'them', 'these', 'so', 'some', 'would', 'make', 'like', 'into', 'him', 'has', 'two', 'more', 'very',
        'what', 'know', 'just', 'first', 'get', 'over', 'think', 'where', 'much', 'go', 'well', 'were', 'me', 'back',
        
        # English contractions (very strong indicators)
        "it's", "i'm", "don't", "can't", "won't", "you're", "they're", "we're", "isn't", "aren't", "wasn't", "weren't",
        "haven't", "hasn't", "hadn't", "wouldn't", "shouldn't", "couldn't", "that's", "what's", "where's", "here's",
        
        # English sentences starters
        'hello', 'hi', 'thank', 'thanks', 'please', 'sorry', 'excuse', 'welcome', 'goodbye', 'bye', 'see', 'nice',
        'good', 'great', 'amazing', 'awesome', 'beautiful', 'pretty', 'cute', 'funny', 'interesting', 'boring',
        
        # English question words
        'what', 'when', 'where', 'why', 'how', 'who', 'which', 'whose', 'whom'
    }
    
    return strong_english

def get_excluded_terms():
    """Terms to exclude from language detection (international/borrowed terms)"""
    return {
        # Hashtags and social media terms (used internationally)
        'fyp', 'foryou', 'parati', 'viral', 'trending', 'challenge', 'duet', 'remix', 'filter', 'effect', 'tiktok',
        'instagram', 'facebook', 'twitter', 'youtube', 'hashtag', 'tag', 'post', 'story', 'live', 'streaming',
        
        # LGBTQ+ terms (used internationally)
        'lgbt', 'gay', 'trans', 'queer', 'lesbian', 'bisexual', 'transgender', 'non-binary', 'pride',
        
        # International borrowed terms
        'tutorial', 'makeup', 'outfit', 'style', 'punk', 'alternative', 'rock', 'pop', 'jazz', 'blues', 'reggae',
        'selfie', 'stories', 'reels', 'feed', 'timeline', 'profile', 'bio', 'link', 'app', 'web', 'online', 'internet',
        
        # Tech terms
        'wifi', 'usb', 'pc', 'tv', 'dvd', 'cd', 'smartphone', 'tablet', 'laptop', 'desktop', 'software', 'hardware',
        
        # Single letters and abbreviations
        'a', 'i', 'u', 'x', 'y', 'z', 'dj', 'vj', 'mc', 'diy', 'faq', 'pdf', 'jpg', 'png', 'mp3', 'mp4',
        
        # Countries/places (often in English)
        'chile', 'usa', 'uk', 'canada', 'australia', 'france', 'germany', 'spain', 'italy', 'brazil', 'argentina'
    }

def analyze_language_content(text, spanish_words, spanish_patterns, english_words, excluded_terms):
    """Analyze if text is predominantly Spanish or English"""
    if pd.isna(text) or text == "":
        return "unknown", 0, 0
    
    text_lower = str(text).lower()
    
    # Remove hashtags and mentions
    text_clean = re.sub(r'[#@]\w+', '', text_lower)
    
    # Extract words
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text_clean)
    
    spanish_score = 0
    english_score = 0
    total_words = 0
    
    # Check individual words
    for word in words:
        if word in excluded_terms:
            continue
            
        total_words += 1
        
        if word in spanish_words:
            spanish_score += 1
        elif word in english_words:
            english_score += 1
    
    # Check Spanish patterns
    for pattern in spanish_patterns:
        matches = re.findall(pattern, text_clean)
        spanish_score += len(matches) * 0.5  # Pattern matches get half weight
    
    # Determine predominant language
    if spanish_score > english_score:
        return "spanish", spanish_score, english_score
    elif english_score > spanish_score:
        return "english", spanish_score, english_score
    else:
        return "mixed", spanish_score, english_score

def is_predominantly_english(text, spanish_words, spanish_patterns, english_words, excluded_terms):
    """Check if text is predominantly English (should be removed)"""
    language, spanish_score, english_score = analyze_language_content(text, spanish_words, spanish_patterns, english_words, excluded_terms)
    
    # Keep if:
    # 1. Predominantly Spanish
    # 2. Mixed but has some Spanish indicators
    # 3. Unknown/unclassifiable
    
    # Remove only if:
    # 1. Clearly English (english_score > spanish_score AND english_score > 2)
    # 2. No Spanish indicators at all AND has English words
    
    if language == "english" and english_score > 2 and spanish_score == 0:
        return True
    elif language == "english" and english_score > spanish_score * 2 and english_score > 3:
        return True
    else:
        return False

def filter_spanish_smart():
    """Smart filtering that preserves Spanish content with some English words"""
    
    # File paths
    input_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/main_tiktok_data_clean.csv"
    output_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/main_tiktok_data_smart_filtered.csv"
    removed_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/removed_english_videos_smart.csv"
    report_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/smart_filtering_report.txt"
    
    print("🔄 Loading dataset...")
    df = pd.read_csv(input_file, low_memory=False)
    print(f"✅ Loaded dataset: {len(df):,} rows")
    
    # Load language indicators
    print("📚 Loading language detection...")
    spanish_words, spanish_patterns = load_spanish_indicators()
    english_words = load_english_indicators()
    excluded_terms = get_excluded_terms()
    
    print(f"✅ Spanish indicators: {len(spanish_words):,} words + {len(spanish_patterns)} patterns")
    print(f"✅ English indicators: {len(english_words):,} words")
    print(f"✅ Excluded terms: {len(excluded_terms):,}")
    
    # Analyze content
    print("🔍 Performing smart language analysis...")
    
    english_title = df['title'].apply(lambda x: is_predominantly_english(x, spanish_words, spanish_patterns, english_words, excluded_terms))
    english_transcription = df['transcription'].apply(lambda x: is_predominantly_english(x, spanish_words, spanish_patterns, english_words, excluded_terms))
    
    # Remove only if BOTH title AND transcription are predominantly English
    # OR if one is clearly English and the other is empty/unknown
    predominantly_english = english_title & english_transcription
    
    # Separate datasets
    spanish_content = df[~predominantly_english].copy()
    english_content = df[predominantly_english].copy()
    
    # Results
    original_count = len(df)
    english_titles = english_title.sum()
    english_transcriptions = english_transcription.sum()
    total_removed = predominantly_english.sum()
    spanish_kept = len(spanish_content)
    removal_percentage = (total_removed / original_count * 100)
    
    print(f"\n📊 SMART FILTERING RESULTS:")
    print(f"   📹 Original videos: {original_count:,}")
    print(f"   🔤 Predominantly English titles: {english_titles:,}")
    print(f"   🗣️ Predominantly English transcriptions: {english_transcriptions:,}")
    print(f"   ❌ Videos removed (both title & transcription English): {total_removed:,}")
    print(f"   ✅ Spanish/Mixed content kept: {spanish_kept:,}")
    print(f"   📉 Percentage removed: {removal_percentage:.1f}%")
    
    # Save datasets
    print(f"\n💾 Saving filtered datasets...")
    spanish_content.to_csv(output_file, index=False)
    english_content.to_csv(removed_file, index=False)
    
    # Analyze some examples for the report
    print("📊 Analyzing examples...")
    examples_kept = []
    examples_removed = []
    
    for _, row in spanish_content.head(5).iterrows():
        title_lang = analyze_language_content(row['title'], spanish_words, spanish_patterns, english_words, excluded_terms)
        trans_lang = analyze_language_content(row['transcription'], spanish_words, spanish_patterns, english_words, excluded_terms)
        examples_kept.append((row, title_lang, trans_lang))
    
    for _, row in english_content.head(5).iterrows():
        title_lang = analyze_language_content(row['title'], spanish_words, spanish_patterns, english_words, excluded_terms)
        trans_lang = analyze_language_content(row['transcription'], spanish_words, spanish_patterns, english_words, excluded_terms)
        examples_removed.append((row, title_lang, trans_lang))
    
    # Create detailed report
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("SMART LANGUAGE FILTERING REPORT\n")
        f.write("=" * 50 + "\n\n")
        f.write("FILTERING LOGIC:\n")
        f.write("- Analyzes Spanish vs English word indicators\n")
        f.write("- Considers Spanish verb patterns and conjugations\n")
        f.write("- Excludes international terms (hashtags, LGBTQ+, tech)\n")
        f.write("- Removes only if BOTH title AND transcription are predominantly English\n")
        f.write("- Preserves Spanish content with some English words\n\n")
        
        f.write(f"RESULTS:\n")
        f.write(f"Original videos: {original_count:,}\n")
        f.write(f"Videos kept: {spanish_kept:,} ({100-removal_percentage:.1f}%)\n")
        f.write(f"Videos removed: {total_removed:,} ({removal_percentage:.1f}%)\n\n")
        
        f.write("EXAMPLES OF KEPT CONTENT:\n")
        f.write("-" * 30 + "\n")
        for i, (row, title_lang, trans_lang) in enumerate(examples_kept):
            f.write(f"\n{i+1}. @{row['username']}\n")
            f.write(f"   Title: {str(row['title'])[:100]}...\n")
            f.write(f"   Title analysis: {title_lang[0]} (ES:{title_lang[1]:.1f}, EN:{title_lang[2]:.1f})\n")
            f.write(f"   Transcription: {str(row['transcription'])[:150]}...\n")
            f.write(f"   Trans analysis: {trans_lang[0]} (ES:{trans_lang[1]:.1f}, EN:{trans_lang[2]:.1f})\n")
        
        f.write(f"\n\nEXAMPLES OF REMOVED CONTENT:\n")
        f.write("-" * 30 + "\n")
        for i, (row, title_lang, trans_lang) in enumerate(examples_removed):
            f.write(f"\n{i+1}. @{row['username']}\n")
            f.write(f"   Title: {str(row['title'])[:100]}...\n")
            f.write(f"   Title analysis: {title_lang[0]} (ES:{title_lang[1]:.1f}, EN:{title_lang[2]:.1f})\n")
            f.write(f"   Transcription: {str(row['transcription'])[:150]}...\n")
            f.write(f"   Trans analysis: {trans_lang[0]} (ES:{trans_lang[1]:.1f}, EN:{trans_lang[2]:.1f})\n")
    
    print(f"✅ Smart filtered dataset: {output_file}")
    print(f"✅ Removed videos: {removed_file}")
    print(f"✅ Detailed report: {report_file}")
    
    # Show examples
    print(f"\n📋 EXAMPLES OF DECISIONS:")
    print(f"\n✅ KEPT (Spanish/Mixed content):")
    for i, (row, title_lang, trans_lang) in enumerate(examples_kept[:2]):
        print(f"\n{i+1}. @{row['username']}")
        print(f"   📝 Title: {str(row['title'])[:80]}...")
        print(f"   📊 Title: {title_lang[0]} (Spanish:{title_lang[1]:.1f}, English:{title_lang[2]:.1f})")
        print(f"   🗣️ Trans: {str(row['transcription'])[:80]}...")
        print(f"   📊 Trans: {trans_lang[0]} (Spanish:{trans_lang[1]:.1f}, English:{trans_lang[2]:.1f})")
    
    if examples_removed:
        print(f"\n❌ REMOVED (Predominantly English):")
        for i, (row, title_lang, trans_lang) in enumerate(examples_removed[:2]):
            print(f"\n{i+1}. @{row['username']}")
            print(f"   📝 Title: {str(row['title'])[:80]}...")
            print(f"   📊 Title: {title_lang[0]} (Spanish:{title_lang[1]:.1f}, English:{title_lang[2]:.1f})")
            print(f"   🗣️ Trans: {str(row['transcription'])[:80]}...")
            print(f"   📊 Trans: {trans_lang[0]} (Spanish:{trans_lang[1]:.1f}, English:{trans_lang[2]:.1f})")
    
    print(f"\n🎉 SMART FILTERING COMPLETE!")
    print(f"✅ Preserved: {spanish_kept:,} videos ({100-removal_percentage:.1f}%)")
    print(f"❌ Removed: {total_removed:,} videos ({removal_percentage:.1f}%)")
    print(f"📁 Output: {output_file}")

if __name__ == "__main__":
    filter_spanish_smart()
