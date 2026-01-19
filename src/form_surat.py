import os
from PyQt6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QPushButton, 
                             QVBoxLayout, QLabel, QHBoxLayout, QFileDialog, 
                             QDateEdit, QComboBox, QCompleter, QGroupBox, QFrame)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QIcon
from .db_manager import connect_db

class FormTambahSurat(QDialog):
    def __init__(self, parent=None, kategori="Keluar"):
        super().__init__(parent)
        self.kategori = kategori
        self.setWindowTitle(f"Form Arsip Surat {self.kategori}")
        self.setFixedWidth(500)
        self.file_path = ""
        
        # Buat ikon panah terlebih dahulu
        self.create_arrow_icon()
        
        # --- GLOBAL STYLING YANG DIPERBAIKI - WARNA HITAM TETAP ---
        self.setStyleSheet(f"""
            QDialog {{ background-color: #f4f6f8; }}
            QLabel {{ color: #34495e; font-weight: 600; font-size: 13px; }}
            
            /* Styling Umum Input - WARNA TEKS HITAM DIPAKSA */
            QLineEdit, QDateEdit, QComboBox {{ 
                border: 1px solid #dcdde1; 
                border-radius: 6px; 
                color: #000000; /* HITAM - tidak terpengaruh tema Windows */
                background: white;
                font-size: 13px;
                min-height: 25px;
            }}

            /* Styling Khusus QLineEdit (Padding Rata) */
            QLineEdit {{
                padding: 10px;
                color: #000000; /* HITAM */
            }}

            /* PERBAIKAN: Styling Khusus ComboBox & DateEdit 
               Memberi ruang di kanan (padding-right) agar panah tidak tertutup */
            QComboBox, QDateEdit {{
                padding: 5px;
                padding-left: 10px;
                padding-right: 30px;
                color: #000000; /* HITAM */
            }}

            /* Pastikan teks tetap hitam saat fokus */
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{
                border: 1px solid #3498db;
                background: #ffffff;
                color: #000000; /* HITAM */
            }}

            /* Pastikan teks tetap hitam saat disabled */
            QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled {{
                color: #000000; /* HITAM */
                background: #f0f0f0;
            }}

            /* Pastikan teks di ComboBox dropdown juga hitam */
            QComboBox QAbstractItemView {{
                border: 1px solid #dcdde1;
                background-color: white;
                color: #000000; /* HITAM untuk item dropdown */
                selection-background-color: #3498db;
                selection-color: white; /* Putih saat item dipilih */
                padding: 5px;
            }}

            /* Pastikan teks yang sedang ditulis di ComboBox editable tetap hitam */
            QComboBox:editable {{
                color: #000000; /* HITAM */
            }}

            /* Override untuk semua state widget */
            QLineEdit:hover, QComboBox:hover, QDateEdit:hover {{
                color: #000000; /* HITAM */
            }}

            QGroupBox {{
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
                color: #2c3e50;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}

            /* PERBAIKAN: Styling Tombol Panah Dropdown */
            QComboBox::drop-down, QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 1px;
                border-left-color: #bdc3c7;
                border-left-style: solid;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background: #ecf0f1;
            }}
            
            /* Panah saat hover */
            QComboBox::drop-down:hover, QDateEdit::drop-down:hover {{
                background: #d5dbdb;
            }}
            
            /* Menggunakan gambar arrow yang sudah dibuat */
            QComboBox::down-arrow, QDateEdit::down-arrow {{
                image: url({self.arrow_icon_path});
                width: 12px;
                height: 12px;
            }}
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        # --- HEADER ---
        warna_header = "#27ae60" if self.kategori == "Keluar" else "#2980b9"
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: {warna_header}; border-radius: 8px;")
        header_frame.setFixedHeight(60)
        
        hl = QHBoxLayout(header_frame)
        lbl_judul = QLabel(f"📝 INPUT DATA SURAT {self.kategori.upper()}")
        lbl_judul.setStyleSheet("color: white; font-size: 16px; font-weight: bold; border: none;")
        lbl_judul.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(lbl_judul)
        
        self.layout.addWidget(header_frame)

        # --- FORM GROUP (CARD) ---
        form_group = QGroupBox("Detail Surat")
        form_layout = QFormLayout(form_group)
        form_layout.setContentsMargins(20, 25, 20, 20)
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # 1. Tanggal
        label_tgl_utama = "Tanggal Terima" if self.kategori == "Masuk" else "Tanggal Kirim"
        self.ent_tanggal = QDateEdit()
        self.ent_tanggal.setCalendarPopup(True) 
        self.ent_tanggal.setDate(QDate.currentDate()) 
        self.ent_tanggal.setDisplayFormat("yyyy-MM-dd")
        
        # 2. Pihak Luar
        label_pihak = "Dari (Pengirim)" if self.kategori == "Masuk" else "Kepada (Tujuan)"
        self.ent_pihak = QLineEdit()
        self.ent_pihak.setPlaceholderText("Isi nama instansi atau perseorangan...")
        
        # 3. PERIHAL / KODE (DROPDOWN)
        self.ent_perihal = QComboBox()
        self.ent_perihal.setEditable(True) 
        self.ent_perihal.setInsertPolicy(QComboBox.InsertPolicy.NoInsert) 
        self.ent_perihal.setPlaceholderText("Ketik kode atau keterangan surat...")
        
        self.ent_perihal.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.ent_perihal.completer().setFilterMode(Qt.MatchFlag.MatchContains) 
        self.ent_perihal.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive) 
        self.load_kode_surat() 

        # 4. Nomor Surat
        self.ent_nomor = QLineEdit()
        self.ent_nomor.setPlaceholderText("Cth: 001/SK-DIR/I/2026")
        
        # 5. Tanggal Surat
        self.ent_tgl_surat = QDateEdit()
        self.ent_tgl_surat.setCalendarPopup(True)
        self.ent_tgl_surat.setDate(QDate.currentDate())
        self.ent_tgl_surat.setDisplayFormat("yyyy-MM-dd")
        
        # 6. Keterangan
        self.ent_keterangan = QLineEdit()
        self.ent_keterangan.setPlaceholderText("Catatan tambahan (Opsional)")
        
        # --- LAYOUT ---
        form_layout.addRow(QLabel(f"{label_tgl_utama}"), self.ent_tanggal)
        form_layout.addRow(QLabel(f"{label_pihak}"), self.ent_pihak)
        form_layout.addRow(QLabel("Perihal / Kode"), self.ent_perihal)
        form_layout.addRow(QLabel("Nomor Surat"), self.ent_nomor)
        form_layout.addRow(QLabel("Tanggal Surat"), self.ent_tgl_surat)
        form_layout.addRow(QLabel("Keterangan"), self.ent_keterangan)
        
        self.layout.addWidget(form_group)
        
        # --- LAMPIRAN ---
        file_group = QGroupBox("Lampiran Digital")
        file_layout = QHBoxLayout(file_group)
        file_layout.setContentsMargins(15, 20, 15, 20)
        
        self.btn_browse = QPushButton("  Pilih File Scan")
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.setStyleSheet("""
            QPushButton { 
                background: #ecf0f1; color: #2c3e50; padding: 10px 15px; 
                border: 1px solid #bdc3c7; border-radius: 6px; font-weight: bold; 
            }
            QPushButton:hover { background: #dfe6e9; border: 1px solid #95a5a6; }
        """)
        self.btn_browse.clicked.connect(self.pilih_berkas)
        
        self.lbl_file = QLabel("Belum ada berkas dipilih...")
        self.lbl_file.setStyleSheet("color: #7f8c8d; font-style: italic; margin-left: 10px; font-weight: normal;")
        
        file_layout.addWidget(self.btn_browse)
        file_layout.addWidget(self.lbl_file, 1)
        self.layout.addWidget(file_group)

        # --- TOMBOL SIMPAN ---
        self.layout.addSpacing(10)
        self.btn_simpan = QPushButton("💾  SIMPAN DATA KE ARSIP")
        self.btn_simpan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_simpan.setStyleSheet(f"""
            QPushButton {{
                background-color: {warna_header}; color: white; padding: 14px; 
                border-radius: 8px; font-weight: bold; font-size: 14px; 
                border: none; margin-top: 5px;
            }}
            QPushButton:hover {{ background-color: #2c3e50; border: 2px solid {warna_header}; }}
        """)
        self.btn_simpan.clicked.connect(self.accept) 
        self.layout.addWidget(self.btn_simpan)

        self.setup_calendar_style()

    def create_arrow_icon(self):
        """Membuat ikon panah dropdown menggunakan SVG"""
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPixmap, QPainter
        import tempfile
        
        # SVG untuk panah ke bawah (segitiga)
        svg_data = """<?xml version="1.0" encoding="UTF-8"?>
        <svg width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
            <polygon points="4,6 12,6 8,11" fill="#2c3e50"/>
        </svg>"""
        
        # Simpan sebagai file sementara
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False)
        temp_file.write(svg_data)
        temp_file.close()
        
        self.arrow_icon_path = temp_file.name

    def setup_calendar_style(self):
        # Memastikan panah di dalam kalender popup tetap terlihat
        style = """
            QCalendarWidget QAbstractItemView:enabled { 
                selection-background-color: #3498db; color: black; 
            } 
            QCalendarWidget QToolButton { 
                color: black; font-weight: bold; background: transparent; icon-size: 20px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: white; }
        """
        self.ent_tanggal.calendarWidget().setStyleSheet(style)
        self.ent_tgl_surat.calendarWidget().setStyleSheet(style)

    def pilih_berkas(self):
        file, _ = QFileDialog.getOpenFileName(self, "Pilih File Scan", "", "Images/PDF (*.jpg *.jpeg *.png *.pdf)")
        if file:
            self.file_path = file
            self.lbl_file.setText(os.path.basename(file))
            self.lbl_file.setStyleSheet("color: #27ae60; font-weight: bold; font-style: normal;")

    def load_kode_surat(self):
        try:
            self.ent_perihal.clear()
            self.ent_perihal.addItem("") 
            db = connect_db()
            cursor = db.cursor()
            cursor.execute("SELECT kode, keterangan FROM kode_surat ORDER BY keterangan ASC")
            for kode, ket in cursor.fetchall():
                self.ent_perihal.addItem(f"{ket} - {kode}")
            db.close()
        except Exception as e: print(e)