import os
import shutil
import pandas as pd
import tempfile 
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QLineEdit, QHeaderView, QMessageBox, QAbstractItemView,
                             QFileDialog, QDialog, QCheckBox, QComboBox, QStyledItemDelegate, QStyleOptionViewItem)
from PyQt6.QtCore import Qt, QDate
from .db_manager import connect_db
from .form_surat import FormTambahSurat
from .settings import get_folder_path, set_folder_path

# --- DELEGATE KHUSUS UNTUK PADDING TEXT ---
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

# --- CLASS SORTING ---
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
# ---------------------

class SuratKeluar(QWidget):
    def __init__(self):
        super().__init__()
        self.all_data = []      
        self.filtered_data = [] 
        self.current_page = 1
        self.rows_per_page = 10
        
        self.create_check_icon()
        self.create_arrow_icon()
        
        self.init_ui()

    def create_check_icon(self):
        svg_data = """<?xml version="1.0" encoding="UTF-8"?>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">
            <polyline points="20 6 9 17 4 12"></polyline>
        </svg>"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False)
        temp_file.write(svg_data)
        temp_file.close()
        self.check_icon_path = temp_file.name.replace('\\', '/')

    def create_arrow_icon(self):
        svg_data = """<?xml version="1.0" encoding="UTF-8"?>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">
            <polyline points="6 9 12 15 18 9"></polyline>
        </svg>"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False)
        temp_file.write(svg_data)
        temp_file.close()
        self.arrow_icon_path = temp_file.name.replace('\\', '/')

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(15)

        # --- HEADER ---
        header_layout = QHBoxLayout()
        judul_container = QVBoxLayout()
        
        title = QLabel("📤 Manajemen Surat Keluar")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2d3436;")
        
        self.lbl_folder = QLabel()
        self.lbl_folder.setStyleSheet("color: #636e72; font-size: 12px; font-style: italic;")
        self.update_label_folder()
        
        judul_container.addWidget(title)
        judul_container.addWidget(self.lbl_folder)
        header_layout.addLayout(judul_container)
        header_layout.addStretch()

        self.btn_ganti_folder = QPushButton("📂 Ganti Folder")
        self.btn_ganti_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ganti_folder.setStyleSheet("""
            QPushButton {
                background-color: #0984e3; color: white; padding: 8px 15px; 
                border-radius: 6px; font-size: 12px;
            }
            QPushButton:hover { background-color: #74b9ff; }
        """)
        self.btn_ganti_folder.clicked.connect(self.aksi_ganti_folder)
        header_layout.addWidget(self.btn_ganti_folder)

        self.btn_tambah = QPushButton("+ Tambah Surat Keluar")
        self.btn_tambah.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tambah.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; padding: 10px 20px; 
                font-weight: bold; border-radius: 8px; border: none;
            }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        self.btn_tambah.clicked.connect(self.aksi_tambah)
        header_layout.addWidget(self.btn_tambah)
        self.main_layout.addLayout(header_layout)

        # --- SEARCH & FILTER ---
        search_filter_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari Nomor Surat, Tujuan, atau Perihal...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 12px; border: 1px solid #dcdde1; border-radius: 8px; 
                background: white; color: black; font-size: 13px;
            }
        """)
        self.search_input.textChanged.connect(self.filter_data)
        
        self.combo_tahun = QComboBox()
        self.combo_tahun.addItem("Semua Tahun")
        self.combo_tahun.setFixedWidth(150)
        self.combo_tahun.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_tahun.setStyleSheet(f"""
            QComboBox {{
                padding: 10px; border: 1px solid #dcdde1; border-radius: 8px;
                background-color: white; color: black; font-size: 13px;
            }}
            QComboBox::drop-down {{ border: none; background: transparent; width: 30px; }}
            QComboBox::down-arrow {{ image: url({self.arrow_icon_path}); width: 16px; height: 16px; }}
            QComboBox QAbstractItemView {{
                background-color: white; color: black;
                selection-background-color: #dfe6e9; selection-color: black;
                border: 1px solid #dcdde1; outline: none;
            }}
        """)
        self.combo_tahun.currentTextChanged.connect(self.filter_data)

        search_filter_layout.addWidget(self.search_input)
        search_filter_layout.addWidget(self.combo_tahun)
        self.main_layout.addLayout(search_filter_layout)

        # --- TABLE ---
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "", "NO", "TANGGAL\nKIRIM", "KEPADA", "NOMOR", "TANGGAL\nSURAT", "PERIHAL", "KET", "AKSI"
        ])
        
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False) 
        self.table.setWordWrap(True) 
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        
        # --- [FIXED] GUNAKAN DELEGATE UNTUK PADDING TEXT ---
        self.table.setItemDelegate(PaddedItemDelegate())
        # ---------------------------------------------------

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed) # Checkbox
        self.table.setColumnWidth(0, 40)
        
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # NO
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # TGL KIRIM
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) # TGL SURAT
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed) # AKSI
        self.table.setColumnWidth(8, 170)
        
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
                /* Padding ini backup, tapi Delegate yang akan handle utamanya */
                border-bottom: 1px solid #f1f2f6; 
                border-right: 1px solid #e0e0e0;
            }
            QTableWidget::item:selected { 
                background-color: #d1ecf1; 
                color: #0c5460; 
            }
            QToolTip { 
                color: #000000; 
                background-color: #ffffff; 
                border: 1px solid #bdc3c7; 
            }
        """)
        self.main_layout.addWidget(self.table)

        # --- PAGINATION ---
        pagination_layout = QHBoxLayout()
        self.btn_prev = QPushButton("◀")
        self.btn_next = QPushButton("▶")
        self.label_page = QLabel("Halaman 1 of 1")
        self.label_page.setStyleSheet("color: black; font-weight: bold;")
        
        style_nav = "QPushButton { color: black; background:#dfe4ea; border-radius:5px; padding:5px 15px; font-weight:bold; }"
        self.btn_prev.setStyleSheet(style_nav)
        self.btn_next.setStyleSheet(style_nav)
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_next.clicked.connect(self.next_page)
        
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addWidget(self.label_page)
        pagination_layout.addWidget(self.btn_next)
        pagination_layout.addStretch()
        self.main_layout.addLayout(pagination_layout)

        # --- BOTTOM ---
        bottom_layout = QHBoxLayout()
        
        self.btn_delete = QPushButton("🗑 Hapus Terpilih")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b; color: white; padding: 10px 20px; 
                font-weight: bold; border-radius: 8px; border: none;
            }
            QPushButton:hover { background-color: #ff5252; }
            QPushButton:pressed { background-color: #e1b12c; }
        """)
        self.btn_delete.clicked.connect(self.aksi_hapus)
        
        self.btn_excel = QPushButton("📊 Export Excel")
        self.btn_excel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_excel.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; padding: 10px 20px; 
                font-weight: bold; border-radius: 8px; border: none;
            }
            QPushButton:hover { background-color: #2ecc71; }
            QPushButton:pressed { background-color: #219150; }
        """)
        self.btn_excel.clicked.connect(self.export_to_excel)
        
        bottom_layout.addWidget(self.btn_delete)
        bottom_layout.addWidget(self.btn_excel)
        bottom_layout.addStretch()
        self.main_layout.addLayout(bottom_layout)
        
        self.load_data()

    def update_label_folder(self):
        path = get_folder_path("keluar")
        self.lbl_folder.setText(f"Penyimpanan: {path}")

    def aksi_ganti_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih Folder Penyimpanan Surat Keluar")
        if folder:
            set_folder_path("keluar", folder)
            self.update_label_folder()
            self.notifikasi_custom("Sukses", "Lokasi penyimpanan Surat Keluar berhasil diubah!", QMessageBox.Icon.Information)

    def load_data(self):
        try:
            db = connect_db()
            if db:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT id, tanggal, asal_surat, nomor_surat, tanggal_surat, judul_surat, keterangan, file_path 
                    FROM surat WHERE kategori='keluar' ORDER BY id DESC
                """)
                self.all_data = cursor.fetchall()
                self.populate_tahun_filter()
                self.current_page = 1
                self.filter_data() 
                db.close()
        except Exception as e: print(e)

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
        index = self.combo_tahun.findText(current_selection)
        if index >= 0: self.combo_tahun.setCurrentIndex(index)
        else: self.combo_tahun.setCurrentIndex(0)
        self.combo_tahun.blockSignals(False)

    def filter_data(self, *args):
        keyword = self.search_input.text().lower()
        selected_tahun = self.combo_tahun.currentText()
        self.filtered_data = []
        for row in self.all_data:
            text_data = f"{row[2]} {row[3]} {row[5]} {row[6]}".lower() 
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
        self.filtered_data = data
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
            
            # 0. Checkbox
            dummy_item = QTableWidgetItem()
            dummy_item.setFlags(Qt.ItemFlag.ItemIsEnabled) 
            self.table.setItem(i, 0, dummy_item)

            chk_container = QWidget()
            # --- [FIXED] BACKGROUND TRANSPARENT ---
            chk_container.setStyleSheet("background-color: transparent;") 
            # --------------------------------------
            chk_layout = QHBoxLayout(chk_container)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            chk_box = QCheckBox()
            chk_box.setProperty("db_id", row[0])
            chk_box.setCursor(Qt.CursorShape.PointingHandCursor)
            chk_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            
            chk_box.setStyleSheet(f"""
                QCheckBox::indicator {{
                    width: 18px; height: 18px;
                    border: 1px solid #bdc3c7; background-color: white; border-radius: 3px;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #27ae60; border: 1px solid #27ae60;
                    image: url({self.check_icon_path});
                }}
            """)
            chk_layout.addWidget(chk_box)
            self.table.setCellWidget(i, 0, chk_container)

            # 1. No (Numeric)
            no_item = NumericTableWidgetItem(str(start_idx + i + 1))
            no_item.setData(Qt.ItemDataRole.UserRole, row[0])
            no_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop) 
            self.table.setItem(i, 1, no_item)

            # Data 2-7
            for j in range(1, 7):
                val = str(row[j]) if row[j] else ""
                if j in [1, 4]: 
                    try:
                        d = QDate.fromString(val, "yyyy-MM-dd")
                        if d.isValid(): val = d.toString("dd/MM/yyyy")
                    except: pass
                
                if j in [1, 4]: item = DateTableWidgetItem(val)
                else: item = QTableWidgetItem(val)
                
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                item.setToolTip(val)
                self.table.setItem(i, j+1, item)
            
            # 8. Aksi
            btn_container = QWidget()
            btn_container.setStyleSheet("background: transparent;")
            btn_l = QHBoxLayout(btn_container)
            btn_l.setContentsMargins(5, 5, 5, 5)
            btn_l.setSpacing(5)
            btn_l.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
            
            btn_view = QPushButton("Lihat")
            btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_view.setStyleSheet("""
                QPushButton { background: #5c7cfa; color: white; border-radius: 4px; padding: 5px 10px; font-weight: bold; font-size: 11px; }
                QPushButton:hover { background: #4263eb; }
            """)
            btn_view.clicked.connect(lambda checked, p=row[7]: self.buka_berkas(p))
            
            btn_edit = QPushButton("✏️ Edit")
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("""
                QPushButton { background: #f1c40f; color: white; border-radius: 4px; padding: 5px 10px; font-weight: bold; font-size: 11px; }
                QPushButton:hover { background: #f39c12; }
            """)
            btn_edit.clicked.connect(lambda checked, r=row: self.aksi_edit(r))
            
            btn_l.addWidget(btn_view)
            btn_l.addWidget(btn_edit)
            self.table.setCellWidget(i, 8, btn_container)
        
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

    def export_to_excel(self):
        data_exp = self.filtered_data if self.filtered_data else self.all_data
        if not data_exp: return
        path, _ = QFileDialog.getSaveFileName(self, "Simpan Laporan", f"Laporan_Surat_Keluar_{datetime.now().strftime('%d%m%Y')}.xlsx", "Excel Files (*.xlsx)")
        if path:
            try:
                df = pd.DataFrame(data_exp, columns=["ID", "Tgl Kirim", "Kepada", "Nomor Surat", "Tgl Surat", "Perihal", "Ket", "Path"])
                df.to_excel(path, index=False)
                self.notifikasi_custom("Sukses", "Laporan berhasil disimpan!", QMessageBox.Icon.Information)
            except Exception as e: self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)

    def aksi_tambah(self):
        dialog = FormTambahSurat(self, kategori="Keluar")
        if dialog.exec():
            tgl_kirim = dialog.ent_tanggal.date().toString("yyyy-MM-dd")
            kepada = dialog.ent_pihak.text().strip()
            nomor = dialog.ent_nomor.text().strip()
            tgl_surat = dialog.ent_tgl_surat.date().toString("yyyy-MM-dd")
            raw_perihal = dialog.ent_perihal.currentText().strip()
            if " - " in raw_perihal: perihal = raw_perihal.rsplit(" - ", 1)[0]
            else: perihal = raw_perihal
            ket = dialog.ent_keterangan.text().strip()
            path_asal = dialog.file_path

            if not nomor or not path_asal:
                self.notifikasi_custom("Peringatan", "Nomor dan Berkas wajib diisi!", QMessageBox.Icon.Warning)
                return

            try:
                up_dir = get_folder_path("keluar") 
                os.makedirs(up_dir, exist_ok=True)
                ext = os.path.splitext(path_asal)[1]
                path_dest = os.path.join(up_dir, f"OUT_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
                shutil.copy(path_asal, path_dest)
                
                db = connect_db()
                cursor = db.cursor()
                cursor.execute("INSERT INTO surat (nomor_surat, judul_surat, asal_surat, kategori, tanggal, tanggal_surat, keterangan, file_path) VALUES (?, ?, ?, 'keluar', ?, ?, ?, ?)", 
                               (nomor, perihal, kepada, tgl_kirim, tgl_surat, ket, path_dest))
                db.commit()
                db.close()
                self.load_data()
                self.notifikasi_custom("Berhasil", "Data berhasil diarsipkan!", QMessageBox.Icon.Information)
            except Exception as e: self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)

    def aksi_edit(self, data):
        dialog = FormTambahSurat(self, kategori="Keluar")
        dialog.setWindowTitle("Edit Surat Keluar")
        path_lama = data[7] 
        dialog.ent_tanggal.setDate(QDate.fromString(data[1], "yyyy-MM-dd"))
        dialog.ent_pihak.setText(str(data[2]))
        dialog.ent_nomor.setText(str(data[3]))
        dialog.ent_tgl_surat.setDate(QDate.fromString(data[4], "yyyy-MM-dd"))
        dialog.ent_perihal.setCurrentText(str(data[5])) 
        dialog.ent_keterangan.setText(str(data[6]))
        dialog.file_path = path_lama

        if dialog.exec():
            try:
                raw_perihal = dialog.ent_perihal.currentText().strip()
                if " - " in raw_perihal: perihal = raw_perihal.rsplit(" - ", 1)[0]
                else: perihal = raw_perihal
                
                path_baru_input = dialog.file_path
                final_path = path_lama
                if path_baru_input != path_lama:
                    up_dir = get_folder_path("keluar")
                    os.makedirs(up_dir, exist_ok=True)
                    ext = os.path.splitext(path_baru_input)[1]
                    final_path = os.path.join(up_dir, f"OUT_EDIT_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
                    shutil.copy(path_baru_input, final_path)

                db = connect_db()
                cursor = db.cursor()
                cursor.execute("UPDATE surat SET tanggal=?, asal_surat=?, nomor_surat=?, tanggal_surat=?, judul_surat=?, keterangan=?, file_path=? WHERE id=?", 
                               (dialog.ent_tanggal.date().toString("yyyy-MM-dd"), dialog.ent_pihak.text(), dialog.ent_nomor.text(), dialog.ent_tgl_surat.date().toString("yyyy-MM-dd"), perihal, dialog.ent_keterangan.text(), final_path, data[0]))
                db.commit()
                db.close()
                self.load_data()
                self.notifikasi_custom("Sukses", "Data berhasil diperbarui!", QMessageBox.Icon.Information)
            except Exception as e: self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)
                
    def aksi_hapus(self):
        ids_to_delete = []
        # Cari item yang dicentang
        for i in range(self.table.rowCount()):
            widget = self.table.cellWidget(i, 0)
            if widget:
                chk = widget.findChild(QCheckBox) 
                if chk and chk.isChecked(): ids_to_delete.append(chk.property("db_id"))

        if not ids_to_delete:
            self.notifikasi_custom("Peringatan", "Pilih data yang ingin dihapus!", QMessageBox.Icon.Warning)
            return
            
        msg = QMessageBox(self)
        msg.setWindowTitle("Konfirmasi Hapus")
        msg.setText(f"Yakin menghapus {len(ids_to_delete)} data terpilih?\nData dan file fisik akan dihapus permanen.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setStyleSheet("""QMessageBox { background-color: #ffffff; } QMessageBox QLabel { color: #000000; } QMessageBox QPushButton { min-width: 90px; }""")
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            try:
                db = connect_db()
                cursor = db.cursor()
                count = 0
                error_files = [] # List untuk mencatat file yang gagal hapus karena dibuka
                
                for db_id in ids_to_delete:
                    cursor.execute("SELECT file_path FROM surat WHERE id=?", (db_id,))
                    res = cursor.fetchone()
                    
                    file_terhapus = True
                    # Cek apakah file fisik ada
                    if res and res[0] and os.path.exists(res[0]):
                        try:
                            os.remove(res[0]) # Coba hapus file fisik
                        except PermissionError:
                            # JIKA ERROR (FILE SEDANG DIBUKA), JANGAN CRASH
                            file_terhapus = False
                            error_files.append(os.path.basename(res[0]))
                    
                    # Hanya hapus data di database jika file fisiknya sukses terhapus (atau memang tidak ada)
                    if file_terhapus:
                        cursor.execute("DELETE FROM surat WHERE id=?", (db_id,))
                        count += 1

                db.commit()
                db.close()
                self.load_data()
                
                # Tampilkan pesan sukses
                if count > 0:
                    self.notifikasi_custom("Berhasil", f"{count} data berhasil dihapus!", QMessageBox.Icon.Information)
                
                # Tampilkan pesan peringatan jika ada file yang gagal dihapus
                if error_files:
                    list_file = "\n".join(error_files[:3]) # Tampilkan max 3 nama file
                    if len(error_files) > 3: list_file += "\n...dan lainnya."
                    self.notifikasi_custom("Gagal Menghapus File", 
                                           f"File berikut sedang dibuka oleh aplikasi lain:\n{list_file}\n\nSilakan tutup file tersebut lalu coba lagi.", 
                                           QMessageBox.Icon.Warning)

            except Exception as e: self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)

    def buka_berkas(self, path):
        if path and os.path.exists(path): os.startfile(os.path.abspath(path))
        else: self.notifikasi_custom("Error", "File tidak ditemukan!", QMessageBox.Icon.Critical)

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
        elif ikon == QMessageBox.Icon.Question: emoji, warna = "❓", "#3498db"

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