import os
import shutil
import sqlite3
import zipfile
import glob
from datetime import datetime
from PyQt6.QtWidgets import (QFileDialog, QMessageBox, QDialog, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton) # [FIX] QHBoxLayout ditambahkan
from PyQt6.QtCore import Qt

class BackupManager:
    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.db_filename = "arsip_digital.db" 
        self.upload_folder_name = "uploads"

        # Auto-detect nama DB jika berbeda
        if not os.path.exists(self.db_filename):
            found_dbs = glob.glob("*.db")
            if found_dbs:
                self.db_filename = found_dbs[0]

    def create_backup(self):
        """Backup Pintar: Mendukung File Tunggal dan Folder Dokumen"""
        if not os.path.exists(self.db_filename):
            self.notifikasi_custom("Gagal", f"Database '{self.db_filename}' tidak ditemukan!", QMessageBox.Icon.Critical)
            return

        nama_default = f"BACKUP_ARSIP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        path_zip, _ = QFileDialog.getSaveFileName(self.parent, "Simpan Backup", nama_default, "ZIP Files (*.zip)")
        
        if not path_zip:
            return

        conn = None
        try:
            conn = sqlite3.connect(self.db_filename)
            cursor = conn.cursor()
            cursor.execute("SELECT id, file_path FROM surat WHERE file_path IS NOT NULL AND file_path != ''")
            rows = cursor.fetchall()
            
            with zipfile.ZipFile(path_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 1. Backup Database
                zipf.write(self.db_filename, arcname=self.db_filename)
                
                # 2. Backup File/Folder Fisik
                item_count = 0
                for row in rows:
                    id_surat = row[0]
                    original_path = row[1]
                    
                    if os.path.exists(original_path):
                        # Jika itu FILE (Surat Masuk/Keluar)
                        if os.path.isfile(original_path):
                            filename = os.path.basename(original_path)
                            # Format: files/ID_NamaFile.pdf
                            zip_entry = f"files/{id_surat}_{filename}"
                            zipf.write(original_path, arcname=zip_entry)
                        
                        # Jika itu FOLDER (Dokumen)
                        elif os.path.isdir(original_path):
                            foldername = os.path.basename(original_path)
                            # Format Folder: files/ID_DIR_NamaFolder/
                            root_zip_folder = f"files/{id_surat}_DIR_{foldername}"
                            
                            # Loop isi folder secara rekursif
                            for root, _, files in os.walk(original_path):
                                for file in files:
                                    abs_file = os.path.join(root, file)
                                    # Hitung path relatif agar struktur dalam folder tetap terjaga
                                    rel_path = os.path.relpath(abs_file, original_path)
                                    zip_entry = os.path.join(root_zip_folder, rel_path)
                                    zipf.write(abs_file, arcname=zip_entry)
                        
                        item_count += 1

            self.notifikasi_custom("Sukses", f"Backup selesai!\nDatabase & {item_count} item tersimpan.\nLokasi: {path_zip}", QMessageBox.Icon.Information)

        except Exception as e:
            self.notifikasi_custom("Error Backup", str(e), QMessageBox.Icon.Critical)
        finally:
            if conn: conn.close()

    def restore_backup(self):
        """Restore Pintar: Menangani File & Folder, serta memperbaiki Path DB"""
        path_zip, _ = QFileDialog.getOpenFileName(self.parent, "Pilih File Backup", "", "ZIP Files (*.zip)")
        if not path_zip: return

        if not self.konfirmasi_custom("RESTORE DATA?", "PERINGATAN: Data saat ini akan DIHAPUS dan digantikan dengan backup.\nLanjutkan?"):
            return

        # Folder temp
        temp_dir = os.path.join(os.getcwd(), "temp_restore_data")
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        conn = None
        try:
            # 1. Ekstrak ZIP
            with zipfile.ZipFile(path_zip, 'r') as zipf:
                zipf.extractall(temp_dir)

            # 2. Restore Database
            found_db = None
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file == self.db_filename or file.endswith(".db"):
                        found_db = os.path.join(root, file)
                        break
                if found_db: break
            
            if not found_db:
                raise Exception("Database tidak ditemukan dalam backup!")

            target_db = os.path.abspath(self.db_filename)
            try:
                if os.path.exists(target_db): os.remove(target_db)
                shutil.move(found_db, target_db)
            except PermissionError:
                raise Exception("Database sedang digunakan! Tutup aplikasi lain.")

            # 3. Restore File & Folder ke 'uploads/'
            dest_base = os.path.abspath(self.upload_folder_name)
            if not os.path.exists(dest_base): os.makedirs(dest_base)

            # Koneksi ke DB baru untuk update path
            conn = sqlite3.connect(target_db)
            cursor = conn.cursor()
            updates = []
            
            # Cari folder 'files' hasil ekstrak
            temp_files_dir = None
            for root, dirs, files in os.walk(temp_dir):
                if "files" in dirs:
                    temp_files_dir = os.path.join(root, "files")
                    break
            
            if temp_files_dir and os.path.exists(temp_files_dir):
                for item in os.listdir(temp_files_dir):
                    src_path = os.path.join(temp_files_dir, item)
                    
                    # A. Jika FILE (Surat Masuk/Keluar)
                    if os.path.isfile(src_path):
                        # Item name format: 123_NamaFile.pdf
                        parts = item.split('_', 1)
                        if len(parts) > 1 and parts[0].isdigit():
                            file_id = int(parts[0])
                            # Pindahkan ke uploads/
                            dest_path = os.path.join(dest_base, item)
                            shutil.move(src_path, dest_path)
                            # Simpan path baru untuk update DB
                            updates.append((dest_path.replace('\\', '/'), file_id))

                    # B. Jika FOLDER (Dokumen)
                    elif os.path.isdir(src_path):
                        # Item name format: 123_DIR_NamaFolder
                        parts = item.split('_DIR_', 1)
                        if len(parts) > 1 and parts[0].isdigit():
                            file_id = int(parts[0])
                            real_foldername = parts[1]
                            
                            # Target: uploads/dokumen/NamaFolder
                            target_dir = os.path.join(dest_base, "dokumen", real_foldername)
                            
                            # Bersihkan target lama jika ada
                            if os.path.exists(target_dir): shutil.rmtree(target_dir)
                            
                            # Pindahkan
                            parent = os.path.dirname(target_dir)
                            os.makedirs(parent, exist_ok=True)
                            shutil.move(src_path, target_dir)
                            
                            updates.append((target_dir.replace('\\', '/'), file_id))

            # 4. Update Path di Database
            if updates:
                cursor.executemany("UPDATE surat SET file_path = ? WHERE id = ?", updates)
                conn.commit()

            self.notifikasi_custom("Sukses", "Data berhasil dipulihkan!\nSilakan RESTART APLIKASI.", QMessageBox.Icon.Information)

        except Exception as e:
            self.notifikasi_custom("Gagal Restore", str(e), QMessageBox.Icon.Critical)
        finally:
            if conn: conn.close()
            if os.path.exists(temp_dir): 
                try: shutil.rmtree(temp_dir)
                except: pass

    # --- UI ---
    def notifikasi_custom(self, judul, pesan, ikon):
        dialog = QDialog(self.parent)
        dialog.setWindowTitle(judul)
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        dialog.setFixedWidth(400)
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
        lbl_pesan.setStyleSheet("font-size: 13px; color: #2c3e50; line-height: 1.4; border: none; background: transparent;")
        layout.addWidget(lbl_pesan)
        
        layout.addSpacing(15)
        btn_ok = QPushButton("OK")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.clicked.connect(dialog.accept)
        btn_ok.setStyleSheet("QPushButton { background-color: #34495e; color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 14px; height: 45px; } QPushButton:hover { background-color: #2c3e50; }")
        layout.addWidget(btn_ok)
        dialog.exec()

    def konfirmasi_custom(self, judul, pesan):
        dialog = QDialog(self.parent)
        dialog.setWindowTitle(judul)
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        dialog.setFixedWidth(400)
        dialog.setStyleSheet("background-color: white; border-radius: 8px;")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_icon = QLabel("❓")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 60px; border: none; background: transparent;")
        layout.addWidget(lbl_icon)
        
        lbl_judul = QLabel(judul)
        lbl_judul.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_judul.setStyleSheet("font-size: 22px; font-weight: 900; color: #3498db; border: none; background: transparent;")
        layout.addWidget(lbl_judul)
        
        lbl_pesan = QLabel(pesan)
        lbl_pesan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_pesan.setWordWrap(True)
        lbl_pesan.setStyleSheet("font-size: 14px; color: #57606f; border: none;")
        layout.addWidget(lbl_pesan)
        layout.addSpacing(15)

        btn_layout = QHBoxLayout()
        btn_batal = QPushButton("Batal")
        btn_batal.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_batal.setFixedHeight(40)
        btn_batal.setStyleSheet("QPushButton { background-color: #ecf0f1; color: #2c3e50; border: 1px solid #bdc3c7; border-radius: 6px; font-weight: bold; } QPushButton:hover { background-color: #dfe6e9; }")
        btn_batal.clicked.connect(dialog.reject)
        
        btn_yes = QPushButton("Ya, Lanjutkan")
        btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_yes.setFixedHeight(40)
        btn_yes.setStyleSheet("QPushButton { background-color: #3498db; color: white; border: none; border-radius: 6px; font-weight: bold; } QPushButton:hover { background-color: #2980b9; }")
        btn_yes.clicked.connect(dialog.accept)
        
        btn_layout.addWidget(btn_batal)
        btn_layout.addWidget(btn_yes)
        layout.addLayout(btn_layout)
        
        return dialog.exec()