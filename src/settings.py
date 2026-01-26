import os
import json

CONFIG_FILE = "config.json"

# Default path relative terhadap aplikasi
DEFAULT_BASE = os.path.join(os.getcwd(), "uploads")

def get_folder_path(kategori):
    """
    Mengambil path berdasarkan kategori ('masuk' atau 'keluar').
    """
    default_path = os.path.join(DEFAULT_BASE, f"surat_{kategori}")
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                # Ambil path spesifik, jika tidak ada, gunakan default
                return data.get(f"path_{kategori}", default_path)
        except Exception:
            return default_path
    return default_path

def set_folder_path(kategori, new_path):
    """
    Menyimpan path baru untuk kategori tertentu.
    """
    data = {}
    # Baca data lama dulu agar settingan lain tidak hilang
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
        except:
            data = {}

    # Update path untuk kategori tersebut
    data[f"path_{kategori}"] = new_path
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)