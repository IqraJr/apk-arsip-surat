import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QFrame, QAbstractItemView, QDialog, 
                             QStyledItemDelegate, QStyleOptionViewItem)
from PyQt6.QtCore import Qt
from .db_manager import connect_db

# --- DELEGATE KHUSUS ---
class PaddedItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        style = opt.widget.style()
        style.drawPrimitive(style.PrimitiveElement.PE_PanelItemViewItem, opt, painter, opt.widget)
        opt.rect.adjust(10, 5, -10, -5) 
        opt.state &= ~style.StateFlag.State_Selected
        opt.state &= ~style.StateFlag.State_HasFocus
        
        # Paksa text warna hitam saat menggambar item via delegate
        opt.palette.setColor(opt.palette.ColorRole.Text, Qt.GlobalColor.black)
        opt.palette.setColor(opt.palette.ColorRole.HighlightedText, Qt.GlobalColor.black) 
        
        style.drawControl(style.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

# --- CLASS UTAMA ---
class ManajemenKodeSurat(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_id = None 
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # --- HEADER ---
        header = QLabel("🔖 Referensi Kode Surat / Klasifikasi")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #000000;")
        self.main_layout.addWidget(header)

        # --- FORM INPUT ---
        self.form_frame = QFrame()
        self.form_frame.setStyleSheet("""
            QFrame { background-color: white; border-radius: 8px; border: 1px solid #dfe6e9; }
            QLabel { border: none; font-weight: bold; color: #000000; } 
            QLineEdit { border: 1px solid #b2bec3; border-radius: 4px; padding: 6px; color: black; background-color: white; }
        """)
        form_layout = QHBoxLayout(self.form_frame)
        
        # Input Kode
        v1 = QVBoxLayout()
        v1.addWidget(QLabel("Kode:"))
        self.ent_kode = QLineEdit()
        self.ent_kode.setPlaceholderText("Cth: 800.1.1")
        self.ent_kode.setFixedWidth(200)
        v1.addWidget(self.ent_kode)
        form_layout.addLayout(v1)

        # Input Keterangan
        v2 = QVBoxLayout()
        v2.addWidget(QLabel("Keterangan / Uraian:"))
        self.ent_ket = QLineEdit()
        self.ent_ket.setPlaceholderText("Cth: Surat Cuti Tahunan")
        v2.addWidget(self.ent_ket)
        form_layout.addLayout(v2)

        # Tombol
        v3 = QVBoxLayout()
        v3.addWidget(QLabel("")) 
        btn_box = QHBoxLayout()
        
        self.btn_simpan = QPushButton("💾 Simpan")
        self.btn_simpan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_simpan.setStyleSheet("""
            QPushButton { background-color: #0984e3; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #74b9ff; }
        """)
        self.btn_simpan.clicked.connect(self.simpan_data)
        
        self.btn_reset = QPushButton("🔄 Reset")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet("""
            QPushButton { background-color: #636e72; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #b2bec3; }
        """)
        self.btn_reset.clicked.connect(self.reset_form)
        
        btn_box.addWidget(self.btn_simpan)
        btn_box.addWidget(self.btn_reset)
        v3.addLayout(btn_box)
        form_layout.addLayout(v3)

        self.main_layout.addWidget(self.form_frame)

        # --- SEARCH BAR ---
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari Kode atau Keterangan...")
        self.search_input.setStyleSheet("padding: 8px; border: 1px solid #bdc3c7; border-radius: 20px; background: white; color: black;")
        self.search_input.textChanged.connect(self.load_data)
        self.main_layout.addWidget(self.search_input)

        # --- TABEL DATA ---
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["NO", "KODE", "KETERANGAN", "AKSI"])
        
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False) 
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        
        self.table.setItemDelegate(PaddedItemDelegate())
        
        header_table = self.table.horizontalHeader()
        header_table.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_table.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive) 
        self.table.setColumnWidth(1, 200) 
        header_table.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header_table.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed) 
        self.table.setColumnWidth(3, 120)
        
        self.table.setStyleSheet("""
            QTableWidget { 
                background-color: white; 
                color: #000000; 
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
                border-bottom: 1px solid #f1f2f6; 
                border-right: 1px solid #e0e0e0;
                color: #000000;
            }
            QTableWidget::item:selected { 
                background-color: #d1ecf1; 
                color: #000000; 
            }
        """)
        self.main_layout.addWidget(self.table)

    def create_copyable_label(self, text):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setStyleSheet("padding: 10px; background-color: transparent; color: #000000;") 
        return lbl

    def simpan_data(self):
        kode = self.ent_kode.text().strip()
        ket = self.ent_ket.text().strip()

        if not kode or not ket:
            self.notifikasi_custom("Peringatan", "Kode dan Keterangan wajib diisi!", QMessageBox.Icon.Warning)
            return

        try:
            db = connect_db()
            cursor = db.cursor()
            
            # --- [LOGIKA BARU: VALIDASI UNIK PADA KETERANGAN, BUKAN KODE] ---
            if self.selected_id:
                # Mode Update: Cek keterangan duplikat di ID lain
                cursor.execute("SELECT id FROM kode_surat WHERE keterangan=? AND id!=?", (ket, self.selected_id))
            else:
                # Mode Insert: Cek keterangan duplikat di semua data
                cursor.execute("SELECT id FROM kode_surat WHERE keterangan=?", (ket,))

            if cursor.fetchone():
                self.notifikasi_custom("Gagal", f"Keterangan '{ket}' sudah ada! Mohon gunakan deskripsi lain.", QMessageBox.Icon.Warning)
                db.close()
                return
            # ----------------------------------------------------------------

            # EKSEKUSI SIMPAN
            if self.selected_id: # UPDATE
                cursor.execute("UPDATE kode_surat SET kode=?, keterangan=? WHERE id=?", (kode, ket, self.selected_id))
                self.notifikasi_custom("Sukses", "Data berhasil diperbarui!", QMessageBox.Icon.Information)
            else: # INSERT
                cursor.execute("INSERT INTO kode_surat (kode, keterangan) VALUES (?, ?)", (kode, ket))
                self.notifikasi_custom("Sukses", "Kode baru berhasil disimpan!", QMessageBox.Icon.Information)
            
            db.commit()
            db.close()
            self.reset_form()
            self.load_data()
            
        except Exception as e:
            self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)

    def load_data(self):
        keyword = self.search_input.text().lower()
        try:
            db = connect_db()
            cursor = db.cursor()
            cursor.execute("SELECT id, kode, keterangan FROM kode_surat ORDER BY kode ASC")
            rows = cursor.fetchall()
            db.close()

            filtered_rows = [r for r in rows if keyword in r[1].lower() or keyword in r[2].lower()]

            self.table.setRowCount(0)
            for i, row in enumerate(filtered_rows):
                self.table.insertRow(i)
                
                # KOLOM 0: NO
                item_no = QTableWidgetItem(str(i + 1))
                item_no.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
                item_no.setForeground(Qt.GlobalColor.black)
                self.table.setItem(i, 0, item_no)
                
                # KOLOM 1: KODE
                lbl_kode = self.create_copyable_label(row[1])
                self.table.setCellWidget(i, 1, lbl_kode)
                
                # KOLOM 2: KETERANGAN
                lbl_ket = self.create_copyable_label(row[2])
                self.table.setCellWidget(i, 2, lbl_ket)
                
                # KOLOM 3: AKSI
                btn_widget = QWidget()
                btn_widget.setStyleSheet("background: transparent;")
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(2, 2, 2, 2)
                btn_layout.setSpacing(5)
                btn_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                
                btn_edit = QPushButton("✎")
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setToolTip("Edit")
                btn_edit.setStyleSheet("""
                    QPushButton { background: #f1c40f; border: none; border-radius: 4px; padding: 4px; color: white; font-weight: bold; }
                    QPushButton:hover { background: #f39c12; }
                """)
                btn_edit.clicked.connect(lambda _, r=row: self.isi_form_edit(r))
                
                btn_hapus = QPushButton("✖")
                btn_hapus.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_hapus.setToolTip("Hapus")
                btn_hapus.setStyleSheet("""
                    QPushButton { background: #ff7675; border: none; border-radius: 4px; padding: 4px; color: white; font-weight: bold; }
                    QPushButton:hover { background: #d63031; }
                """)
                btn_hapus.clicked.connect(lambda _, id_k=row[0]: self.hapus_data(id_k))
                
                btn_layout.addWidget(btn_edit)
                btn_layout.addWidget(btn_hapus)
                self.table.setCellWidget(i, 3, btn_widget)
            
            self.table.resizeRowsToContents()
                
        except Exception as e:
            print(f"Error load data: {e}")

    def isi_form_edit(self, row_data):
        self.selected_id = row_data[0]
        self.ent_kode.setText(row_data[1])
        self.ent_ket.setText(row_data[2])
        self.btn_simpan.setText("Update Data")
        self.btn_simpan.setStyleSheet("""
            QPushButton { background-color: #e67e22; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #d35400; }
        """)
        self.ent_kode.setFocus()

    def hapus_data(self, id_kode):
        dialog = QDialog(self)
        dialog.setWindowTitle("Konfirmasi Hapus")
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        dialog.setFixedWidth(380)
        dialog.setStyleSheet("background-color: white; border-radius: 8px;")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_icon = QLabel("🗑️")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 60px; border: none; background: transparent;")
        layout.addWidget(lbl_icon)
        
        lbl_judul = QLabel("HAPUS KODE?")
        lbl_judul.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_judul.setStyleSheet("font-size: 22px; font-weight: 900; color: #c0392b; border: none; background: transparent;")
        layout.addWidget(lbl_judul)
        
        lbl_pesan = QLabel("Data yang dihapus tidak bisa dikembalikan.")
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
                db = connect_db()
                cursor = db.cursor()
                cursor.execute("DELETE FROM kode_surat WHERE id=?", (id_kode,))
                db.commit()
                db.close()
                self.load_data()
                self.reset_form()
                self.notifikasi_custom("Berhasil", "Kode berhasil dihapus!", QMessageBox.Icon.Information)
            except Exception as e:
                self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)

    def reset_form(self):
        self.selected_id = None
        self.ent_kode.clear()
        self.ent_ket.clear()
        self.btn_simpan.setText("💾 Simpan")
        self.btn_simpan.setStyleSheet("""
            QPushButton { background-color: #0984e3; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #74b9ff; }
        """)

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
        if ikon == QMessageBox.Icon.Warning: emoji, warna_judul = "⚠️", "#f39c12"
        elif ikon == QMessageBox.Icon.Critical: emoji, warna_judul = "❌", "#c0392b"

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