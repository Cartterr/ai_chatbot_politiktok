#!/usr/bin/env python3

import pandas as pd
import fasttext
import logging
import os
import json
import time
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fasttext_language_filter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FastTextLanguageFilter:
    def __init__(self):
        self.model = None
        self.load_model()
        self.processed_count = 0
        self.spanish_count = 0
        self.non_spanish_count = 0
        
        # File paths
        self.input_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/final_tiktok_data_fixed.csv"
        self.spanish_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/final_spanish_videos.csv"
        self.non_spanish_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/removed_non_spanish_videos.csv"
        self.progress_file = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/fasttext_filter_progress.json"
        
        # Resume capability
        self.last_processed_index = self.load_progress()

    def load_model(self):
        """Load the fastText language identification model"""
        model_path = "/home/valentina/ai_chatbot_politiktok/backend/lid.176.bin"
        
        if not os.path.exists(model_path):
            logger.error(f"❌ FastText model not found at {model_path}")
            logger.info("Please download it with: wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin")
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        logger.info(f"📚 Loading FastText model from {model_path}")
        self.model = fasttext.load_model(model_path)
        logger.info("✅ FastText model loaded successfully!")

    def detect_language(self, text):
        """Detect language using FastText with confidence score"""
        if not text or pd.isna(text) or str(text).strip() == "":
            return "unknown", 0.0
        
        # Clean text for fastText (single line, no special chars that might confuse)
        clean_text = str(text).replace('\n', ' ').replace('\r', ' ').strip()
        if len(clean_text) < 3:  # Too short to reliably detect
            return "unknown", 0.0
        
        try:
            # Predict language (k=1 returns top prediction)
            predictions = self.model.predict(clean_text, k=1)
            language_code = predictions[0][0].replace('__label__', '')
            confidence = predictions[1][0]
            
            return language_code, confidence
        except Exception as e:
            logger.warning(f"Error detecting language for text: {str(e)}")
            return "error", 0.0

    def classify_content(self, title, transcription):
        """Classify video content as Spanish or not Spanish"""
        
        # Collect all text content
        content_parts = []
        if pd.notna(title) and str(title).strip():
            content_parts.append(str(title).strip())
        if pd.notna(transcription) and str(transcription).strip():
            # Truncate very long transcriptions
            trans_text = str(transcription).strip()
            if len(trans_text) > 1000:
                trans_text = trans_text[:1000]
            content_parts.append(trans_text)
        
        if not content_parts:
            return "NO_CONTENT", 0.0, "No content to analyze"
        
        # Combine all content
        combined_text = " ".join(content_parts)
        
        # Detect language
        language_code, confidence = self.detect_language(combined_text)
        
        # Determine if Spanish
        is_spanish = language_code == "es" and confidence > 0.3  # Minimum confidence threshold
        
        classification = "SPANISH" if is_spanish else "NOT_SPANISH"
        details = f"Detected: {language_code} (confidence: {confidence:.3f})"
        
        return classification, confidence, details

    def load_progress(self):
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

    def save_progress(self, index):
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
                empty_df = pd.DataFrame(columns=df_columns)
                empty_df.to_csv(file_path, index=False)
                logger.info(f"📄 Created output file: {file_path}")

    def save_batch(self, batch_data, file_path):
        """Save a batch of data to CSV file"""
        if not batch_data:
            return
            
        try:
            batch_df = pd.DataFrame(batch_data)
            
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                batch_df.to_csv(file_path, mode='a', header=False, index=False)
            else:
                batch_df.to_csv(file_path, mode='w', header=True, index=False)
                
            logger.info(f"💾 Saved batch of {len(batch_data)} videos to {os.path.basename(file_path)}")
        except Exception as e:
            logger.error(f"Error saving batch: {e}")

    def process_dataset(self):
        """Process the entire dataset row by row"""
        logger.info("🚀 Starting FastText language filtering process...")
        
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
        batch_size = 50  # Larger batch size since FastText is much faster
        
        for index, row in df.iterrows():
            if index < start_index:
                continue
                
            self.processed_count += 1
            
            # Get title and transcription
            title = row.get('title', '')
            transcription = row.get('transcription', '')
            username = row.get('username', 'unknown')
            
            logger.info(f"\n📹 Processing {self.processed_count}/{total_rows - start_index} - @{username}")
            
            # Classify language using FastText
            classification, confidence, details = self.classify_content(title, transcription)
            
            if classification == "SPANISH":
                spanish_batch.append(row)
                self.spanish_count += 1
                logger.info(f"   ✅ SPANISH - {details}")
            else:
                non_spanish_batch.append(row)
                self.non_spanish_count += 1
                logger.info(f"   ❌ NOT SPANISH - {details}")
            
            # Save batches periodically
            if len(spanish_batch) >= batch_size:
                self.save_batch(spanish_batch, self.spanish_file)
                spanish_batch = []
            
            if len(non_spanish_batch) >= batch_size:
                self.save_batch(non_spanish_batch, self.non_spanish_file)
                non_spanish_batch = []
            
            # Save progress every 100 videos (faster processing)
            if self.processed_count % 100 == 0:
                self.save_progress(index)
                retention_pct = (self.spanish_count / self.processed_count) * 100
                logger.info(f"💾 Progress saved - Spanish: {self.spanish_count}, Non-Spanish: {self.non_spanish_count} ({retention_pct:.1f}% Spanish)")
        
        # Save remaining batches
        if spanish_batch:
            self.save_batch(spanish_batch, self.spanish_file)
        if non_spanish_batch:
            self.save_batch(non_spanish_batch, self.non_spanish_file)
        
        # Final save
        self.save_progress(total_rows - 1)
        
        # Summary
        retention_pct = (self.spanish_count / self.processed_count) * 100 if self.processed_count > 0 else 0
        logger.info(f"\n🎉 FILTERING COMPLETE!")
        logger.info(f"   📊 Total processed: {self.processed_count:,}")
        logger.info(f"   ✅ Spanish videos: {self.spanish_count:,}")
        logger.info(f"   ❌ Non-Spanish videos: {self.non_spanish_count:,}")
        logger.info(f"   📈 Spanish retention: {retention_pct:.1f}%")
        logger.info(f"   📁 Spanish dataset: {self.spanish_file}")
        logger.info(f"   📁 Non-Spanish dataset: {self.non_spanish_file}")

def main():
    """Main function to run the language filter"""
    filter_processor = FastTextLanguageFilter()
    
    try:
        filter_processor.process_dataset()
    except KeyboardInterrupt:
        logger.info("\n⏸️  Process interrupted by user. Progress has been saved.")
        logger.info("   Run the script again to resume from where you left off.")
    except Exception as e:
        logger.error(f"❌ Error during processing: {str(e)}", exc_info=True)

if __name__ == "__main__":
    print("🚀 FastText Language Filter for TikTok Videos")
    print("=" * 50)
    print("This script uses FastText AI to accurately detect Spanish content")
    print("and filter out ALL non-Spanish videos (English, Portuguese, etc.)")
    print("\nPress Ctrl+C to stop at any time - progress will be saved!")
    print("=" * 50)
    
    main()
