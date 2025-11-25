import argparse
import subprocess
import os
import sys
import hashlib
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from webflow.client import Webflow

# 1. Load Environment Variables
load_dotenv()

# Check for required Env Vars
if not os.getenv("WEBFLOW_API_TOKEN") or not os.getenv("SITE_ID"):
    print("Error: Missing .env file or WEBFLOW_API_TOKEN/SITE_ID variables.")
    sys.exit(1)

# Initialize Webflow client
webflow = Webflow(access_token=os.getenv("WEBFLOW_API_TOKEN"))

# --- Helper: Format Bytes to MB ---
def format_bytes(size):
    power = 2**20
    n = size / power
    return f"{n:.2f} MB"

# --- Section 1: Compression Logic ---
def compress_video(input_path, crf):
    input_path = Path(input_path)
    
    # Define output directory and path
    output_dir = Path("compressed")
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error: Could not create output directory {output_dir}: {e}")
        sys.exit(1)

    output_path = output_dir / input_path.with_suffix('.webm').name

    # Construct FFmpeg command (VP9/Opus)
    command = [
        "ffmpeg",
        "-y",                   # Overwrite output file without asking
        "-i", str(input_path),
        "-c:v", "libvpx-vp9",
        "-crf", str(crf),
        "-b:v", "0",
        "-b:a", "96k",
        "-c:a", "libopus",
        "-threads", "4",
        "-row-mt", "1",
        "-loglevel", "error",   # Reduce FFmpeg spam in console
        "-stats",               # Show progress stats
        str(output_path)
    ]

    print(f"🔄 Compressing: {input_path.name} -> {output_path.name} (CRF {crf})...")
    
    try:
        start_time = time.time()
        subprocess.run(command, check=True)
        elapsed = time.time() - start_time
        print(f"✅ Compression finished in {elapsed:.2f}s")
        return output_path
    except subprocess.CalledProcessError:
        print(f"\n❌ Error occurred during FFmpeg execution.")
        sys.exit(1)
    except FileNotFoundError:
        print("\n❌ Error: 'ffmpeg' command not found. Ensure FFmpeg is installed.")
        sys.exit(1)

# --- Section 2: Upload Logic ---

def create_asset_folder(site_id, folder_name):
    existing_folders = webflow.assets.list_folders(site_id)
    folders_list = existing_folders.asset_folders if hasattr(existing_folders, 'asset_folders') else existing_folders

    existing_folder = next(
        (folder for folder in folders_list
         if getattr(folder, 'display_name', None) == folder_name),
        None
    )

    if existing_folder:
        return existing_folder.id

    print(f"Creating Webflow folder: {folder_name}")
    response = webflow.assets.create_folder(site_id=site_id, display_name=folder_name)
    return response.id

def get_file_md5(path):
    hash_md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def poll_for_asset_url(site_id, asset_id, retries=20, delay=5):
    print(f"⏳ Polling Webflow Asset List (Max {retries*delay}s)...")
    
    for i in range(retries):
        try:
            response = webflow.assets.list(site_id)
            all_assets = response.assets if hasattr(response, 'assets') else response
            
            target_asset = next((a for a in all_assets if a.id == asset_id), None)
            
            if target_asset:
                url = getattr(target_asset, 'original_url', None) or \
                      getattr(target_asset, 'hosted_url', None) or \
                      getattr(target_asset, 'url', None)
                
                if url:
                    return url
                else:
                    print(f"   ...attempt {i+1}: Asset found, URL generating...")
            else:
                print(f"   ...attempt {i+1}: Asset ID not found in list yet.")
            
            time.sleep(delay)
        except Exception as e:
            print(f"   ...attempt {i+1} failed: {e}")
            time.sleep(delay)
    return None

def upload_local_asset(site_id, folder_id, file_path):
    try:
        file_name = os.path.basename(file_path)
        print(f"\n🚀 Preparing upload for: {file_name}")

        file_hash = get_file_md5(file_path)

        upload_init = webflow.assets.create(
            site_id=site_id,
            parent_folder=folder_id,
            file_name=file_name,
            file_hash=file_hash,
        )

        asset_id = upload_init.id
        upload_url = upload_init.upload_url
        d = upload_init.upload_details

        form_data = {
            "acl": d.acl, "bucket": d.bucket, "X-Amz-Algorithm": d.x_amz_algorithm,
            "X-Amz-Credential": d.x_amz_credential, "X-Amz-Date": d.x_amz_date,
            "key": d.key, "Policy": d.policy, "X-Amz-Signature": d.x_amz_signature,
            "success_action_status": d.success_action_status,
            "Content-Type": d.content_type, "Cache-Control": d.cache_control,
        }

        with open(file_path, "rb") as f:
            files = {"file": (file_name, f, d.content_type)}
            print(f"Uploading to S3...")
            upload_response = requests.post(upload_url, data=form_data, files=files)

        if upload_response.status_code == 201:
            print(f"✅ S3 Upload successful.")
            final_url = poll_for_asset_url(site_id, asset_id)            
            if final_url:
                print(f"\n🎉 SUCCESS! File Ready. CDN URL:")
                print("---------------------------------------------------")
                print(final_url)
                print("---------------------------------------------------")
            else:
                print("\n⚠️ Upload worked, but timed out waiting for URL.")
        else:
            print(f"❌ Failed to upload. Status: {upload_response.status_code}")

    except Exception as e:
        print(f"Error during upload: {e}")

# --- Section 3: Main Execution ---

def main():
    parser = argparse.ArgumentParser(description="Compress video then upload to Webflow.")
    parser.add_argument("input_file", help="The video file to convert")
    parser.add_argument("-crf", "--crf", type=int, required=True, help="The CRF quality value")
    args = parser.parse_args()

    # 1. Validate Input
    input_path = Path(args.input_file)
    if not input_path.is_file():
        print(f"Error: File '{args.input_file}' not found.")
        sys.exit(1)

    # 2. Run Compression
    compressed_path = compress_video(input_path, args.crf)

    # 3. Compare Sizes
    original_size = input_path.stat().st_size
    new_size = compressed_path.stat().st_size
    saved_percent = ((original_size - new_size) / original_size) * 100

    print("\n--- Size Comparison ---")
    print(f"Original:   {format_bytes(original_size)}")
    print(f"Compressed: {format_bytes(new_size)}")
    print(f"Reduction:  {saved_percent:.1f}%")
    
    # 4. Ask User for Confirmation
    confirm = input(f"\nDo you want to upload '{compressed_path.name}' to Webflow? (Y/n): ").strip().lower()
    
    if confirm == 'y' or confirm == '':
        site_id = os.getenv("SITE_ID")
        folder_name = "Video Uploads"
        
        # Get or Create Folder
        folder_id = create_asset_folder(site_id, folder_name)
        
        # Upload
        if folder_id:
            upload_local_asset(site_id, folder_id, compressed_path)
    else:
        print("❌ Upload cancelled by user.")

if __name__ == "__main__":
    main()