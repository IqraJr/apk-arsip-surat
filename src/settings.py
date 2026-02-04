import os
import json
import sys

CONFIG_FILE = "config.json"

# --- PERBAIKAN LOGIKA PATH ---
# Mengambil lokasi file ini berada, lalu naik satu folder ke atas (ke root project)
if getattr(sys, 'frozen', False):
    # Jika dijalankan sebagai .exe
    base_dir = os.path.dirname(sys.executable)
else:
    # Jika dijalankan sebagai script .py (settings.py ada di dalam folder src)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Path default selalu mengarah ke folder 'uploads' di dalam project
DEFAULT_BASE = os.path.join(base_dir, "uploads")

def get_folder_path(kategori):
    """
    Mengambil path berdasarkan kategori ('masuk' atau 'keluar').
    """
    default_path = os.path.join(DEFAULT_BASE, f"surat_{kategori}")
    
    # Pastikan config.json juga dibaca dari folder yang benar
    config_path = os.path.join(base_dir, CONFIG_FILE)
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
                return data.get(f"path_{kategori}", default_path)
        except Exception:
            return default_path
    return default_path

def set_folder_path(kategori, new_path):
    """
    Menyimpan path baru untuk kategori tertentu.
    """
    config_path = os.path.join(base_dir, CONFIG_FILE)
    data = {}
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
        except:
            data = {}

    data[f"path_{kategori}"] = new_path
    
    with open(config_path, 'w') as f:
        json.dump(data, f, indent=4)