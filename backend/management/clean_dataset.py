import pandas as pd
import requests
import json
import os
import time
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def call_deepseek_api(words_batch: List[str]) -> Dict[str, bool]:
    # Create a new session for each request to avoid any caching issues
    session = requests.Session()
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Connection": "close"
    }
    
    words_text = ", ".join(words_batch)
    
    prompt = f"""TAREA ESPECÍFICA: Analiza ÚNICAMENTE las palabras de la lista proporcionada. No consideres palabras de solicitudes anteriores.

LISTA A ANALIZAR: {words_text}

ELIMINA SOLO si están en la lista Y cumplen estos criterios:
1. Palabras en INGLÉS: stop, lie, mean, and, the, but, you, me, I, love, hate, ok, yes, no, green, times, cute, led, fine, christmas, dad
2. Artículos españoles básicos: el, la, los, las, un, una, de, del, en, con, por, para, y, o, que, si

MANTÉN TODO LO DEMÁS:
- Jerga chilena: weón, weá, wea, po, cachai, fome, bacán, cuático
- Palabras españolas: bien, mal, bueno, malo, claro, sale, libre, listo, gran, bajo, abajo, política, justicia
- Cualquier palabra española/chilena con significado

CRÍTICO: Solo devuelve palabras que estén en la lista proporcionada. NO agregues palabras externas.

JSON (sin explicaciones):
{{"palabras_a_eliminar": []}}"""

    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 2000,
        "stream": False,
        "top_p": 1.0
    }
    
    try:
        response = session.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        
        try:
            # Clean content to extract JSON from markdown blocks and explanations
            clean_content = content.strip()
            if clean_content.startswith('```json'):
                clean_content = clean_content[7:]
            if clean_content.startswith('```'):
                clean_content = clean_content[3:]
            if clean_content.endswith('```'):
                clean_content = clean_content[:-3]
            
            # Extract only the JSON part (before any explanation)
            lines = clean_content.split('\n')
            json_lines = []
            for line in lines:
                line = line.strip()
                if line.startswith('{') or line.startswith('['):
                    json_lines.append(line)
                elif json_lines and line.startswith('}') or line.startswith(']'):
                    json_lines.append(line)
                    break
                elif json_lines and not line.startswith('**') and not line.startswith('```') and line:
                    json_lines.append(line)
                elif line.startswith('**') or line.startswith('Explicación') or line.startswith('```'):
                    break
            
            clean_content = '\n'.join(json_lines).strip()
            
            parsed_result = json.loads(clean_content)
            words_to_remove = parsed_result.get('palabras_a_eliminar', [])
            
            result_dict = {}
            for word in words_batch:
                result_dict[word] = word in words_to_remove
            
            # Filter to only show words that are actually in this batch
            words_actually_removed = [word for word in words_to_remove if word in words_batch]
            
            if words_actually_removed:
                print(f"   ❌ ELIMINANDO {len(words_actually_removed)} palabras de este lote: {', '.join(words_actually_removed)}")
            else:
                print(f"   ✅ No se eliminó ninguna palabra de este lote")
            
            # Debug: show if API returned words not in batch
            words_not_in_batch = [word for word in words_to_remove if word not in words_batch]
            if words_not_in_batch:
                print(f"   ⚠️  API devolvió palabras que no están en este lote: {', '.join(words_not_in_batch)}")
            
            return result_dict
            
        except json.JSONDecodeError:
            print(f"Error parsing JSON response: {content}")
            return {word: False for word in words_batch}
            
    except Exception as e:
        print(f"Error calling DeepSeek API: {e}")
        return {word: False for word in words_batch}
    finally:
        # Close the session to ensure no connection reuse
        session.close()

def clean_dataset():
    print("🧹 Iniciando limpieza del dataset...")
    
    input_file = "/home/valentina/ai_chatbot_politiktok/backend/data/data.csv"
    output_file = "/home/valentina/ai_chatbot_politiktok/backend/data/data_new.csv"
    
    print(f"📖 Leyendo dataset desde: {input_file}")
    df = pd.read_csv(input_file)
    
    print(f"📊 Dataset original: {len(df)} palabras")
    
    unique_words = df['word'].unique().tolist()
    print(f"🔤 Palabras únicas: {len(unique_words)}")
    
    batch_size = 50
    words_to_remove = set()
    total_batches = (len(unique_words) + batch_size - 1) // batch_size
    
    print(f"🚀 Procesando en {total_batches} lotes de {batch_size} palabras...")
    
    for i in range(0, len(unique_words), batch_size):
        batch = unique_words[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        print(f"📦 Procesando lote {batch_num}/{total_batches} ({len(batch)} palabras)...")
        
        result = call_deepseek_api(batch)
        
        for word, should_remove in result.items():
            if should_remove:
                words_to_remove.add(word)
        
        removed_in_batch = sum(1 for should_remove in result.values() if should_remove)
        print(f"   📊 Total marcadas para eliminar en este lote: {removed_in_batch}")
        
        if batch_num < total_batches:
            print("⏳ Esperando 2 segundos antes del siguiente lote...")
            time.sleep(2)
    
    print(f"\n🗑️  Total de palabras marcadas para eliminar: {len(words_to_remove)}")
    
    if words_to_remove:
        print("📝 Palabras que serán eliminadas:")
        for word in sorted(list(words_to_remove)[:20]):
            print(f"   - {word}")
        if len(words_to_remove) > 20:
            print(f"   ... y {len(words_to_remove) - 20} más")
    
    cleaned_df = df[~df['word'].isin(words_to_remove)]
    
    print(f"\n📊 Dataset limpio: {len(cleaned_df)} filas (eliminadas: {len(df) - len(cleaned_df)})")
    
    print(f"💾 Guardando dataset limpio en: {output_file}")
    cleaned_df.to_csv(output_file, index=False)
    
    print("✅ ¡Limpieza completada!")
    
    return len(df), len(cleaned_df), len(words_to_remove)

def regenerate_final_output():
    print("\n🔄 Regenerando archivo final...")
    
    data_new_file = "/home/valentina/ai_chatbot_politiktok/backend/data/data_new.csv"
    final_output_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/final_tiktok_data_cleaned.csv"
    
    if not os.path.exists(data_new_file):
        print(f"❌ Error: No se encuentra {data_new_file}")
        return
    
    print(f"📖 Leyendo dataset limpio desde: {data_new_file}")
    df_new = pd.read_csv(data_new_file)
    
    print(f"💾 Copiando a archivo final: {final_output_file}")
    df_new.to_csv(final_output_file, index=False)
    
    print("✅ ¡Archivo final regenerado!")

if __name__ == "__main__":
    try:
        original_count, cleaned_count, removed_count = clean_dataset()
        
        print(f"\n📈 RESUMEN:")
        print(f"   📊 Filas originales: {original_count}")
        print(f"   ✅ Filas después de limpieza: {cleaned_count}")
        print(f"   🗑️  Filas eliminadas: {removed_count}")
        print(f"   📉 Porcentaje eliminado: {(removed_count / original_count * 100):.1f}%")
        
        regenerate_final_output()
        
    except Exception as e:
        print(f"❌ Error durante la limpieza: {e}")
        import traceback
        traceback.print_exc()
