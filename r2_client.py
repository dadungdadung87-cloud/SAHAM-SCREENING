# ==========================================
# R2 CLIENT - Jembatan ke Cloudflare R2 (S3-compatible)
# Dipakai oleh update_data.py (upload) dan app.py (download)
# ==========================================
import os
import json
import boto3
from botocore.client import Config

CONFIG_FILE = "r2_config.json"

def _load_credentials():
    # 1) Environment variables
    acc = os.environ.get("R2_ACCOUNT_ID")
    key = os.environ.get("R2_ACCESS_KEY_ID")
    sec = os.environ.get("R2_SECRET_ACCESS_KEY")
    bucket = os.environ.get("R2_BUCKET", "saham-arsip")
    if acc and key and sec:
        return acc, key, sec, bucket
    # 2) File config lokal (WAJIB di-gitignore)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                c = json.load(f)
            return c["account_id"], c["access_key_id"], c["secret_access_key"], c.get("bucket", "saham-arsip")
        except Exception:
            pass
    # 3) Streamlit secrets (untuk Codespaces)
    try:
        import streamlit as st
        s = st.secrets
        return s["R2_ACCOUNT_ID"], s["R2_ACCESS_KEY_ID"], s["R2_SECRET_ACCESS_KEY"], s.get("R2_BUCKET", "saham-arsip")
    except Exception:
        pass
    return None, None, None, None

def get_r2_client():
    acc, key, sec, bucket = _load_credentials()
    if not acc or not key or not sec:
        return None, None
    client = boto3.client(
        "s3",
        endpoint_url=f"https://{acc}.r2.cloudflarestorage.com",
        aws_access_key_id=key,
        aws_secret_access_key=sec,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
    return client, bucket

def upload_arsip(local_path, object_name):
    client, bucket = get_r2_client()
    if not client:
        print("⚠️ R2 belum dikonfigurasi, lewati upload.")
        return False
    client.upload_file(local_path, bucket, object_name)
    return True

def download_arsip(object_name, local_path):
    client, bucket = get_r2_client()
    if not client:
        return False
    try:
        client.download_file(bucket, object_name, local_path)
        return True
    except Exception:
        return False

def list_arsip():
    client, bucket = get_r2_client()
    if not client:
        return []
    try:
        resp = client.list_objects_v2(Bucket=bucket, Prefix="Arsip_Data_Harian/")
        return [item["Key"] for item in resp.get("Contents", [])]
    except Exception:
        return []

# ==========================================
# >>> BARU: BACKUP & RESTORE DATABASE (PORTOFOLIO) <<<
# ==========================================
def upload_database(mirror=False):
    """Upload CSV Database/ ke R2.
    
    Args:
        mirror: Jika True, R2 dijadikan cermin persis — file CSV yang terhapus
                di laptop juga akan terhapus di R2 (mencegah sinyal zombie).
    """
    import glob
    client, bucket = get_r2_client()
    if not client: return False
    try:
        # Kumpulkan semua file CSV lokal (kecuali cache)
        files_lokal = [f for f in glob.glob("Database/*.csv") 
                       if "cache_autopilot" not in os.path.basename(f)]
        nama_lokal = {os.path.basename(f) for f in files_lokal}
        
        # Upload semua file lokal ke R2
        for f in files_lokal:
            nama = os.path.basename(f)
            client.upload_file(f, bucket, f"Database/{nama}")
        
        # Mode mirror: hapus file di R2 yang sudah tidak ada di laptop
        if mirror:
            resp = client.list_objects_v2(Bucket=bucket, Prefix="Database/")
            for item in resp.get("Contents", []):
                nama_di_r2 = item["Key"].split("/")[-1]
                if nama_di_r2 not in nama_lokal:
                    try:
                        client.delete_object(Bucket=bucket, Key=item["Key"])
                        print(f"   🗑️ Mirror: {nama_di_r2} dihapus dari R2")
                    except Exception:
                        pass
        
        return len(files_lokal) > 0
    except Exception as e:
        print(f"⚠️ upload_database gagal: {e}")
        return False

def download_database():
    """Download seluruh CSV dari folder Database/ R2 ke lokal (restore)"""
    client, bucket = get_r2_client()
    if not client: return False
    try:
        os.makedirs("Database", exist_ok=True)
        resp = client.list_objects_v2(Bucket=bucket, Prefix="Database/")
        n = 0
        for item in resp.get("Contents", []):
            key = item["Key"]
            if key.endswith(".csv"):
                nama = key.split("/")[-1]
                if "cache_autopilot" in nama: continue
                client.download_file(bucket, key, os.path.join("Database", nama))
                n += 1
        return n > 0
    except Exception:
        return False