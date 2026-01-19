# src/dokumen.py
import os
import shutil
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QMessageBox, 
                             QFrame, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt
from .db_manager import connect_db

class KelolaDokumen(QWidget):
    def __init__(self):
        super().__init__()
        self.files_asal = [] 
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(15)

        # --- HEADER ---
        header = QLabel("📁 Manajer Dokumen Digital")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #1a1a2e;")
        self.main_layout.addWidget(header)

        # --- CONTAINER FORM (INPUT) ---
        self.card_frame = QFrame()
        self.card_frame.setStyleSheet("background-color: white; border-radius: 12px; border: 1px solid #dfe6e9;")
        card_layout = QVBoxLayout(self.card_frame)
        
        row_input = QHBoxLayout()
        # Input Judul
        v_box_judul = QVBoxLayout()
        v_box_judul.addWidget(QLabel("<b>Nama Folder / Kelompok Dokumen:</b>", styleSheet="border:none; color: black;"))
        self.ent_judul = QLineEdit()
        self.ent_judul.setPlaceholderText("Contoh: Laporan Keuangan 2025")
        self.ent_judul.setStyleSheet("padding: 10px; border: 1px solid #bdc3c7; border-radius: 6px; color: black;")
        v_box_judul.addWidget(self.ent_judul)
        row_input.addLayout(v_box_judul, 2)

        # Pilih File
        v_box_file = QVBoxLayout()
        v_box_file.addWidget(QLabel("<b>Pilih File:</b>", styleSheet="border:none; color: black;"))
        btn_lay = QHBoxLayout()
        self.btn_pilih = QPushButton("📁 Pilih Dokumen")
        self.btn_pilih.setStyleSheet("background-color: #f1f2f6; padding: 10px; font-weight: bold; border-radius: 6px; color: black;")
        self.btn_pilih.clicked.connect(self.pilih_file)
        btn_lay.addWidget(self.btn_pilih)
        self.lbl_path = QLabel("0 file dipilih")
        self.lbl_path.setStyleSheet("border:none; color: #7f8c8d; font-style: italic;")
        btn_lay.addWidget(self.lbl_path)
        v_box_file.addLayout(btn_lay)
        row_input.addLayout(v_box_file, 3)

        card_layout.addLayout(row_input)

        self.btn_simpan = QPushButton("🚀 Unggah & Simpan Kelompok Dokumen")
        self.btn_simpan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_simpan.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 12px; border-radius: 8px; border: none;")
        self.btn_simpan.clicked.connect(self.simpan_dokumen)
        card_layout.addWidget(self.btn_simpan)

        self.main_layout.addWidget(self.card_frame)

        # --- FITUR PENCARIAN (BARU) ---
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari nama dokumen...")
        self.search_input.setStyleSheet("padding: 10px; border-radius: 20px; border: 1px solid #bdc3c7; background: white; color: black;")
        self.search_input.textChanged.connect(self.load_data) # Live search
        search_layout.addWidget(self.search_input)
        self.main_layout.addLayout(search_layout)

        # --- TABEL (DENGAN KOLOM JUMLAH FILE) ---
        self.table = QTableWidget()
        self.table.setColumnCount(5) # Tambah 1 kolom
        self.table.setHorizontalHeaderLabels(["NO", "NAMA DOKUMEN", "TANGGAL", "ISI", "AKSI"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setStyleSheet("""
            QTableWidget { background-color: white; color: black; gridline-color: #f1f2f6; } 
            QHeaderView::section { background-color: #7132CA; color: white; padding: 10px; font-weight: bold; }
        """)
        self.main_layout.addWidget(self.table)

    def pilih_file(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Pilih Dokumen", "", "All Files (*)")
        if files:
            self.files_asal = files
            self.lbl_path.setText(f"{len(files)} file dipilih")
            self.lbl_path.setStyleSheet("color: #27ae60; font-weight: bold; border: none;")

    def simpan_dokumen(self):
        judul = self.ent_judul.text().strip()
        if not judul or not self.files_asal:
            self.notifikasi_custom("Peringatan", "Isi judul dan pilih file!", QMessageBox.Icon.Warning)
            return

        try:
            nama_folder_aman = "".join([c for c in judul if c.isalnum() or c in (' ', '_', '-')]).strip()
            folder_tujuan = os.path.join(os.getcwd(), "uploads", "dokumen", nama_folder_aman)
            
            if os.path.exists(folder_tujuan):
                folder_tujuan += "_" + datetime.now().strftime('%H%M%S')
            
            os.makedirs(folder_tujuan, exist_ok=True)

            for file_path in self.files_asal:
                shutil.copy(file_path, folder_tujuan)

            db = connect_db()
            cursor = db.cursor()
            cursor.execute("INSERT INTO surat (judul_surat, kategori, tanggal, file_path) VALUES (?, ?, ?, ?)",
                           (judul, 'dokumen', datetime.now().strftime('%Y-%m-%d'), folder_tujuan))
            db.commit()
            db.close()
            
            self.notifikasi_custom("Berhasil", f"Folder '{judul}' berhasil disimpan.", QMessageBox.Icon.Information)
            self.reset_form()
            self.load_data()

        except Exception as e:
            self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)

    def load_data(self):
        try:
            self.table.setRowCount(0)
            keyword = self.search_input.text()
            db = connect_db()
            cursor = db.cursor()
            
            # Query dengan filter pencarian
            query = "SELECT id, judul_surat, tanggal, file_path FROM surat WHERE kategori='dokumen' AND judul_surat LIKE ? ORDER BY id DESC"
            cursor.execute(query, ('%' + keyword + '%',))
            
            for i, row in enumerate(cursor.fetchall()):
                id_db, judul, tgl, path = row
                self.table.insertRow(i)
                
                # Hitung jumlah file di dalam folder (Fitur Baru)
                jml_file = 0
                if os.path.exists(path):
                    jml_file = len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])

                self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                self.table.setItem(i, 1, QTableWidgetItem(str(judul)))
                self.table.setItem(i, 2, QTableWidgetItem(str(tgl)))
                self.table.setItem(i, 3, QTableWidgetItem(f"{jml_file} File"))
                
                # Container Tombol
                btn_container = QWidget()
                btn_container.setStyleSheet("background: transparent;")
                btn_lay = QHBoxLayout(btn_container)
                btn_lay.setContentsMargins(5, 2, 5, 2)
                btn_lay.setSpacing(10)
                
                btn_buka = QPushButton("Buka")
                btn_buka.setStyleSheet("background: #5c7cfa; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;")
                btn_buka.clicked.connect(lambda checked, p=path: self.buka_folder(p))
                
                btn_hapus = QPushButton("🗑")
                btn_hapus.setStyleSheet("background: #ff6b6b; color: white; padding: 5px; border-radius: 4px;")
                btn_hapus.clicked.connect(lambda checked, id_d=id_db, p=path: self.aksi_hapus(id_d, p))

                btn_lay.addWidget(btn_buka)
                btn_lay.addWidget(btn_hapus)
                self.table.setCellWidget(i, 4, btn_container)
                self.table.setRowHeight(i, 50)
            db.close()
        except Exception as e: print(e)

    def buka_folder(self, path):
        if os.path.exists(path):
            os.startfile(os.path.abspath(path))
        else:
            self.notifikasi_custom("Error", "Folder fisik tidak ditemukan!", QMessageBox.Icon.Critical)

    def aksi_hapus(self, id_doc, path_folder):
        msg = QMessageBox(self)
        msg.setWindowTitle("Hapus Dokumen")
        msg.setText("Hapus data dan seluruh file di dalam folder ini?")
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setStyleSheet("QMessageBox { background: white; } QLabel { color: black; }")
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            try:
                # 1. Hapus Folder Fisik (Fitur Baru)
                if os.path.exists(path_folder):
                    shutil.rmtree(path_folder) # Menghapus folder beserta isinya

                # 2. Hapus dari Database
                db = connect_db(); cursor = db.cursor()
                cursor.execute("DELETE FROM surat WHERE id = ?", (id_doc,))
                db.commit(); db.close()
                
                self.load_data()
            except Exception as e:
                self.notifikasi_custom("Error", f"Gagal menghapus: {e}", QMessageBox.Icon.Critical)

    def reset_form(self):
        self.ent_judul.clear()
        self.lbl_path.setText("0 file dipilih")
        self.lbl_path.setStyleSheet("color: #7f8c8d; font-style: italic; border: none;")
        self.files_asal = []

    def notifikasi_custom(self, judul, pesan, ikon):
        msg = QMessageBox(self)
        msg.setWindowTitle(judul); msg.setText(pesan); msg.setIcon(ikon)
        msg.setStyleSheet("QMessageBox { background-color: white; } QLabel { color: black; } QPushButton { color: black; min-width: 80px; }")
        msg.exec()