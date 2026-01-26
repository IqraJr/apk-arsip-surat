import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFrame, QLabel, QStackedWidget, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from src.kode_surat import ManajemenKodeSurat

# Import komponen dari folder src
from src import connect_db, Dashboard, SuratMasuk, SuratKeluar, KelolaDokumen
# PASTIKAN FILE kode_surat.py SUDAH ADA DI FOLDER src
from src.kode_surat import ManajemenKodeSurat 

class AplikasiUtama(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistem Manajemen Arsip Digital Surat")
        self.resize(1200, 800)

        # Cek Koneksi Database (SQLite)
        db = connect_db()
        if not db:
            QMessageBox.critical(self, "Error Database", "Gagal menginisialisasi database lokal!")
            sys.exit()
        db.close() 

        self.setup_ui()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.layout_utama = QHBoxLayout(main_widget)
        self.layout_utama.setContentsMargins(0, 0, 0, 0)
        self.layout_utama.setSpacing(0)

        # --- SIDEBAR ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(260)
        self.sidebar.setStyleSheet("background-color: #2c3e50;")
        self.layout_utama.addWidget(self.sidebar)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 10, 0, 10)
        sidebar_layout.setSpacing(5)

        logo_label = QLabel("SI-PENGARSIP")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("color: white; font-size: 22px; font-weight: bold; padding: 30px;")
        sidebar_layout.addWidget(logo_label)

        # Daftar Menu Navigasi (Tambahkan Kode Surat di Sini)
        # Urutan Index: 0:Dash, 1:Masuk, 2:Keluar, 3:Dokumen, 4:Kode Surat
        self.menus = [
            ("🏠   Dashboard", 0),
            ("📥   Surat Masuk", 1),
            ("📤   Surat Keluar", 2),
            ("📁   Kelola Dokumen", 3),
            ("🔖   Kode Surat", 4), # MENU BARU
        ]

        for text, index in self.menus:
            btn = QPushButton(text)
            btn.setFixedHeight(55)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self.get_menu_style())
            # Menggunakan default value idx=index untuk menghindari bug closure
            btn.clicked.connect(lambda checked, idx=index: self.ganti_halaman(idx))
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        btn_keluar = QPushButton("🚪   Keluar")
        btn_keluar.setFixedHeight(55)
        btn_keluar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_keluar.setStyleSheet(self.get_menu_style(is_exit=True))
        btn_keluar.clicked.connect(self.close)
        sidebar_layout.addWidget(btn_keluar)

        # --- AREA KONTEN ---
        self.halaman_konten = QStackedWidget()
        self.halaman_konten.setStyleSheet("background-color: #f8f9fa; border-top-left-radius: 20px; border: none;")
        self.layout_utama.addWidget(self.halaman_konten)

        self.init_halaman()

    def init_halaman(self):
        # Tambahkan widget ke stacked widget sesuai urutan index di self.menus
        self.halaman_konten.addWidget(Dashboard())          # Index 0
        self.halaman_konten.addWidget(SuratMasuk())         # Index 1
        self.halaman_konten.addWidget(SuratKeluar())        # Index 2
        self.halaman_konten.addWidget(KelolaDokumen())      # Index 3
        self.halaman_konten.addWidget(ManajemenKodeSurat()) # Index 4 (WIDGET BARU)

    def ganti_halaman(self, index):
        self.halaman_konten.setCurrentIndex(index)
        current_widget = self.halaman_konten.currentWidget()
        
        # Refresh data saat halaman dibuka
        if hasattr(current_widget, 'load_data'):
            current_widget.load_data()
            
        if hasattr(current_widget, 'refresh_data'):
            current_widget.refresh_data()

    def get_menu_style(self, is_exit=False):
        bg_hover = "#e74c3c" if is_exit else "#1abc9c"
        return f"""
            QPushButton {{
                background-color: transparent; color: white; border: none;
                text-align: left; padding-left: 30px; font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {bg_hover};
            }}
        """

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = AplikasiUtama()
    window.show()
    sys.exit(app.exec())