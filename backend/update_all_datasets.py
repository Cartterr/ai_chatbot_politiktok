#!/usr/bin/env python3

import pandas as pd
import os

def update_all_datasets():
    """Update user types in ALL relevant datasets"""
    
    # Define user type mappings
    user_type_updates = {
        "bsepulvedahales": "Política formal",
        "crisreal94": "Política formal", 
        "elseadev": "Política formal",
        "entretv60": "Política formal",
        "ignacia..benitez": "Política formal",
        "julietamartinezo": "Derechos de la Naturaleza",
        "rod.jav": "Política formal",
        "periodistaencrisis": "Política formal",
        "rosette.sg": "Discapacidad y capacitismo",
        "sailor.comunista": "Política formal",
        "sanatimea": "Política formal",
        "track3.chile": "Política formal",
        "tremendascl": "Derechos de la Naturaleza",
        "vickyestuvoaqui": "Política formal"
    }
    
    # Users to remove completely
    users_to_remove = {
        "bycamilisima",
        "cata.byb", 
        "isabelsaieg",
        "isicardemil",
        "kaysaud"
    }
    
    print("🔄 Updating ALL datasets with user type changes...")
    
    # List of datasets to update
    datasets_to_update = [
        "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/ultimate_temporal_dataset.csv",
        "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/main_tiktok_data_clean.csv",
        "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/combined_tiktok_data_with_dates_clean.csv",
        "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/main_tiktok_data_smart_filtered.csv"
    ]
    
    total_updates = 0
    total_removals = 0
    
    for dataset_path in datasets_to_update:
        if not os.path.exists(dataset_path):
            print(f"⚠️  Dataset not found: {dataset_path}")
            continue
            
        dataset_name = os.path.basename(dataset_path)
        print(f"\n📊 Processing: {dataset_name}")
        
        try:
            # Load dataset
            df = pd.read_csv(dataset_path, low_memory=False)
            print(f"✅ Loaded: {len(df):,} rows")
            
            original_count = len(df)
            dataset_updates = 0
            dataset_removals = 0
            
            # Apply user type updates
            for username, new_user_type in user_type_updates.items():
                if 'username' in df.columns and 'user_type' in df.columns:
                    mask = df['username'] == username
                    if mask.any():
                        old_type = df.loc[mask, 'user_type'].iloc[0]
                        df.loc[mask, 'user_type'] = new_user_type
                        affected_rows = mask.sum()
                        print(f"   ✏️  {username}: {affected_rows} rows updated to '{new_user_type}'")
                        dataset_updates += affected_rows
                else:
                    print(f"   ⚠️  No username/user_type columns found")
                    break
            
            # Remove specified users
            for username in users_to_remove:
                if 'username' in df.columns:
                    mask = df['username'] == username
                    rows_to_remove = mask.sum()
                    if rows_to_remove > 0:
                        df = df[~mask]
                        print(f"   ❌ Removed {rows_to_remove} rows from: {username}")
                        dataset_removals += rows_to_remove
            
            # Save updated dataset
            if dataset_updates > 0 or dataset_removals > 0:
                # Create backup
                backup_path = dataset_path.replace('.csv', '_updated_backup.csv')
                original_df = pd.read_csv(dataset_path, low_memory=False)
                original_df.to_csv(backup_path, index=False)
                
                # Save updated version
                df.to_csv(dataset_path, index=False)
                print(f"   💾 Updated: {len(df):,} rows (was {original_count:,})")
                print(f"   📦 Backup: {os.path.basename(backup_path)}")
                
                total_updates += dataset_updates
                total_removals += dataset_removals
            else:
                print(f"   ✅ No changes needed")
                
        except Exception as e:
            print(f"   ❌ Error processing {dataset_name}: {str(e)}")
    
    print(f"\n📊 FINAL SUMMARY:")
    print(f"   ✏️  Total user type updates: {total_updates}")
    print(f"   ❌ Total rows removed: {total_removals}")
    print(f"   📁 Datasets processed: {len(datasets_to_update)}")
    
    # Verify the ultimate dataset
    print(f"\n🔍 VERIFYING ULTIMATE DATASET:")
    ultimate_path = "/home/valentina/ai_chatbot_politiktok/backend/data/output/clean/ultimate_temporal_dataset.csv"
    try:
        df_ultimate = pd.read_csv(ultimate_path, low_memory=False)
        print(f"   📊 Ultimate dataset: {len(df_ultimate):,} rows")
        
        if 'user_type' in df_ultimate.columns:
            user_type_counts = df_ultimate['user_type'].value_counts()
            print(f"   📈 User type distribution:")
            for user_type, count in user_type_counts.head(8).items():
                print(f"      • {user_type}: {count:,}")
        
        # Check some updated users
        print(f"   🔍 Sample updated users:")
        for username in list(user_type_updates.keys())[:3]:
            user_data = df_ultimate[df_ultimate['username'] == username]
            if not user_data.empty:
                user_type = user_data['user_type'].iloc[0]
                count = len(user_data)
                print(f"      • @{username}: {user_type} ({count} videos)")
            else:
                print(f"      • @{username}: not found in ultimate dataset")
                
    except Exception as e:
        print(f"   ❌ Error verifying ultimate dataset: {str(e)}")
    
    print(f"\n🎉 ALL DATASETS UPDATED!")
    print(f"✅ User types updated across all relevant datasets")
    print(f"✅ Specified users removed from all datasets") 
    print(f"✅ Backups created for all modified files")

if __name__ == "__main__":
    update_all_datasets()
