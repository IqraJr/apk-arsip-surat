import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QFrame, QAbstractItemView, 
                             QDialog, QStyledItemDelegate, QStyleOptionViewItem)
from PyQt6.QtCore import Qt
from .db_manager import connect_db

# --- DELEGATE KHUSUS UNTUK PADDING TEXT (SAMA DENGAN SURAT KELUAR) ---
class PaddedItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        style = opt.widget.style()
        style.drawPrimitive(style.PrimitiveElement.PE_PanelItemViewItem, opt, painter, opt.widget)
        opt.rect.adjust(10, 5, -10, -5) # Padding teks
        opt.state &= ~style.StateFlag.State_Selected
        opt.state &= ~style.StateFlag.State_HasFocus
        style.drawControl(style.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

class ManajemenKodeSurat(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_id = None 
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(20)

        # --- 1. HEADER TITLE ---
        header_layout = QHBoxLayout()
        v_head = QVBoxLayout()
        
        lbl_title = QLabel("🔖 Referensi Kode Surat")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2d3436;")
        
        lbl_sub = QLabel("Kelola daftar klasifikasi untuk auto-fill nomor surat")
        lbl_sub.setStyleSheet("font-size: 13px; color: #636e72; margin-top: 2px;")
        
        v_head.addWidget(lbl_title)
        v_head.addWidget(lbl_sub)
        header_layout.addLayout(v_head)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)

        # --- 2. CARD INPUT (FORM) ---
        self.form_card = QFrame()
        self.form_card.setStyleSheet("""
            QFrame { 
                background-color: white; 
                border-radius: 10px; 
                border: 1px solid #dfe6e9; 
            }
            QLabel { 
                font-weight: bold; color: #2d3436; font-size: 12px; border: none;
            }
            QLineEdit { 
                border: 1px solid #dfe6e9; border-radius: 6px; 
                padding: 10px; background: #fdfdfd; color: black;
            }
            QLineEdit:focus { border: 1px solid #3498db; background: white; }
        """)
        
        form_layout = QHBoxLayout(self.form_card)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(15)
        
        # Input Kode
        v_kode = QVBoxLayout()
        v_kode.addWidget(QLabel("KODE SURAT"))
        self.ent_kode = QLineEdit()
        self.ent_kode.setPlaceholderText("Cth: 005")
        self.ent_kode.setFixedWidth(120)
        v_kode.addWidget(self.ent_kode)
        form_layout.addLayout(v_kode)

        # Input Keterangan
        v_ket = QVBoxLayout()
        v_ket.addWidget(QLabel("KETERANGAN / KLASIFIKASI"))
        self.ent_ket = QLineEdit()
        self.ent_ket.setPlaceholderText("Cth: Undangan Dinas")
        v_ket.addWidget(self.ent_ket)
        form_layout.addLayout(v_ket)

        # Tombol Aksi Form
        v_btn = QVBoxLayout()
        v_btn.addWidget(QLabel("")) # Spacer agar sejajar ke bawah
        btn_box = QHBoxLayout()
        
        self.btn_simpan = QPushButton("💾 Simpan")
        self.btn_simpan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_simpan.setFixedHeight(38)
        self.btn_simpan.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; border-radius: 6px; padding: 0 20px; border: none; }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        self.btn_simpan.clicked.connect(self.simpan_data)
        
        self.btn_reset = QPushButton("🔄 Reset")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setFixedHeight(38)
        self.btn_reset.setStyleSheet("""
            QPushButton { background-color: #95a5a6; color: white; font-weight: bold; border-radius: 6px; padding: 0 15px; border: none; }
            QPushButton:hover { background-color: #7f8c8d; }
        """)
        self.btn_reset.clicked.connect(self.reset_form)
        
        btn_box.addWidget(self.btn_simpan)
        btn_box.addWidget(self.btn_reset)
        v_btn.addLayout(btn_box)
        form_layout.addLayout(v_btn)

        self.main_layout.addWidget(self.form_card)

        # --- 3. SEARCH BAR ---
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari Kode atau Keterangan...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 12px; border: 1px solid #dcdde1; border-radius: 8px; 
                background: white; color: black; font-size: 13px; margin-top: 10px;
            }
            QLineEdit:focus { border: 1px solid #a29bfe; }
        """)
        self.search_input.textChanged.connect(self.load_data)
        self.main_layout.addWidget(self.search_input)

        # --- 4. TABEL ---
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["NO", "KODE", "KETERANGAN", "AKSI"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        
        self.table.setItemDelegate(PaddedItemDelegate())

        header_table = self.table.horizontalHeader()
        header_table.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 60)
        header_table.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_table.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header_table.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 140)
        
        self.table.setStyleSheet("""
            QTableWidget { background-color: white; color: #2d3436; border: none; outline: none; }
            QHeaderView::section { 
                background-color: #7132CA; color: white; padding: 12px; font-weight: bold; 
                border: none; text-transform: uppercase; border-right: 1px solid #9b59b6;
            }
            QTableWidget::item { border-bottom: 1px solid #f1f2f6; border-right: 1px solid #e0e0e0; }
            QTableWidget::item:selected { background-color: #d1ecf1; color: #0c5460; }
        """)
        self.main_layout.addWidget(self.table)

    def simpan_data(self):
        kode = self.ent_kode.text().strip()
        ket = self.ent_ket.text().strip()

        if not kode or not ket:
            self.notifikasi_custom("Peringatan", "Kode dan Keterangan wajib diisi!", QMessageBox.Icon.Warning)
            return

        try:
            db = connect_db()
            cursor = db.cursor()
            
            if self.selected_id: # MODE UPDATE
                cursor.execute("UPDATE kode_surat SET kode=?, keterangan=? WHERE id=?", (kode, ket, self.selected_id))
                self.notifikasi_custom("Sukses", "Data berhasil diperbarui!", QMessageBox.Icon.Information)
            else: # MODE INSERT BARU
                cursor.execute("SELECT id FROM kode_surat WHERE kode=?", (kode,))
                if cursor.fetchone():
                    self.notifikasi_custom("Gagal", f"Kode '{kode}' sudah ada!", QMessageBox.Icon.Warning)
                    db.close()
                    return
                
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
                
                item_no = QTableWidgetItem(str(i + 1))
                item_no.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, 0, item_no)
                
                self.table.setItem(i, 1, QTableWidgetItem(row[1]))
                self.table.setItem(i, 2, QTableWidgetItem(row[2]))
                
                # Widget Tombol Aksi
                btn_widget = QWidget()
                btn_widget.setStyleSheet("background: transparent;")
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(5, 5, 5, 5)
                btn_layout.setSpacing(5)
                
                btn_edit = QPushButton("✏️")
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setToolTip("Edit Data")
                btn_edit.setStyleSheet("""
                    QPushButton { background: #f1c40f; border-radius: 4px; padding: 6px; }
                    QPushButton:hover { background: #f39c12; }
                """)
                btn_edit.clicked.connect(lambda _, r=row: self.isi_form_edit(r))
                
                btn_hapus = QPushButton("🗑")
                btn_hapus.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_hapus.setToolTip("Hapus Data")
                btn_hapus.setStyleSheet("""
                    QPushButton { background: #ff7675; border-radius: 4px; padding: 6px; color: white; }
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
            QPushButton { background-color: #e67e22; color: white; font-weight: bold; border-radius: 6px; padding: 0 20px; border: none; }
            QPushButton:hover { background-color: #d35400; }
        """)
        self.ent_kode.setFocus()

    def hapus_data(self, id_kode):
        # --- UI POPUP CUSTOM ALA SURAT KELUAR ---
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
        
        lbl_judul = QLabel("HAPUS KODE?")
        lbl_judul.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_judul.setStyleSheet("font-size: 22px; font-weight: 900; color: #c0392b; border: none; background: transparent; margin-top: 5px;")
        layout.addWidget(lbl_judul)
        
        lbl_pesan = QLabel("Anda akan menghapus kode referensi ini.<br>Data yang sudah dihapus tidak dapat dikembalikan.")
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
        btn_batal.setStyleSheet("""
            QPushButton {
                background-color: #ecf0f1; color: #2c3e50; border: 1px solid #bdc3c7; 
                border-radius: 6px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #dfe6e9; }
        """)
        btn_batal.clicked.connect(dialog.reject)
        
        btn_hapus = QPushButton("Ya, Hapus")
        btn_hapus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_hapus.setFixedHeight(40)
        btn_hapus.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c; color: white; border: none; 
                border-radius: 6px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
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
                self.notifikasi_custom("Berhasil", "Kode surat berhasil dihapus!", QMessageBox.Icon.Information)
            except Exception as e:
                self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)

    def reset_form(self):
        self.selected_id = None
        self.ent_kode.clear()
        self.ent_ket.clear()
        self.btn_simpan.setText("💾 Simpan")
        self.btn_simpan.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; border-radius: 6px; padding: 0 20px; border: none; }
            QPushButton:hover { background-color: #2ecc71; }
        """)

    def notifikasi_custom(self, judul, pesan, ikon):
        dialog = QDialog(self)
        dialog.setWindowTitle(judul)
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