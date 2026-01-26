import os
import shutil
import pandas as pd
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QLineEdit, QHeaderView, QMessageBox, QAbstractItemView,
                             QFileDialog, QDialog)
from PyQt6.QtCore import Qt, QDate
from .db_manager import connect_db
from .form_surat import FormTambahSurat
from .settings import get_folder_path, set_folder_path

class SuratMasuk(QWidget):
    def __init__(self):
        super().__init__()
        self.all_data = []      # Data asli dari DB
        self.filtered_data = [] # Data filter
        self.current_page = 1
        self.rows_per_page = 10
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(15)

        # --- HEADER ---
        header_layout = QHBoxLayout()
        
        # Container untuk Judul dan Info Folder
        judul_container = QVBoxLayout()
        
        title = QLabel("📥 Manajemen Surat Masuk")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2d3436;")
        
        # WIDGET BARU: Label Info Folder
        self.lbl_folder = QLabel()
        self.lbl_folder.setStyleSheet("color: #636e72; font-size: 12px; font-style: italic;")
        self.update_label_folder() # Panggil fungsi update text
        
        judul_container.addWidget(title)
        judul_container.addWidget(self.lbl_folder)
        
        header_layout.addLayout(judul_container)
        header_layout.addStretch()

        # WIDGET BARU: Tombol Ganti Folder
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

        self.btn_tambah = QPushButton("+ Tambah Surat Masuk")
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

        # --- SEARCH BAR ---
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari Nomor Surat, Perihal, atau Keterangan...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 12px; border: 1px solid #dcdde1; border-radius: 8px; 
                background: white; color: black; font-size: 13px;
            }
        """)
        self.search_input.textChanged.connect(self.filter_data)
        self.main_layout.addWidget(self.search_input)

        # --- TABLE (8 KOLOM) ---
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "NO", "TANGGAL\nTERIMA", "DARI", "NOMOR", "TANGGAL\nSURAT", "PERIHAL", "KET", "AKSI"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # NO
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # TGL TERIMA
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # TGL SURAT
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents) # AKSI
        
        self.table.setStyleSheet("""
            QTableWidget { background-color: white; color: #2d3436; border: none; outline: none; }
            QHeaderView::section { 
                background-color: #7132CA; color: white; padding: 12px; 
                font-weight: bold; border: none; text-transform: uppercase;
            }
            QTableWidget::item:selected { background-color: #C47BE4; color: white; }
            QTableWidget::item { padding: 10px; border-bottom: 1px solid #f1f2f6; }
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
        self.btn_delete.setStyleSheet("background-color: #ff6b6b; color: white; padding: 10px 20px; font-weight: bold; border-radius: 8px; border: none;")
        self.btn_delete.clicked.connect(self.aksi_hapus)
        
        self.btn_excel = QPushButton("📊 Export Excel")
        self.btn_excel.setStyleSheet("background-color: #27ae60; color: white; padding: 10px 20px; font-weight: bold; border-radius: 8px; border: none;")
        self.btn_excel.clicked.connect(self.export_to_excel)
        
        bottom_layout.addWidget(self.btn_delete)
        bottom_layout.addWidget(self.btn_excel)
        bottom_layout.addStretch()
        self.main_layout.addLayout(bottom_layout)

        self.load_data()

    # --- FUNGSI PENDUKUNG (Dipisah dari init_ui) ---

    def update_label_folder(self):
        path = get_folder_path("masuk")
        self.lbl_folder.setText(f"Penyimpanan: {path}")

    def aksi_ganti_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih Folder Penyimpanan Surat Masuk")
        if folder:
            set_folder_path("masuk", folder)
            self.update_label_folder()
            self.notifikasi_custom("Sukses", "Lokasi penyimpanan Surat Masuk berhasil diubah!", QMessageBox.Icon.Information)

    def load_data(self):
        try:
            db = connect_db()
            if db:
                cursor = db.cursor()
                # 0:id, 1:tgl_terima, 2:dari, 3:nomor, 4:tgl_surat, 5:perihal, 6:ket, 7:path
                cursor.execute("""
                    SELECT id, tanggal, asal_surat, nomor_surat, tanggal_surat, judul_surat, keterangan, file_path 
                    FROM surat WHERE kategori='masuk' ORDER BY id DESC
                """)
                self.all_data = cursor.fetchall()
                self.current_page = 1
                self.display_data(self.all_data)
                db.close()
        except Exception as e: print(f"Error Load: {e}")

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
            
            no_item = QTableWidgetItem(str(start_idx + i + 1))
            no_item.setData(Qt.ItemDataRole.UserRole, row[0])
            no_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, no_item)

            for j in range(1, 7):
                val = str(row[j]) if row[j] else ""
                if j in [1, 4]:
                    try:
                        d = QDate.fromString(val, "yyyy-MM-dd")
                        if d.isValid(): val = d.toString("dd/MM/yyyy")
                    except: pass
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, j, item)
            
            # --- AKSI ---
            btn_container = QWidget()
            btn_container.setStyleSheet("background: transparent;")
            btn_l = QHBoxLayout(btn_container)
            btn_l.setContentsMargins(10, 5, 10, 5)
            btn_l.setSpacing(15)
            
            btn_view = QPushButton("Lihat")
            btn_view.setStyleSheet("""
                QPushButton {
                    background: #5c7cfa; color: white; border-radius: 4px; 
                    padding: 6px 12px; font-weight: bold; min-width: 30px;
                }
                QPushButton:hover { background: #4263eb; }
            """)
            btn_view.clicked.connect(lambda checked, p=row[7]: self.buka_berkas(p))
            
            btn_edit = QPushButton("✏️")
            btn_edit.setStyleSheet("""
                QPushButton {
                    background: #f1c40f; color: white; border-radius: 4px; 
                    padding: 6px; min-width: 40px;
                }
                QPushButton:hover { background: #f39c12; }
            """)
            btn_edit.clicked.connect(lambda checked, r=row: self.aksi_edit(r))
            
            btn_l.addWidget(btn_view)
            btn_l.addWidget(btn_edit)
            self.table.setCellWidget(i, 7, btn_container)
            self.table.setRowHeight(i, 55)
        self.table.setSortingEnabled(True)

    def filter_data(self):
        text = self.search_input.text().lower()
        self.filtered_data = [d for d in self.all_data if 
                              text in str(d[3]).lower() or 
                              text in str(d[5]).lower() or 
                              text in str(d[6]).lower()]
        self.current_page = 1
        self.display_data(self.filtered_data)

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
        path, _ = QFileDialog.getSaveFileName(self, "Simpan Laporan", f"Laporan_Surat_Masuk_{datetime.now().strftime('%d%m%Y')}.xlsx", "Excel Files (*.xlsx)")
        if path:
            try:
                df = pd.DataFrame(data_exp, columns=["ID", "Tgl Terima", "Dari", "Nomor Surat", "Tgl Surat", "Perihal", "Ket", "Path"])
                df.to_excel(path, index=False)
                self.notifikasi_custom("Sukses", "Laporan berhasil disimpan!", QMessageBox.Icon.Information)
            except Exception as e: self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)

    def aksi_tambah(self):
        dialog = FormTambahSurat(self, kategori="Masuk")
        if dialog.exec():
            # Urutan di form: ent_tanggal(terima), ent_pihak(dari), ent_nomor, ent_tgl_surat, ent_perihal, ent_keterangan
            tgl_terima = dialog.ent_tanggal.date().toString("yyyy-MM-dd")
            dari = dialog.ent_pihak.text().strip()
            nomor = dialog.ent_nomor.text().strip()
            tgl_surat = dialog.ent_tgl_surat.date().toString("yyyy-MM-dd")
            
            # --- LOGIKA PEMBERSIHAN KODE ---
            raw_perihal = dialog.ent_perihal.currentText().strip()
            if " - " in raw_perihal:
                # Ambil bagian kiri (Judul), buang kanan (Kode)
                perihal = raw_perihal.rsplit(" - ", 1)[0]
            else:
                perihal = raw_perihal
            # -------------------------------
            
            ket = dialog.ent_keterangan.text().strip()
            path_asal = dialog.file_path

            if not nomor or not path_asal:
                self.notifikasi_custom("Peringatan", "Nomor dan Berkas wajib diisi!", QMessageBox.Icon.Warning)
                return

            try:
                # --- PERUBAHAN DI SINI ---
                # Mengambil path dinamis dari settings
                up_dir = get_folder_path("masuk") 
                
                # Pastikan folder tersebut ada (buat jika belum ada)
                os.makedirs(up_dir, exist_ok=True)
                
                # Proses Copy File
                ext = os.path.splitext(path_asal)[1]
                nama_file_baru = f"IN_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                path_dest = os.path.join(up_dir, nama_file_baru)
                
                shutil.copy(path_asal, path_dest)
                
                # Simpan PATH LENGKAP ke database agar file tetap bisa dibuka
                # meskipun folder dipindah-pindah
                db = connect_db()
                cursor = db.cursor()
                cursor.execute("""
                    INSERT INTO surat (nomor_surat, judul_surat, asal_surat, kategori, tanggal, tanggal_surat, keterangan, file_path) 
                    VALUES (?, ?, ?, 'masuk', ?, ?, ?, ?)
                """, (nomor, perihal, dari, tgl_terima, tgl_surat, ket, path_dest)) # Gunakan path_dest (path lengkap)
                
                db.commit()
                db.close()
                self.load_data()
                self.notifikasi_custom("Berhasil", "Data berhasil diarsipkan!", QMessageBox.Icon.Information)
            except Exception as e: 
                self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)

    def aksi_edit(self, data):
        dialog = FormTambahSurat(self, kategori="Masuk")
        dialog.setWindowTitle("Edit Surat Masuk")
        
        # Simpan path lama untuk perbandingan nanti
        path_lama = data[7] 
        
        # Mengisi form dengan data lama
        dialog.ent_tanggal.setDate(QDate.fromString(data[1], "yyyy-MM-dd"))
        dialog.ent_pihak.setText(str(data[2]))
        dialog.ent_nomor.setText(str(data[3]))
        dialog.ent_tgl_surat.setDate(QDate.fromString(data[4], "yyyy-MM-dd"))
        dialog.ent_perihal.setCurrentText(str(data[5])) 
        dialog.ent_keterangan.setText(str(data[6]))
        dialog.file_path = path_lama

        if dialog.exec():
            try:
                # --- 1. Logika Pembersihan Judul ---
                raw_perihal = dialog.ent_perihal.currentText().strip()
                if " - " in raw_perihal:
                    perihal = raw_perihal.rsplit(" - ", 1)[0]
                else:
                    perihal = raw_perihal
                
                # --- 2. Logika Pemindahan File (Jika Berubah) ---
                path_baru_input = dialog.file_path
                final_path = path_lama # Defaultnya pakai path lama

                # Jika user memilih file baru (path berbeda dengan database)
                if path_baru_input != path_lama:
                    # Ambil folder tujuan saat ini
                    up_dir = get_folder_path("masuk")
                    os.makedirs(up_dir, exist_ok=True)
                    
                    # Buat nama file unik baru
                    ext = os.path.splitext(path_baru_input)[1]
                    # Tambahkan penanda 'EDIT' agar mudah dilacak
                    nama_file_baru = f"IN_EDIT_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                    path_dest = os.path.join(up_dir, nama_file_baru)
                    
                    # Salin file ke folder arsip
                    shutil.copy(path_baru_input, path_dest)
                    final_path = path_dest
                    
                    # (Opsional) Hapus file lama jika ingin hemat memori
                    # if path_lama and os.path.exists(path_lama):
                    #    try: os.remove(path_lama)
                    #    except: pass

                # --- 3. Update Database ---
                db = connect_db()
                cursor = db.cursor()
                
                cursor.execute("""
                    UPDATE surat SET tanggal=?, asal_surat=?, nomor_surat=?, tanggal_surat=?, judul_surat=?, keterangan=?, file_path=? 
                    WHERE id=?
                """, (
                    dialog.ent_tanggal.date().toString("yyyy-MM-dd"), 
                    dialog.ent_pihak.text(), 
                    dialog.ent_nomor.text(), 
                    dialog.ent_tgl_surat.date().toString("yyyy-MM-dd"), 
                    perihal, 
                    dialog.ent_keterangan.text(), 
                    final_path, # Gunakan path yang sudah dipastikan di folder arsip
                    data[0]
                ))

                db.commit()
                db.close()
                self.load_data()
                self.notifikasi_custom("Sukses", "Data dan file berhasil diperbarui!", QMessageBox.Icon.Information)
            except Exception as e: 
                self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)
                
    def aksi_hapus(self):
        row = self.table.currentRow()
        if row < 0: 
            self.notifikasi_custom("Peringatan", "Pilih data yang ingin dihapus!", QMessageBox.Icon.Warning)
            return
            
        # 1. Ambil ID dari UserRole kolom pertama
        db_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Konfirmasi Hapus")
        msg.setText("Apakah Anda yakin? Data dan file fisik akan dihapus permanen.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        # Style dasar dialog
        msg.setStyleSheet("""
            QMessageBox { 
                background-color: #ffffff; 
            }

            QMessageBox QLabel { 
                background: transparent;
                color: #000000; 
                font-size: 13px; 
                padding: 6px 4px;
            }

            QMessageBox QPushButton { 
                min-width: 90px; 
                min-height: 30px;
                border-radius: 6px;
                font-size: 12px;
                border: none;
                padding: 6px 14px;
                color: white;
            }
        """)

        # Ambil tombol secara eksplisit (aman di semua bahasa OS)
        btn_yes = msg.button(QMessageBox.StandardButton.Yes)
        btn_no  = msg.button(QMessageBox.StandardButton.No)

        # Styling langsung
        btn_yes.setStyleSheet("background-color: #27ae60;")
        btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_no.setStyleSheet("background-color: #e74c3c;")
        btn_no.setCursor(Qt.CursorShape.PointingHandCursor)

        if msg.exec() == QMessageBox.StandardButton.Yes:
            try:
                db = connect_db()
                cursor = db.cursor()

                # 2. Ambil path file sebelum data dihapus
                cursor.execute("SELECT file_path FROM surat WHERE id=?", (db_id,))
                result = cursor.fetchone()
                
                if result:
                    path_file = result[0]
                    # 3. Hapus file fisik jika ada
                    if path_file and os.path.exists(path_file):
                        try:
                            os.remove(path_file)
                        except Exception as e:
                            print(f"Gagal menghapus file fisik: {e}")

                # 4. Hapus data dari database
                cursor.execute("DELETE FROM surat WHERE id=?", (db_id,))
                db.commit()
                db.close()
                
                self.load_data()
                self.notifikasi_custom("Berhasil", "Data dan file berhasil dihapus!", QMessageBox.Icon.Information)
            except Exception as e:
                self.notifikasi_custom("Error", str(e), QMessageBox.Icon.Critical)

    def buka_berkas(self, path):
        if path and os.path.exists(path): os.startfile(os.path.abspath(path))
        else: self.notifikasi_custom("Error", "File tidak ditemukan!", QMessageBox.Icon.Critical)

    def notifikasi_custom(self, judul, pesan, ikon):
        # --- MEMBUAT DIALOG CUSTOM (Agar posisi benar-benar di tengah) ---
        dialog = QDialog(self)
        dialog.setWindowTitle("Pemberitahuan")
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        dialog.setFixedWidth(380) # Lebar fix agar proporsional
        dialog.setStyleSheet("background-color: white; border-radius: 8px;")
        
        # Layout utama vertikal
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(25, 25, 25, 25) # Margin sekeliling
        layout.setSpacing(10) # Jarak antar elemen
        
        # 1. Tentukan Icon & Warna
        emoji = "✅" 
        warna_judul = "#27ae60" # Hijau Sukses
        
        if ikon == QMessageBox.Icon.Warning:
            emoji = "⚠️"
            warna_judul = "#f39c12" # Kuning Peringatan
        elif ikon == QMessageBox.Icon.Critical:
            emoji = "❌"
            warna_judul = "#c0392b" # Merah Error
        elif ikon == QMessageBox.Icon.Question:
            emoji = "❓"
            warna_judul = "#3498db" # Biru Tanya

        # 2. Widget Icon (Emoji)
        lbl_icon = QLabel(emoji)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 55px; border: none; background: transparent;")
        layout.addWidget(lbl_icon)
        
        # 3. Widget Judul
        lbl_judul = QLabel(judul.upper())
        lbl_judul.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_judul.setStyleSheet(f"""
            font-size: 20px; 
            font-weight: 900; 
            color: {warna_judul}; 
            border: none; 
            background: transparent;
            margin-top: 5px;
        """)
        layout.addWidget(lbl_judul)
        
        # 4. Widget Pesan
        lbl_pesan = QLabel(pesan)
        lbl_pesan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_pesan.setWordWrap(True) # Agar text panjang turun ke bawah otomatis
        lbl_pesan.setStyleSheet("""
            font-size: 13px; 
            color: #57606f; 
            line-height: 1.4; 
            border: none; 
            background: transparent;
        """)
        layout.addWidget(lbl_pesan)
        
        # Spasi sebelum tombol
        layout.addSpacing(15)

        # 5. Tombol OK (Full Width)
        btn_ok = QPushButton("OK")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.clicked.connect(dialog.accept)
        btn_ok.setFixedHeight(45) # Tinggi tombol fix
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #2c3e50; }
            QPushButton:pressed { background-color: #27ae60; }
        """)
        layout.addWidget(btn_ok)

        dialog.exec()