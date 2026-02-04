import os
import shutil
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QMessageBox, 
                             QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
                             QListWidget, QAbstractItemView, QDialog, 
                             QStyledItemDelegate, QStyleOptionViewItem)
from PyQt6.QtCore import Qt, QSize, QDate
from PyQt6.QtGui import QIcon, QAction, QPainter, QColor
from .db_manager import connect_db
from send2trash import send2trash

# --- 1. HELPER CLASSES (SAMA DENGAN SURAT MASUK/KELUAR) ---

class PaddedItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        style = opt.widget.style()
        
        # Gambar background seleksi penuh
        style.drawPrimitive(style.PrimitiveElement.PE_PanelItemViewItem, opt, painter, opt.widget)
        
        # Beri padding pada text
        opt.rect.adjust(10, 5, -10, -5) 
        
        # Hapus state selected agar text tidak digambar ulang
        opt.state &= ~style.StateFlag.State_Selected
        opt.state &= ~style.StateFlag.State_HasFocus
        
        style.drawControl(style.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

class NumericTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        try: return float(self.text()) < float(other.text())
        except ValueError: return super().__lt__(other)

class DateTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            d1 = QDate.fromString(self.text(), "yyyy-MM-dd") # Format database dokumen biasanya yyyy-MM-dd
            d2 = QDate.fromString(other.text(), "yyyy-MM-dd")
            return d1 < d2
        except: return super().__lt__(other)

# Custom Item untuk Sorting Jumlah File (Misal: "5 File")
class FileCountItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            # Ambil angka di depan spasi ("10 File" -> 10)
            val1 = int(self.text().split()[0])
            val2 = int(other.text().split()[0])
            return val1 < val2
        except: return super().__lt__(other)

# --- 2. WIDGET DRAG & DROP ---

class DropListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #bdc3c7;
                border-radius: 6px;
                padding: 5px;
                background-color: #f7f9f9;
                color: #2c3e50;
                font-size: 13px;
            }
            QListWidget:hover {
                border: 2px dashed #3498db;
                background-color: #ecf0f1;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.count() == 0:
            painter = QPainter(self.viewport())
            painter.save()
            col = QColor(150, 150, 150)
            painter.setPen(col)
            text = "Seret & Lepas (Drag & Drop) file di sini..."
            rect = self.viewport().rect()
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            painter.restore()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            if os.path.isfile(f):
                items = self.findItems(f, Qt.MatchFlag.MatchExactly)
                if not items: self.addItem(f)
        event.accept()

# --- 3. CLASS UTAMA ---

class KelolaDokumen(QWidget):
    def __init__(self):
        super().__init__()
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

        # --- CONTAINER FORM ---
        self.card_frame = QFrame()
        self.card_frame.setStyleSheet("background-color: white; border-radius: 12px; border: 1px solid #dfe6e9;")
        card_layout = QVBoxLayout(self.card_frame)
        
        # Input Judul
        v_box_judul = QVBoxLayout()
        v_box_judul.addWidget(QLabel("<b>Nama Folder / Kelompok Dokumen:</b>", styleSheet="border:none; color: black;"))
        self.ent_judul = QLineEdit()
        self.ent_judul.setPlaceholderText("Contoh: Laporan Keuangan 2025")
        self.ent_judul.setStyleSheet("padding: 10px; border: 1px solid #bdc3c7; border-radius: 6px; color: black;")
        v_box_judul.addWidget(self.ent_judul)
        card_layout.addLayout(v_box_judul)

        # Area File
        file_area_layout = QHBoxLayout()
        
        self.list_files = DropListWidget()
        self.list_files.setFixedHeight(120)
        file_area_layout.addWidget(self.list_files, 3) 
        
        btn_file_layout = QVBoxLayout()
        
        # Style Tombol Biru
        style_btn_blue = """
            QPushButton { background-color: #3498db; color: white; padding: 8px; border-radius: 5px; font-weight: bold;}
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #1abc9c; }
        """
        # Style Tombol Ungu
        style_btn_purple = """
            QPushButton { background-color: #9b59b6; color: white; padding: 8px; border-radius: 5px; font-weight: bold;}
            QPushButton:hover { background-color: #8e44ad; }
            QPushButton:pressed { background-color: #27ae60; }
        """
        # Style Tombol Merah
        style_btn_red = """
            QPushButton { background-color: #e74c3c; color: white; padding: 8px; border-radius: 5px; font-weight: bold;}
            QPushButton:hover { background-color: #c0392b; }
            QPushButton:pressed { background-color: #e67e22; }
        """

        self.btn_pilih = QPushButton("📄 Tambah File")
        self.btn_pilih.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pilih.setStyleSheet(style_btn_blue)
        self.btn_pilih.clicked.connect(self.pilih_file)
        
        self.btn_folder = QPushButton("📂 Ambil 1 Folder")
        self.btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_folder.setStyleSheet(style_btn_purple)
        self.btn_folder.clicked.connect(self.pilih_folder)
        
        self.btn_clear = QPushButton("❌ Hapus List")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setStyleSheet(style_btn_red)
        self.btn_clear.clicked.connect(self.hapus_item_list)
        
        btn_file_layout.addWidget(self.btn_pilih)
        btn_file_layout.addWidget(self.btn_folder)
        btn_file_layout.addWidget(self.btn_clear)
        btn_file_layout.addStretch()
        
        file_area_layout.addLayout(btn_file_layout, 1)
        card_layout.addLayout(file_area_layout)

        # Tombol Simpan
        self.btn_simpan = QPushButton("🚀 Unggah & Simpan Kelompok Dokumen")
        self.btn_simpan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_simpan.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 12px; border-radius: 8px; border: none; }
            QPushButton:hover { background-color: #219150; }
            QPushButton:pressed { background-color: #2ecc71; }
        """)
        self.btn_simpan.clicked.connect(self.simpan_dokumen)
        card_layout.addWidget(self.btn_simpan)

        self.main_layout.addWidget(self.card_frame)

        # --- SEARCH ---
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari nama dokumen...")
        self.search_input.setStyleSheet("padding: 10px; border-radius: 20px; border: 1px solid #bdc3c7; background: white; color: black;")
        self.search_input.textChanged.connect(self.load_data)
        search_layout.addWidget(self.search_input)
        self.main_layout.addLayout(search_layout)

        # --- TABEL (STYLE & SORTING BARU) ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["NO", "NAMA DOKUMEN", "TANGGAL", "ISI", "AKSI"])
        
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False) 
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        
        # Pakai Delegate untuk Padding
        self.table.setItemDelegate(PaddedItemDelegate())

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # No
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Tanggal
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Isi
        
        # Kolom Aksi Fixed Width
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 160)

        self.table.setStyleSheet("""
            QTableWidget { 
                background-color: white; 
                color: #2d3436; 
                border: none; 
                outline: none; 
            }
            QHeaderView::section { 
                background-color: #7132CA; 
                color: white; 
                padding: 12px; 
                font-weight: bold; 
                border: none; 
                text-transform: uppercase;
                border-right: 1px solid #9b59b6;
            }
            QTableWidget::item { 
                padding-top: 8px;
                padding-bottom: 8px;
                padding-left: 10px;
                padding-right: 10px;
                border-bottom: 1px solid #f1f2f6; 
                border-right: 1px solid #e0e0e0;
            }
            QTableWidget::item:selected { 
                background-color: #d1ecf1; 
                color: #0c5460; 
            }
        """)
        self.main_layout.addWidget(self.table)

    def pilih_file(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Pilih Dokumen", "", "All Files (*)")
        if files:
            for f in files:
                if not self.list_files.findItems(f, Qt.MatchFlag.MatchExactly):
                    self.list_files.addItem(f)

    def pilih_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih Folder (Ambil Semua Isi)")
        if folder:
            try:
                for nama_file in os.listdir(folder):
                    full_path = os.path.join(folder, nama_file)
                    if os.path.isfile(full_path):
                        items = self.list_files.findItems(full_path, Qt.MatchFlag.MatchExactly)
                        if not items:
                            self.list_files.addItem(full_path)
            except Exception as e:
                self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)

    def hapus_item_list(self):
        selected_items = self.list_files.selectedItems()
        if not selected_items:
            self.list_files.clear()
        else:
            for item in selected_items:
                self.list_files.takeItem(self.list_files.row(item))

    def simpan_dokumen(self):
        judul = self.ent_judul.text().strip()
        files_to_copy = [self.list_files.item(i).text() for i in range(self.list_files.count())]

        if not judul or not files_to_copy:
            self.notifikasi_custom("Peringatan", "Isi judul dan pastikan ada file di dalam list!", QMessageBox.Icon.Warning)
            return

        try:
            nama_folder_aman = "".join([c for c in judul if c.isalnum() or c in (' ', '_', '-')]).strip()
            folder_tujuan = os.path.join(os.getcwd(), "uploads", "dokumen", nama_folder_aman)
            
            if os.path.exists(folder_tujuan):
                folder_tujuan += "_" + datetime.now().strftime('%H%M%S')
            
            os.makedirs(folder_tujuan, exist_ok=True)

            for file_path in files_to_copy:
                if os.path.exists(file_path):
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
            self.table.setSortingEnabled(False) # Matikan sorting saat insert
            self.table.setRowCount(0)
            keyword = self.search_input.text()
            db = connect_db()
            cursor = db.cursor()
            
            query = "SELECT id, judul_surat, tanggal, file_path FROM surat WHERE kategori='dokumen' AND judul_surat LIKE ? ORDER BY id DESC"
            cursor.execute(query, ('%' + keyword + '%',))
            
            for i, row in enumerate(cursor.fetchall()):
                id_db, judul, tgl, path = row
                self.table.insertRow(i)
                
                jml_file = 0
                if os.path.exists(path):
                    jml_file = len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])

                # 0. No (Numeric)
                item_no = NumericTableWidgetItem(str(i + 1))
                item_no.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
                self.table.setItem(i, 0, item_no)

                # 1. Judul
                item_judul = QTableWidgetItem(str(judul))
                item_judul.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                self.table.setItem(i, 1, item_judul)

                # 2. Tanggal (Date Sort)
                item_tgl = DateTableWidgetItem(str(tgl))
                item_tgl.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                self.table.setItem(i, 2, item_tgl)

                # 3. Isi (File Count Sort)
                item_isi = FileCountItem(f"{jml_file} File")
                item_isi.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
                self.table.setItem(i, 3, item_isi)
                
                # 4. Aksi
                btn_container = QWidget()
                btn_container.setStyleSheet("background: transparent;")
                btn_lay = QHBoxLayout(btn_container)
                btn_lay.setContentsMargins(5, 5, 5, 5)
                btn_lay.setSpacing(5)
                btn_lay.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
                
                btn_buka = QPushButton("Buka")
                btn_buka.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_buka.setStyleSheet("""
                    QPushButton { background: #5c7cfa; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold; font-size: 11px; }
                    QPushButton:hover { background: #4263eb; }
                """)
                btn_buka.clicked.connect(lambda checked, p=path: self.buka_folder(p))
                
                btn_hapus = QPushButton("🗑")
                btn_hapus.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_hapus.setStyleSheet("""
                    QPushButton { background: #ff6b6b; color: white; padding: 5px; border-radius: 4px; font-size: 11px; }
                    QPushButton:hover { background: #e74c3c; }
                """)
                btn_hapus.clicked.connect(lambda checked, id_d=id_db, p=path: self.aksi_hapus(id_d, p))

                btn_lay.addWidget(btn_buka)
                btn_lay.addWidget(btn_hapus)
                self.table.setCellWidget(i, 4, btn_container)
            
            self.table.resizeRowsToContents()
            self.table.setSortingEnabled(True) # Nyalakan lagi
            db.close()
        except Exception as e: print(e)

    def buka_folder(self, path):
        if os.path.exists(path):
            os.startfile(os.path.abspath(path))
        else:
            self.notifikasi_custom("Error", "Folder fisik tidak ditemukan!", QMessageBox.Icon.Critical)

    def aksi_hapus(self, id_doc, path_folder):
        # UI POPUP KONFIRMASI (SAMA DENGAN SURAT MASUK)
        dialog = QDialog(self)
        dialog.setWindowTitle("Konfirmasi Hapus")
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        dialog.setFixedWidth(400)
        dialog.setStyleSheet("background-color: white; border-radius: 8px;")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_icon = QLabel("🗑️")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 60px; border: none; background: transparent;")
        layout.addWidget(lbl_icon)
        
        lbl_judul = QLabel("HAPUS DOKUMEN?")
        lbl_judul.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_judul.setStyleSheet("font-size: 22px; font-weight: 900; color: #c0392b; border: none; background: transparent;")
        layout.addWidget(lbl_judul)
        
        lbl_pesan = QLabel("Seluruh file di dalam folder ini akan dihapus permanen.")
        lbl_pesan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_pesan.setStyleSheet("font-size: 14px; color: #57606f; border: none;")
        layout.addWidget(lbl_pesan)
        layout.addSpacing(15)

        btn_layout = QHBoxLayout()
        btn_batal = QPushButton("Batal")
        btn_batal.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_batal.setFixedHeight(40)
        btn_batal.setStyleSheet("QPushButton { background-color: #ecf0f1; color: #2c3e50; border: 1px solid #bdc3c7; border-radius: 6px; font-weight: bold; } QPushButton:hover { background-color: #dfe6e9; }")
        btn_batal.clicked.connect(dialog.reject)
        
        btn_hapus = QPushButton("Ya, Hapus")
        btn_hapus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_hapus.setFixedHeight(40)
        btn_hapus.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border: none; border-radius: 6px; font-weight: bold; } QPushButton:hover { background-color: #c0392b; }")
        btn_hapus.clicked.connect(dialog.accept)
        
        btn_layout.addWidget(btn_batal)
        btn_layout.addWidget(btn_hapus)
        layout.addLayout(btn_layout)
        
        if dialog.exec():
            try:
                # 1. Hapus Folder Fisik (PINDAH KE RECYCLE BIN)
                if os.path.exists(path_folder):
                    # GANTI shutil.rmtree DENGAN INI:
                    send2trash(path_folder) 

                # 2. Hapus dari Database (Tetap hapus permanen dari DB)
                db = connect_db(); cursor = db.cursor()
                cursor.execute("DELETE FROM surat WHERE id = ?", (id_doc,))
                db.commit(); db.close()
                
                self.load_data()
                self.notifikasi_custom("Berhasil", "Dokumen dipindahkan ke Recycle Bin!", QMessageBox.Icon.Information)
            
            except Exception as e:
                self.notifikasi_custom("Error", f"Gagal menghapus: {e}", QMessageBox.Icon.Critical)

    def reset_form(self):
        self.ent_judul.clear()
        self.list_files.clear()
        self.files_asal = []

    # --- POPUP NOTIFIKASI KUSTOM (SUKSES / GAGAL) ---
    def notifikasi_custom(self, judul, pesan, ikon):
        dialog = QDialog(self)
        dialog.setWindowTitle(judul)
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        dialog.setFixedWidth(380)
        dialog.setStyleSheet("background-color: white; border-radius: 8px;")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(10)
        
        emoji = "✅" 
        warna_judul = "#27ae60"
        
        if ikon == QMessageBox.Icon.Warning:
            emoji = "⚠️"; warna_judul = "#f39c12"
        elif ikon == QMessageBox.Icon.Critical:
            emoji = "❌"; warna_judul = "#c0392b"

        lbl_icon = QLabel(emoji)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 55px; border: none; background: transparent;")
        layout.addWidget(lbl_icon)
        
        lbl_judul = QLabel(judul.upper())
        lbl_judul.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_judul.setStyleSheet(f"font-size: 20px; font-weight: 900; color: {warna_judul}; border: none; background: transparent; margin-top: 5px;")
        layout.addWidget(lbl_judul)
        
        lbl_pesan = QLabel(pesan)
        lbl_pesan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_pesan.setWordWrap(True)
        lbl_pesan.setStyleSheet("font-size: 13px; color: #57606f; line-height: 1.4; border: none; background: transparent;")
        layout.addWidget(lbl_pesan)
        
        layout.addSpacing(15)

        btn_ok = QPushButton("OK")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.clicked.connect(dialog.accept)
        btn_ok.setFixedHeight(45)
        btn_ok.setStyleSheet("""
            QPushButton { background-color: #34495e; color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #2c3e50; }
            QPushButton:pressed { background-color: #27ae60; }
        """)
        layout.addWidget(btn_ok)

        dialog.exec()