import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QFrame, QAbstractItemView)
from PyQt6.QtCore import Qt
from .db_manager import connect_db

class ManajemenKodeSurat(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_id = None # Untuk menyimpan ID saat mode Edit
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # --- HEADER ---
        header = QLabel("🔖 Referensi Kode Surat / Klasifikasi")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #2d3436;")
        self.main_layout.addWidget(header)

        # --- FORM INPUT (Card Style) ---
        self.form_frame = QFrame()
        self.form_frame.setStyleSheet("""
            QFrame { background-color: white; border-radius: 8px; border: 1px solid #dfe6e9; }
            QLabel { border: none; font-weight: bold; color: #636e72; }
            QLineEdit { border: 1px solid #b2bec3; border-radius: 4px; padding: 6px; color: black; }
        """)
        form_layout = QHBoxLayout(self.form_frame)
        
        # Input Kode (Contoh: 800.1.1)
        v1 = QVBoxLayout()
        v1.addWidget(QLabel("Kode:"))
        self.ent_kode = QLineEdit()
        self.ent_kode.setPlaceholderText("Cth: 800.1.1")
        self.ent_kode.setFixedWidth(150)
        v1.addWidget(self.ent_kode)
        form_layout.addLayout(v1)

        # Input Keterangan (Contoh: Cuti Tahunan)
        v2 = QVBoxLayout()
        v2.addWidget(QLabel("Keterangan / Uraian:"))
        self.ent_ket = QLineEdit()
        self.ent_ket.setPlaceholderText("Cth: Surat Cuti Tahunan")
        v2.addWidget(self.ent_ket)
        form_layout.addLayout(v2)

        # Tombol Simpan & Reset
        v3 = QVBoxLayout()
        v3.addWidget(QLabel("")) # Spacer label
        btn_box = QHBoxLayout()
        
        self.btn_simpan = QPushButton("💾 Simpan")
        self.btn_simpan.setStyleSheet("background-color: #0984e3; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")
        self.btn_simpan.clicked.connect(self.simpan_data)
        
        self.btn_reset = QPushButton("🔄 Reset")
        self.btn_reset.setStyleSheet("background-color: #636e72; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")
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
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        header_table = self.table.horizontalHeader()
        header_table.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_table.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_table.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header_table.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setStyleSheet("""
            QTableWidget { background-color: white; gridline-color: #f1f2f6; color: black; }
            QHeaderView::section { background-color: #2d3436; color: white; padding: 8px; font-weight: bold; }
            QTableWidget::item { padding: 5px; }
        """)
        self.main_layout.addWidget(self.table)

    def simpan_data(self):
        kode = self.ent_kode.text().strip()
        ket = self.ent_ket.text().strip()

        if not kode or not ket:
            self.notifikasi("Peringatan", "Kode dan Keterangan wajib diisi!", QMessageBox.Icon.Warning)
            return

        try:
            db = connect_db()
            cursor = db.cursor()
            
            if self.selected_id: # MODE UPDATE
                cursor.execute("UPDATE kode_surat SET kode=?, keterangan=? WHERE id=?", (kode, ket, self.selected_id))
                self.notifikasi("Sukses", "Data berhasil diperbarui!", QMessageBox.Icon.Information)
            else: # MODE INSERT BARU
                # Cek duplikat kode
                cursor.execute("SELECT id FROM kode_surat WHERE kode=?", (kode,))
                if cursor.fetchone():
                    self.notifikasi("Gagal", f"Kode '{kode}' sudah ada!", QMessageBox.Icon.Warning)
                    db.close()
                    return
                
                cursor.execute("INSERT INTO kode_surat (kode, keterangan) VALUES (?, ?)", (kode, ket))
                self.notifikasi("Sukses", "Kode baru berhasil disimpan!", QMessageBox.Icon.Information)
            
            db.commit()
            db.close()
            self.reset_form()
            self.load_data()
            
        except Exception as e:
            self.notifikasi("Error", str(e), QMessageBox.Icon.Critical)

    def load_data(self):
        keyword = self.search_input.text().lower()
        try:
            db = connect_db()
            cursor = db.cursor()
            cursor.execute("SELECT id, kode, keterangan FROM kode_surat ORDER BY kode ASC")
            rows = cursor.fetchall()
            db.close()

            # Filter data di Python (simple)
            filtered_rows = [r for r in rows if keyword in r[1].lower() or keyword in r[2].lower()]

            self.table.setRowCount(0)
            for i, row in enumerate(filtered_rows):
                self.table.insertRow(i)
                # NO
                self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                # KODE
                self.table.setItem(i, 1, QTableWidgetItem(row[1]))
                # KETERANGAN
                self.table.setItem(i, 2, QTableWidgetItem(row[2]))
                
                # AKSI (Edit & Hapus)
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(2, 2, 2, 2)
                btn_layout.setSpacing(5)
                
                btn_edit = QPushButton("✎")
                btn_edit.setToolTip("Edit")
                btn_edit.setStyleSheet("background: #f1c40f; border: none; border-radius: 4px; padding: 4px;")
                btn_edit.clicked.connect(lambda _, r=row: self.isi_form_edit(r))
                
                btn_hapus = QPushButton("✖")
                btn_hapus.setToolTip("Hapus")
                btn_hapus.setStyleSheet("background: #ff7675; border: none; border-radius: 4px; padding: 4px; color: white;")
                btn_hapus.clicked.connect(lambda _, id_k=row[0]: self.hapus_data(id_k))
                
                btn_layout.addWidget(btn_edit)
                btn_layout.addWidget(btn_hapus)
                self.table.setCellWidget(i, 3, btn_widget)
                
        except Exception as e:
            print(f"Error load data: {e}")

    def isi_form_edit(self, row_data):
        self.selected_id = row_data[0]
        self.ent_kode.setText(row_data[1])
        self.ent_ket.setText(row_data[2])
        self.btn_simpan.setText("Update Data")
        self.btn_simpan.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")
        self.ent_kode.setFocus()

    def hapus_data(self, id_kode):
        msg = QMessageBox(self)
        msg.setWindowTitle("Hapus Kode")
        msg.setText("Yakin ingin menghapus kode referensi ini?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setStyleSheet("QMessageBox { background: white; } QLabel { color: black; }")
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            try:
                db = connect_db()
                cursor = db.cursor()
                cursor.execute("DELETE FROM kode_surat WHERE id=?", (id_kode,))
                db.commit()
                db.close()
                self.load_data()
                self.reset_form() # Reset jika sedang mode edit
            except Exception as e:
                self.notifikasi("Error", str(e), QMessageBox.Icon.Critical)

    def reset_form(self):
        self.selected_id = None
        self.ent_kode.clear()
        self.ent_ket.clear()
        self.btn_simpan.setText("💾 Simpan")
        self.btn_simpan.setStyleSheet("background-color: #0984e3; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")

    def notifikasi(self, judul, pesan, ikon):
        msg = QMessageBox(self)
        msg.setWindowTitle(judul)
        msg.setText(pesan)
        msg.setIcon(ikon)
        msg.setStyleSheet("QMessageBox { background: white; } QLabel { color: black; }")
        msg.exec()