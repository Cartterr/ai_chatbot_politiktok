#!/usr/bin/env python3

import fasttext
import os

def test_fasttext():
    """Test FastText language detection"""
    
    model_path = "/home/valentina/ai_chatbot_politiktok/backend/lid.176.bin"
    
    if not os.path.exists(model_path):
        print(f"❌ Model not found at {model_path}")
        print("Downloading model...")
        os.system("wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin")
    
    print("📚 Loading FastText model...")
    model = fasttext.load_model(model_path)
    print("✅ Model loaded successfully!")
    
    # Test cases
    test_cases = [
        ("Hola amigos, como están hoy? Espero que tengan un buen día.", "Spanish"),
        ("Hello friends, how are you today? I hope you have a good day.", "English"),
        ("Olá pessoal, como vocês estão hoje? Espero que tenham um bom dia.", "Portuguese"),
        ("Bonjour les amis, comment allez-vous aujourd'hui?", "French"),
        ("toi enojao con el mundo #foryou #parati", "Spanish with hashtags"),
        ("Reply to @someone uwu", "English with mentions"),
        ("ajsdkjf random gibberish text", "Unclear/Random"),
    ]
    
    print("\n🧪 Testing language detection:")
    print("=" * 60)
    
    for text, description in test_cases:
        predictions = model.predict(text, k=1)
        language_code = predictions[0][0].replace('__label__', '')
        confidence = predictions[1][0]
        
        # Determine if Spanish
        is_spanish = language_code == "es" and confidence > 0.3
        result = "✅ SPANISH" if is_spanish else f"❌ NOT SPANISH ({language_code})"
        
        print(f"\n📝 {description}:")
        print(f"   Text: {text[:50]}...")
        print(f"   {result} (confidence: {confidence:.3f})")
    
    print("\n🎉 FastText testing complete!")
    return True

if __name__ == "__main__":
    test_fasttext()
