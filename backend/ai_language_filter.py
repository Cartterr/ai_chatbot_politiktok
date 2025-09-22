#!/usr/bin/env python3

import pandas as pd
import httpx
import json
import logging
import os
import asyncio
import time
from typing import Optional, Dict, Any
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_language_filter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OllamaLanguageFilter:
    def __init__(self):
        self.setup_ollama_connection()
        self.model = "mistral:latest"  # Using Mistral for better classification performance
        self.processed_count = 0
        self.spanish_count = 0
        self.non_spanish_count = 0

        # File paths
        self.input_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/final_tiktok_data_fixed.csv"
        self.spanish_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/final_spanish_videos.csv"
        self.non_spanish_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/removed_non_spanish_videos.csv"
        self.progress_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/filter_progress.json"

        # Resume capability
        self.last_processed_index = self.load_progress()

    def setup_ollama_connection(self):
        """Setup Ollama connection using EXACT same logic as ollama_client.py"""
        # Use EXACT same logic as ollama_client.py
        OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL")
        
        if OLLAMA_BASE_URL:
            self.ollama_api_base = f"{OLLAMA_BASE_URL}/api"
            logger.info(f"Using Ollama Base URL from environment: {self.ollama_api_base}")
        else:
            import subprocess
            try:
                result = subprocess.run(['ip', 'route', 'show'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'default' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            WINDOWS_HOST_IP = parts[2]
                            break
                else:
                    WINDOWS_HOST_IP = "172.28.80.1"
            except:
                WINDOWS_HOST_IP = "172.28.80.1"
            
            self.ollama_api_base = f"http://{WINDOWS_HOST_IP}:11434/api"
            logger.info(f"Using fallback Ollama Base URL: {self.ollama_api_base}")
        
        # Allow further overriding via OLLAMA_API_BASE environment variable
        self.ollama_api_base = os.environ.get("OLLAMA_API_BASE", self.ollama_api_base)
        logger.info(f"Final Ollama Base URL: {self.ollama_api_base}")

    async def test_connection(self):
        """Test connection to Ollama"""
        url = f"{self.ollama_api_base}/tags"
        logger.info(f"🔌 Testing connection to Ollama: {url}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                models = response.json().get("models", [])
                logger.info(f"✅ Successfully connected to Ollama!")
                logger.info(f"📚 Found {len(models)} available models:")

                model_found = False
                for model in models:
                    model_name = model.get('name', '')
                    logger.info(f"   • {model_name}")
                    if self.model in model_name:
                        model_found = True
                        logger.info(f"   ✅ Target model {self.model} found!")

                if not model_found:
                    logger.warning(f"⚠️  Target model {self.model} not found. Available models listed above.")
                    return False

                return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to Ollama: {str(e)}")
            return False

    async def classify_language(self, title: str, transcription: str) -> str:
        """Use AI to classify if video content is in Spanish or English"""

        # Prepare content for analysis
        content_parts = []
        if pd.notna(title) and str(title).strip():
            content_parts.append(f"TITLE: {str(title).strip()}")
        if pd.notna(transcription) and str(transcription).strip():
            # Truncate very long transcriptions to avoid token limits
            trans_text = str(transcription).strip()
            if len(trans_text) > 1000:
                trans_text = trans_text[:1000] + "..."
            content_parts.append(f"TRANSCRIPTION: {trans_text}")

        if not content_parts:
            return "UNKNOWN"

        content = "\n".join(content_parts)

        # Create a very direct prompt for Spanish detection
        prompt = f"""Task: Determine if this text is in Spanish language.

Text: {content}

Rules:
1. Ignore hashtags and @mentions
2. Look at the actual words and grammar
3. Spanish uses words like: que, de, la, el, en, y, es, no, con, para, como, pero, muy, todo, mas, etc.
4. Spanish has patterns like: -ando, -iendo, -ción, -dad endings
5. If text is primarily Spanish = answer SPANISH
6. If text is English, Portuguese, French, or any other language = answer NOT_SPANISH
7. If unclear/gibberish = answer NOT_SPANISH

Answer only: SPANISH or NOT_SPANISH"""

        try:
            url = f"{self.ollama_api_base}/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,  # Deterministic for consistent classification
                    "top_p": 0.05,       # Even more focused
                    "top_k": 1,          # Only best option
                    "num_predict": 3     # Very short response expected
                }
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()
                ai_response = result.get("response", "").strip().upper()

                # Extract the classification from AI response
                if "SPANISH" in ai_response:
                    return "SPANISH"
                else:
                    return "NOT_SPANISH"

        except Exception as e:
            logger.error(f"Error classifying content: {str(e)}")
            return "ERROR"

    def load_progress(self) -> int:
        """Load progress from previous run"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r') as f:
                    progress = json.load(f)
                    last_index = progress.get('last_processed_index', -1)
                    logger.info(f"📂 Resuming from index {last_index + 1}")
                    return last_index
        except Exception as e:
            logger.warning(f"Could not load progress: {e}")
        return -1

    def save_progress(self, index: int):
        """Save current progress"""
        try:
            progress = {
                'last_processed_index': index,
                'processed_count': self.processed_count,
                'spanish_count': self.spanish_count,
                'non_spanish_count': self.non_spanish_count,
                'timestamp': time.time()
            }
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save progress: {e}")

    def initialize_output_files(self, df_columns):
        """Initialize output CSV files with headers if they don't exist"""
        for file_path in [self.spanish_file, self.non_spanish_file]:
            if not os.path.exists(file_path):
                # Create empty DataFrame with same columns and save
                empty_df = pd.DataFrame(columns=df_columns)
                empty_df.to_csv(file_path, index=False)
                logger.info(f"📄 Created output file: {file_path}")

    async def process_dataset(self):
        """Process the entire dataset row by row"""
        logger.info("🚀 Starting AI language filtering process...")

        # Test connection first
        if not await self.test_connection():
            logger.error("❌ Cannot connect to Ollama. Please check your setup.")
            return

        # Load dataset
        logger.info(f"📊 Loading dataset: {self.input_file}")
        df = pd.read_csv(self.input_file, low_memory=False)
        total_rows = len(df)
        logger.info(f"📹 Total videos to process: {total_rows:,}")

        # Initialize output files
        self.initialize_output_files(df.columns)

        # Start processing from last checkpoint
        start_index = self.last_processed_index + 1
        logger.info(f"🔄 Starting processing from index {start_index}")

        spanish_batch = []
        non_spanish_batch = []
        batch_size = 10  # Save in batches to avoid memory issues

        for index, row in df.iterrows():
            if index < start_index:
                continue

            self.processed_count += 1

            # Get title and transcription
            title = row.get('title', '')
            transcription = row.get('transcription', '')
            username = row.get('username', 'unknown')

            logger.info(f"\n📹 Processing {self.processed_count}/{total_rows - start_index} - @{username}")
            logger.info(f"   📝 Title: {str(title)[:60]}{'...' if len(str(title)) > 60 else ''}")

            # Classify language using AI
            classification = await self.classify_language(title, transcription)

            if classification == "SPANISH":
                spanish_batch.append(row)
                self.spanish_count += 1
                logger.info(f"   ✅ SPANISH - Added to Spanish dataset")
            else:
                # NOT_SPANISH, UNKNOWN, or ERROR - remove from Spanish dataset
                non_spanish_batch.append(row)
                self.non_spanish_count += 1
                logger.info(f"   ❌ NOT SPANISH ({classification}) - Removed from dataset")

            # Save batches periodically
            if len(spanish_batch) >= batch_size:
                self.save_batch(spanish_batch, self.spanish_file)
                spanish_batch = []
            
            if len(non_spanish_batch) >= batch_size:
                self.save_batch(non_spanish_batch, self.non_spanish_file)
                non_spanish_batch = []

            # Save progress every 10 videos
            if self.processed_count % 10 == 0:
                self.save_progress(index)
                logger.info(f"💾 Progress saved - Spanish: {self.spanish_count}, Non-Spanish: {self.non_spanish_count}")

            # Small delay to avoid overwhelming the AI
            await asyncio.sleep(0.1)

        # Save remaining batches
        if spanish_batch:
            self.save_batch(spanish_batch, self.spanish_file)
        if non_spanish_batch:
            self.save_batch(non_spanish_batch, self.non_spanish_file)

        # Final save
        self.save_progress(total_rows - 1)

        # Summary
        logger.info(f"\n🎉 FILTERING COMPLETE!")
        logger.info(f"   📊 Total processed: {self.processed_count:,}")
        logger.info(f"   ✅ Spanish videos: {self.spanish_count:,}")
        logger.info(f"   ❌ Non-Spanish videos: {self.non_spanish_count:,}")
        logger.info(f"   📈 Spanish retention: {(self.spanish_count/self.processed_count)*100:.1f}%")
        logger.info(f"   📁 Spanish dataset: {self.spanish_file}")
        logger.info(f"   📁 Non-Spanish dataset: {self.non_spanish_file}")

    def save_batch(self, batch_data, file_path):
        """Save a batch of data to CSV file"""
        if not batch_data:
            return

        try:
            # Convert list of Series to DataFrame
            batch_df = pd.DataFrame(batch_data)

            # Append to existing file
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                batch_df.to_csv(file_path, mode='a', header=False, index=False)
            else:
                batch_df.to_csv(file_path, mode='w', header=True, index=False)

            logger.info(f"💾 Saved batch of {len(batch_data)} videos to {os.path.basename(file_path)}")
        except Exception as e:
            logger.error(f"Error saving batch: {e}")

async def main():
    """Main function to run the language filter"""
    filter_processor = OllamaLanguageFilter()

    try:
        await filter_processor.process_dataset()
    except KeyboardInterrupt:
        logger.info("\n⏸️  Process interrupted by user. Progress has been saved.")
        logger.info("   Run the script again to resume from where you left off.")
    except Exception as e:
        logger.error(f"❌ Error during processing: {str(e)}", exc_info=True)

if __name__ == "__main__":
    print("🤖 AI Language Filter for TikTok Videos")
    print("=" * 50)
    print("This script will process each video and keep ONLY Spanish content")
    print("using your local Ollama AI (gemma3:4b) - removes ALL non-Spanish videos")
    print("\nPress Ctrl+C to stop at any time - progress will be saved!")
    print("=" * 50)

    asyncio.run(main())
