# src/__init__.py

# Memudahkan import sehingga di main.py cukup: from src import Dashboard
from .db_manager import connect_db
from .dashboard import Dashboard
from .surat_masuk import SuratMasuk
from .surat_keluar import SuratKeluar
from .dokumen import KelolaDokumen

# Mendefinisikan apa saja yang tersedia saat menggunakan 'from src import *'
__all__ = ['connect_db', 'Dashboard', 'SuratMasuk', 'SuratKeluar', 'KelolaDokumen']

