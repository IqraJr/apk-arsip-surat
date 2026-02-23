import os
import shutil
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QMessageBox, 
                             QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
                             QListWidget, QListWidgetItem, QAbstractItemView, QDialog, 
                             QStyledItemDelegate, QStyleOptionViewItem, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt, QSize, QDate
from PyQt6.QtGui import QIcon, QPainter, QColor
from .db_manager import connect_db
from .settings import get_folder_path, set_folder_path
from send2trash import send2trash

# --- 1. HELPER CLASSES ---

class PaddedItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        style = opt.widget.style()
        style.drawPrimitive(style.PrimitiveElement.PE_PanelItemViewItem, opt, painter, opt.widget)
        opt.rect.adjust(10, 5, -10, -5) 
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
            d1 = QDate.fromString(self.text(), "dd/MM/yyyy")
            d2 = QDate.fromString(other.text(), "dd/MM/yyyy")
            return d1 < d2
        except: return super().__lt__(other)

class FileCountItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
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
                self.addItemWithButton(f)
        event.accept()

    def addItemWithButton(self, file_path):
        items = self.findItems(file_path, Qt.MatchFlag.MatchExactly)
        if items: return 

        item = QListWidgetItem(self)
        item.setText(file_path)
        item.setSizeHint(QSize(0, 40)) 
        self.addItem(item)
        
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)
        
        lbl_text = QLabel(os.path.basename(file_path))
        lbl_text.setToolTip(file_path)
        lbl_text.setStyleSheet("font-weight: bold; color: #2c3e50;")
        
        btn_del = QPushButton("🗑")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setFixedSize(30, 30)
        btn_del.setStyleSheet("QPushButton { background-color: #ff7675; color: white; border-radius: 4px; border: none; font-size: 14px; } QPushButton:hover { background-color: #d63031; }")
        btn_del.clicked.connect(lambda: self.hapus_item_spesifik(item))
        
        layout.addWidget(lbl_text)
        layout.addStretch()
        layout.addWidget(btn_del)
        
        self.setItemWidget(item, widget)

    def hapus_item_spesifik(self, item):
        row = self.row(item)
        self.takeItem(row)

# --- 3. CLASS UTAMA ---

