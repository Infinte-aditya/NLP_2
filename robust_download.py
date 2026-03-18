import os
from huggingface_hub import snapshot_download

# Ensure backend can be imported
MODEL_NAME = "facebook/nllb-200-distilled-600M"

print(f"Starting robust download of {MODEL_NAME}...")
print("This will download approximately 1.2GB of data. Please wait...")

try:
    # This will download the entire repository to the default cache location
    # and handle retries/resumes correctly.
    download_path = snapshot_download(
        repo_id=MODEL_NAME,
        repo_type="model",
        library_name="transformers",
        resume_download=True
    )
    print(f"\nSUCCESS: Model downloaded to: {download_path}")
    print("The backend should now start instantly.")
except Exception as e:
    print(f"\nERROR during download: {e}")
    import traceback
    traceback.print_exc()
