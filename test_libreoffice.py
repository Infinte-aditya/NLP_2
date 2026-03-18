import os
import subprocess
import tempfile
import shutil

SOFFICE_PATH = r"C:\Program Files\LibreOffice\program\soffice.exe"

def _kill_stale_soffice():
    try:
        subprocess.run(["taskkill", "/F", "/IM", "soffice.bin"], capture_output=True, timeout=5)
    except: pass

def test_conversion(docx_path, pdf_path):
    output_dir = os.path.dirname(pdf_path) or "."
    os.makedirs(output_dir, exist_ok=True)
    abs_docx = os.path.abspath(docx_path)
    abs_outdir = os.path.abspath(output_dir)
    _kill_stale_soffice()
    tmp_profile = tempfile.mkdtemp(prefix="soffice_profile_")
    profile_url = "file:///" + tmp_profile.replace("\\", "/")
    
    cmd = [
        SOFFICE_PATH,
        f"-env:UserInstallation={profile_url}",
        "--headless",
        "--norestore",
        "--nolockcheck",
        "--convert-to", "pdf",
        "--outdir", abs_outdir,
        abs_docx
    ]
    
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"Return code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        shutil.rmtree(tmp_profile, ignore_errors=True)

if __name__ == "__main__":
    # Create a dummy docx if none exists or use an existing one
    dummy_docx = "test_dummy.docx"
    # Actually, I saw 'Sample Input File English.docx' in the uploads directory
    source = os.path.join("uploads", "Sample Input File English.docx")
    if os.path.exists(source):
        test_conversion(source, "test_output.pdf")
    else:
        print(f"{source} not found")
