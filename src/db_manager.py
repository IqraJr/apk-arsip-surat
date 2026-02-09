import sqlite3
import os
import sys

def connect_db():
    try:
        # Menentukan lokasi database agar selalu di samping file utama aplikasi
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            # Jika file ini ada di dalam folder 'src', naik satu tingkat
            if os.path.basename(base_path) == 'src':
                base_path = os.path.dirname(base_path)

        db_path = os.path.join(base_path, "arsip_digital.db")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # --- PERBAIKAN DI SINI ---
        
        # 1. Buat Tabel Surat (Eksekusi Sendiri)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS surat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nomor_surat TEXT,
                judul_surat TEXT,
                asal_surat TEXT,
                kategori TEXT,
                tanggal TEXT,        -- Tanggal Terima/Kirim
                tanggal_surat TEXT,  -- Tanggal asli di Fisik Surat
                keterangan TEXT,
                file_path TEXT
            )
        """)

        # 2. Buat Tabel Kode Surat (Eksekusi Sendiri)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kode_surat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kode TEXT NOT NULL,
                keterangan TEXT NOT NULL UNIQUE
            )
        """)
        
        conn.commit()
        return conn
    except Exception as e:
        print(f"Error Database SQLite: {e}")
        return None