class KelolaDokumen(QWidget):
    def __init__(self):
        super().__init__()
        self.all_data = []      
        self.filtered_data = [] 
        self.current_page = 1
        self.rows_per_page = 10
        self.create_check_icon()
        self.create_arrow_icon()
        self.setup_ui()
        self.load_data()

    def create_check_icon(self):
        import tempfile
        svg_data = """<?xml version="1.0" encoding="UTF-8"?>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">
            <polyline points="20 6 9 17 4 12"></polyline>
        </svg>"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False)
        temp_file.write(svg_data)
        temp_file.close()
        self.check_icon_path = temp_file.name.replace('\\', '/')

    def create_arrow_icon(self):
        import tempfile
        svg_data = """<?xml version="1.0" encoding="UTF-8"?>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">
            <polyline points="6 9 12 15 18 9"></polyline>
        </svg>"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False)
        temp_file.write(svg_data)
        temp_file.close()
        self.arrow_icon_path = temp_file.name.replace('\\', '/')

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(15)

        # --- HEADER ---
        header_layout = QHBoxLayout()
        judul_container = QVBoxLayout()
        title = QLabel("📁 Manajer Dokumen Digital")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1a1a2e;")
        self.lbl_folder = QLabel()
        self.lbl_folder.setStyleSheet("color: #636e72; font-size: 12px; font-style: italic;")
        self.update_label_folder()
        judul_container.addWidget(title)
        judul_container.addWidget(self.lbl_folder)
        header_layout.addLayout(judul_container)
        header_layout.addStretch()

        self.btn_ganti_folder = QPushButton("📂 Ganti Folder")
        self.btn_ganti_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ganti_folder.setStyleSheet("QPushButton { background-color: #0984e3; color: white; padding: 8px 15px; border-radius: 6px; font-size: 12px; } QPushButton:hover { background-color: #74b9ff; }")
        self.btn_ganti_folder.clicked.connect(self.aksi_ganti_folder)
        header_layout.addWidget(self.btn_ganti_folder)
        self.main_layout.addLayout(header_layout)

        # --- CONTAINER FORM ---
        self.card_frame = QFrame()
        self.card_frame.setStyleSheet("background-color: white; border-radius: 12px; border: 1px solid #dfe6e9;")
        card_layout = QVBoxLayout(self.card_frame)
        
        # Form Input
        top_form = QHBoxLayout()
        left_form = QVBoxLayout()
        
        self.ent_judul = QLineEdit(); self.ent_judul.setPlaceholderText("Nama Dokumen (Wajib)")
        self.ent_kategori = QLineEdit(); self.ent_kategori.setPlaceholderText("Kategori")
        self.ent_ket = QLineEdit(); self.ent_ket.setPlaceholderText("Keterangan")
        
        for w in [self.ent_judul, self.ent_kategori, self.ent_ket]:
            # [UI FIX] Force text color black
            w.setStyleSheet("padding: 10px; border: 1px solid #bdc3c7; border-radius: 6px; background-color: white; color: black;")
            left_form.addWidget(w)
        
        top_form.addLayout(left_form, 1)

        # File List
        right_form = QVBoxLayout()
        self.list_files = DropListWidget()
        self.list_files.setFixedHeight(120)
        right_form.addWidget(self.list_files)
        
        btn_file_lay = QHBoxLayout()
        btn_add = QPushButton("📄 +File"); btn_add.clicked.connect(self.pilih_file)
        btn_fold = QPushButton("📂 +Folder"); btn_fold.clicked.connect(self.pilih_folder)
        btn_clr = QPushButton("❌ Clear"); btn_clr.clicked.connect(self.hapus_semua_list)
        
        for b in [btn_add, btn_fold, btn_clr]:
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("padding: 5px; border-radius: 4px; background: #dfe6e9; color: black;")
            btn_file_lay.addWidget(b)
            
        right_form.addLayout(btn_file_lay)
        top_form.addLayout(right_form, 2)
        card_layout.addLayout(top_form)

        # Submit Button
        self.btn_simpan = QPushButton("🚀 Simpan Dokumen")
        self.btn_simpan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_simpan.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 12px; border-radius: 8px; border: none; } QPushButton:hover { background-color: #2ecc71; }")
        self.btn_simpan.clicked.connect(self.simpan_dokumen)
        card_layout.addWidget(self.btn_simpan)

        self.main_layout.addWidget(self.card_frame)

        # --- SEARCH ---
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari dokumen...")
        self.search_input.setStyleSheet("padding: 10px; border-radius: 20px; border: 1px solid #bdc3c7; background: white; color: black;")
        self.search_input.textChanged.connect(self.filter_data)
        
        self.combo_tahun = QComboBox()
        self.combo_tahun.addItem("Semua Tahun")
        self.combo_tahun.setFixedWidth(150)
        self.combo_tahun.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # [UI FIX] Styling Dropdown agar tidak konflik background
        self.combo_tahun.setStyleSheet(f"""
            QComboBox {{ 
                padding: 8px; 
                border: 1px solid #dcdde1; 
                border-radius: 8px; 
                background: white; 
                color: black; 
            }} 
            QComboBox::down-arrow {{ 
                image: url({self.arrow_icon_path}); 
                width: 14px; 
            }}
            QComboBox QAbstractItemView {{
                background-color: white;
                color: black;
                selection-background-color: #dfe6e9;
                selection-color: black;
                border: 1px solid #dcdde1;
                outline: none;
            }}
        """)
        self.combo_tahun.currentTextChanged.connect(self.filter_data)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.combo_tahun)
        self.main_layout.addLayout(search_layout)

        # --- TABLE ---
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["", "NO", "TANGGAL", "NAMA DOKUMEN", "KATEGORI", "KETERANGAN", "JML FILE", "AKSI"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False) 
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.table.setItemDelegate(PaddedItemDelegate())

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(0, 40)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(7, 180) # [FIX] Lebarkan kolom aksi
        
        self.table.setStyleSheet("""
            QTableWidget { background-color: white; color: #2d3436; border: none; outline: none; }
            QHeaderView::section { background-color: #7132CA; color: white; padding: 12px; font-weight: bold; border: none; text-transform: uppercase; border-right: 1px solid #9b59b6; }
            QTableWidget::item { border-bottom: 1px solid #f1f2f6; border-right: 1px solid #e0e0e0; }
            QTableWidget::item:selected { background-color: #d1ecf1; color: #0c5460; }
        """)
        self.main_layout.addWidget(self.table)

        # --- PAGINATION & ACTIONS ---
        bottom_layout = QHBoxLayout()
        self.btn_prev = QPushButton("◀"); self.btn_prev.clicked.connect(self.prev_page)
        
        # [UI FIX] Pagination Label
        self.label_page = QLabel("Halaman 1 of 1")
        self.label_page.setStyleSheet("color: black; font-weight: bold; font-size: 13px;") 
        
        self.btn_next = QPushButton("▶"); self.btn_next.clicked.connect(self.next_page)
        
        for b in [self.btn_prev, self.btn_next]:
            b.setFixedWidth(40); b.setStyleSheet("background: #dfe4ea; border-radius: 4px; color: black;")

        self.btn_delete = QPushButton("🗑 Hapus Terpilih")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setStyleSheet("QPushButton { background-color: #ff6b6b; color: white; padding: 8px 15px; border-radius: 6px; border: none; } QPushButton:hover { background-color: #ff5252; }")
        self.btn_delete.clicked.connect(self.aksi_hapus_terpilih)
        
        bottom_layout.addWidget(self.btn_delete)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_prev)
        bottom_layout.addWidget(self.label_page)
        bottom_layout.addWidget(self.btn_next)
        self.main_layout.addLayout(bottom_layout)

    # --- LOGIC ---
    def update_label_folder(self):
        path = get_folder_path("dokumen")
        self.lbl_folder.setText(f"Penyimpanan: {path}")

    def aksi_ganti_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih Folder Penyimpanan Dokumen")
        if folder:
            set_folder_path("dokumen", folder)
            self.update_label_folder()
            self.notifikasi_custom("Sukses", "Lokasi penyimpanan Dokumen berhasil diubah!", QMessageBox.Icon.Information)

    def load_data(self):
        try:
            db = connect_db()
            cursor = db.cursor()
            cursor.execute("SELECT id, tanggal, judul_surat, asal_surat, keterangan, file_path FROM surat WHERE kategori='dokumen' ORDER BY id DESC")
            self.all_data = cursor.fetchall()
            self.populate_tahun_filter()
            self.current_page = 1
            self.filter_data() 
            db.close()
        except Exception as e: print(f"Error Load: {e}")

    def populate_tahun_filter(self):
        current_selection = self.combo_tahun.currentText()
        tahun_set = set()
        for row in self.all_data:
            val_tgl = str(row[1]) if row[1] else ""
            if val_tgl and "-" in val_tgl:
                try: tahun_set.add(val_tgl.split("-")[0])
                except: pass
        list_tahun = sorted(list(tahun_set), reverse=True)
        self.combo_tahun.blockSignals(True)
        self.combo_tahun.clear()
        self.combo_tahun.addItem("Semua Tahun")
        self.combo_tahun.addItems(list_tahun)
        idx = self.combo_tahun.findText(current_selection)
        if idx >= 0: self.combo_tahun.setCurrentIndex(idx)
        else: self.combo_tahun.setCurrentIndex(0)
        self.combo_tahun.blockSignals(False)

    def filter_data(self, *args):
        keyword = self.search_input.text().lower()
        selected_tahun = self.combo_tahun.currentText()
        self.filtered_data = []
        for row in self.all_data:
            text_data = f"{row[2]} {row[3]} {row[4]}".lower() 
            row_tahun = ""
            val_tgl = str(row[1]) if row[1] else ""
            if val_tgl and "-" in val_tgl:
                try: row_tahun = val_tgl.split("-")[0]
                except: pass
            if (keyword in text_data) and ((selected_tahun == "Semua Tahun") or (selected_tahun == row_tahun)):
                self.filtered_data.append(row)
        self.current_page = 1
        self.display_data(self.filtered_data)

    def display_data(self, data):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        start_idx = (self.current_page - 1) * self.rows_per_page
        page_data = data[start_idx : start_idx + self.rows_per_page]
        total_pages = max(1, (len(data) + self.rows_per_page - 1) // self.rows_per_page)
        self.label_page.setText(f"Halaman {self.current_page} dari {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)

        for i, row in enumerate(page_data):
            self.table.insertRow(i)
            
            # Checkbox
            chk_container = QWidget(); chk_container.setStyleSheet("background: transparent;") 
            chk_layout = QHBoxLayout(chk_container); chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter); chk_layout.setContentsMargins(0,0,0,0)
            chk_box = QCheckBox(); chk_box.setProperty("db_id", row[0]); chk_box.setCursor(Qt.CursorShape.PointingHandCursor)
            chk_box.setStyleSheet(f"QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid #bdc3c7; background: white; border-radius: 3px; }} QCheckBox::indicator:checked {{ background: #27ae60; border: 1px solid #27ae60; image: url({self.check_icon_path}); }}")
            chk_layout.addWidget(chk_box)
            self.table.setCellWidget(i, 0, chk_container)

            self.table.setItem(i, 1, NumericTableWidgetItem(str(start_idx + i + 1))) # No
            
            val_tgl = str(row[1])
            try: d = QDate.fromString(val_tgl, "yyyy-MM-dd"); val_tgl = d.toString("dd/MM/yyyy")
            except: pass
            self.table.setItem(i, 2, DateTableWidgetItem(val_tgl))

            self.table.setItem(i, 3, QTableWidgetItem(str(row[2]))) # Nama
            self.table.setItem(i, 4, QTableWidgetItem(str(row[3]))) # Kategori
            self.table.setItem(i, 5, QTableWidgetItem(str(row[4]))) # Ket

            # Hitung File
            path_folder = row[5]
            file_count = 0
            if path_folder and os.path.exists(path_folder) and os.path.isdir(path_folder):
                try: file_count = len([f for f in os.listdir(path_folder) if os.path.isfile(os.path.join(path_folder, f))])
                except: pass
            self.table.setItem(i, 6, FileCountItem(f"{file_count} File"))

            # --- [FIX LAYOUT TOMBOL AKSI] ---
            btn_cont = QWidget()
            btn_cont.setStyleSheet("background: transparent;")
            btn_l = QHBoxLayout(btn_cont)
            btn_l.setContentsMargins(5, 5, 5, 5) 
            btn_l.setSpacing(5)
            btn_l.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
            
            btn_view = QPushButton("Buka")
            btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_view.setStyleSheet("QPushButton { background: #5c7cfa; color: white; border-radius: 4px; padding: 5px 10px; font-weight: bold; font-size: 11px; } QPushButton:hover { background: #4263eb; }")
            btn_view.clicked.connect(lambda checked, p=path_folder: self.buka_folder(p))
            
            btn_edit = QPushButton("✏️ Edit")
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("QPushButton { background: #f1c40f; color: white; border-radius: 4px; padding: 5px 10px; font-weight: bold; font-size: 11px; } QPushButton:hover { background: #f39c12; }")
            btn_edit.clicked.connect(lambda checked, r=row: self.aksi_edit(r))
            
            btn_l.addWidget(btn_view)
            btn_l.addWidget(btn_edit)
            self.table.setCellWidget(i, 7, btn_cont)
        
        self.table.resizeRowsToContents() 
        self.table.setSortingEnabled(True)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.display_data(self.filtered_data)

    def next_page(self):
        total_pages = (len(self.filtered_data) + self.rows_per_page - 1) // self.rows_per_page
        if self.current_page < total_pages:
            self.current_page += 1
            self.display_data(self.filtered_data)

    # --- CRUD ---
    def pilih_file(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Pilih Dokumen", "", "All Files (*)")
        for f in files: self.list_files.addItemWithButton(f)

    def pilih_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih Folder")
        if folder:
            try:
                for f in os.listdir(folder):
                    fp = os.path.join(folder, f)
                    if os.path.isfile(fp): self.list_files.addItemWithButton(fp)
            except: pass

    def hapus_semua_list(self): self.list_files.clear()

    def simpan_dokumen(self):
        judul = self.ent_judul.text().strip()
        files = [self.list_files.item(i).text() for i in range(self.list_files.count())]
        
        if not judul: return self.notifikasi_custom("Gagal", "Nama Dokumen wajib diisi!", QMessageBox.Icon.Warning)
        if not files: return self.notifikasi_custom("Gagal", "Minimal pilih 1 file!", QMessageBox.Icon.Warning)

        try:
            safe_name = "".join([c for c in judul if c.isalnum() or c in (' ', '-', '_')]).strip()
            dest_dir = os.path.join(get_folder_path("dokumen"), safe_name)
            if os.path.exists(dest_dir): dest_dir += f"_{datetime.now().strftime('%H%M%S')}"
            os.makedirs(dest_dir, exist_ok=True)

            for f in files:
                if os.path.exists(f): shutil.copy(f, dest_dir)

            db = connect_db()
            db.execute("INSERT INTO surat (judul_surat, asal_surat, kategori, tanggal, keterangan, file_path) VALUES (?, ?, 'dokumen', ?, ?, ?)",
                       (judul, self.ent_kategori.text(), datetime.now().strftime('%Y-%m-%d'), self.ent_ket.text(), dest_dir))
            db.commit(); db.close()
            
            self.notifikasi_custom("Berhasil", "Dokumen Tersimpan!", QMessageBox.Icon.Information)
            self.ent_judul.clear(); self.ent_kategori.clear(); self.ent_ket.clear(); self.list_files.clear()
            self.load_data()
        except Exception as e: self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)

    def buka_folder(self, path):
        if path and os.path.exists(path): os.startfile(os.path.abspath(path))
        else: self.notifikasi_custom("Info", "Folder fisik tidak ditemukan (Mungkin sudah terhapus).", QMessageBox.Icon.Warning)

    def aksi_edit(self, data):
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Dokumen")
        dialog.setFixedWidth(400)
        # Hapus border-radius dari QDialog untuk menghilangkan artifact hitam
        dialog.setStyleSheet("""
            QDialog { background-color: white; }
            QLabel { color: black; font-weight: bold; background: transparent; }
            QLineEdit { border: 1px solid #bdc3c7; border-radius: 4px; padding: 6px; background: white; color: black; }
        """)
        layout = QVBoxLayout(dialog)
        
        inp_nama = QLineEdit(str(data[2]))
        inp_kategori = QLineEdit(str(data[3]))
        inp_ket = QLineEdit(str(data[4]))
        
        layout.addWidget(QLabel("Nama Dokumen:")); layout.addWidget(inp_nama)
        layout.addWidget(QLabel("Kategori:")); layout.addWidget(inp_kategori)
        layout.addWidget(QLabel("Keterangan:")); layout.addWidget(inp_ket)
        
        btn = QPushButton("Simpan")
        btn.clicked.connect(dialog.accept)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; padding: 10px; border-radius: 6px; font-weight: bold; border: none; } QPushButton:hover { background-color: #2980b9; }")
        layout.addWidget(btn)
        
        if dialog.exec():
            try:
                db = connect_db()
                db.execute("UPDATE surat SET judul_surat=?, asal_surat=?, keterangan=? WHERE id=?", 
                           (inp_nama.text(), inp_kategori.text(), inp_ket.text(), data[0]))
                db.commit(); db.close()
                self.load_data()
                self.notifikasi_custom("Sukses", "Data diperbarui!", QMessageBox.Icon.Information)
            except Exception as e: self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)

    # --- [LOGIKA HAPUS CERDAS] ---
    def aksi_hapus_terpilih(self):
        ids_to_delete = []
        for i in range(self.table.rowCount()):
            widget = self.table.cellWidget(i, 0)
            if widget:
                chk = widget.findChild(QCheckBox) 
                if chk and chk.isChecked(): ids_to_delete.append(chk.property("db_id"))

        if not ids_to_delete:
            self.notifikasi_custom("Peringatan", "Pilih (centang) data yang ingin dihapus!", QMessageBox.Icon.Warning)
            return

        # UI Dialog Konfirmasi
        dialog = QDialog(self)
        dialog.setWindowTitle("Konfirmasi Hapus")
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        dialog.setFixedWidth(400)
        dialog.setStyleSheet("background-color: white; border-radius: 8px;")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        lbl_icon = QLabel("🗑️")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 60px; border: none; background: transparent;")
        layout.addWidget(lbl_icon)
        
        lbl_judul = QLabel("HAPUS DOKUMEN?")
        lbl_judul.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_judul.setStyleSheet("font-size: 22px; font-weight: 900; color: #c0392b; border: none; background: transparent; margin-top: 5px;")
        layout.addWidget(lbl_judul)
        
        lbl_pesan = QLabel(f"Anda akan menghapus <b>{len(ids_to_delete)} dokumen</b> terpilih.<br>Folder fisik akan dipindahkan ke Recycle Bin.")
        lbl_pesan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_pesan.setWordWrap(True)
        lbl_pesan.setStyleSheet("font-size: 14px; color: #57606f; line-height: 1.4; border: none; background: transparent;")
        layout.addWidget(lbl_pesan)
        layout.addSpacing(15)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        btn_batal = QPushButton("Batal")
        btn_batal.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_batal.setFixedHeight(40)
        btn_batal.setStyleSheet("QPushButton { background-color: #ecf0f1; color: #2c3e50; border: 1px solid #bdc3c7; border-radius: 6px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #dfe6e9; }")
        btn_batal.clicked.connect(dialog.reject)
        
        btn_hapus = QPushButton("Ya, Hapus")
        btn_hapus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_hapus.setFixedHeight(40)
        btn_hapus.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #c0392b; }")
        btn_hapus.clicked.connect(dialog.accept)
        
        btn_layout.addWidget(btn_batal)
        btn_layout.addWidget(btn_hapus)
        layout.addLayout(btn_layout)

        if dialog.exec(): 
            try:
                db = connect_db()
                cursor = db.cursor()
                deleted_count = 0
                locked_items = [] # Menyimpan nama folder yang gagal dihapus

                for db_id in ids_to_delete:
                    cursor.execute("SELECT judul_surat, file_path FROM surat WHERE id=?", (db_id,))
                    row = cursor.fetchone()
                    
                    if not row: continue
                    
                    judul_doc = row[0]
                    raw_path = row[1]
                    delete_success = False

                    # Normalisasi Path
                    if raw_path and raw_path.startswith("\\\\?\\"): raw_path = raw_path[4:]
                    path_folder = os.path.normpath(raw_path) if raw_path else None
                    
                    # Logika Hapus Fisik
                    if path_folder and os.path.exists(path_folder):
                        try:
                            # 1. Coba pindahkan ke Recycle Bin
                            send2trash(path_folder)
                            delete_success = True
                        except OSError as e:
                            # 2. Cek apakah terkunci (WinError 32 = File used by another process)
                            if hasattr(e, 'winerror') and e.winerror == 32:
                                locked_items.append(f"{judul_doc} (Sedang dibuka)")
                                continue # Skip, jangan hapus dari DB
                            elif hasattr(e, 'winerror') and e.winerror == 13: # Permission denied
                                locked_items.append(f"{judul_doc} (Akses ditolak)")
                                continue
                            else:
                                # 3. Jika gagal karena alasan lain, coba paksa hapus
                                try:
                                    shutil.rmtree(path_folder, ignore_errors=False)
                                    delete_success = True
                                except Exception as e_force:
                                    # Jika masih gagal juga, laporkan
                                    locked_items.append(f"{judul_doc} (Error: {str(e_force)})")
                                    continue
                    else:
                        # Folder fisik sudah tidak ada, anggap sukses dihapus
                        delete_success = True

                    # Hapus dari DB hanya jika fisik berhasil dihapus
                    if delete_success:
                        cursor.execute("DELETE FROM surat WHERE id=?", (db_id,))
                        deleted_count += 1

                db.commit()
                db.close()
                self.load_data()
                
                # --- Tampilkan Notifikasi Hasil ---
                if locked_items:
                    # Jika ada file yang terkunci
                    msg = "<b>Beberapa dokumen tidak bisa dihapus karena sedang digunakan:</b><br><br>"
                    msg += "<br>".join([f"• {item}" for item in locked_items])
                    msg += "<br><br>Mohon tutup file/folder tersebut dan coba lagi."
                    self.notifikasi_custom("Gagal Menghapus Sebagian", msg, QMessageBox.Icon.Warning)
                elif deleted_count > 0:
                    self.notifikasi_custom("Berhasil", f"{deleted_count} dokumen berhasil dihapus!", QMessageBox.Icon.Information)

            except Exception as e:
                self.notifikasi_custom("Error Sistem", str(e), QMessageBox.Icon.Critical)

    def notifikasi_custom(self, judul, pesan, ikon):
        dialog = QDialog(self)
        dialog.setWindowTitle("Pemberitahuan")
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        dialog.setFixedWidth(380)
        dialog.setStyleSheet("background-color: white; border-radius: 8px;")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(25, 25, 25, 25)
        
        emoji = "✅" 
        warna = "#27ae60"
        if ikon == QMessageBox.Icon.Warning: emoji, warna = "⚠️", "#f39c12"
        elif ikon == QMessageBox.Icon.Critical: emoji, warna = "❌", "#c0392b"

        lbl_icon = QLabel(emoji)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 55px; border: none; background: transparent;")
        layout.addWidget(lbl_icon)
        
        lbl_judul = QLabel(judul.upper())
        lbl_judul.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_judul.setStyleSheet(f"font-size: 20px; font-weight: 900; color: {warna}; border: none; background: transparent; margin-top: 5px;")
        layout.addWidget(lbl_judul)
        
        lbl_pesan = QLabel(pesan)
        lbl_pesan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_pesan.setWordWrap(True)
        lbl_pesan.setStyleSheet("font-size: 13px; color: #57606f; line-height: 1.4; border: none; background: transparent;")
        layout.addWidget(lbl_pesan)
        layout.addSpacing(15)

        btn = QPushButton("OK")
        btn.clicked.connect(dialog.accept)
        btn.setStyleSheet("QPushButton { background-color: #34495e; color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 14px; height: 45px; } QPushButton:hover { background-color: #2c3e50; }")
        layout.addWidget(btn)
        
        dialog.exec()