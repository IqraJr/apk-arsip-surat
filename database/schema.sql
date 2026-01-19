-- Membuat Database
CREATE DATABASE IF NOT EXISTS db_arsip;
USE db_arsip;

-- Membuat Tabel Surat
CREATE TABLE IF NOT EXISTS surat (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nomor_surat VARCHAR(100),          -- Nomor resmi dari surat
    judul_surat VARCHAR(255) NOT NULL, -- Perihal / Judul
    kategori ENUM('masuk', 'keluar', 'dokumen') NOT NULL,
    asal_surat VARCHAR(255),           -- Pengirim (jika masuk) atau Tujuan (jika keluar)
    penerima VARCHAR(255),             -- Penerima internal
    tanggal DATE NOT NULL,             -- Tanggal surat masuk/keluar
    file_path VARCHAR(255) NOT NULL,   -- Lokasi file di folder uploads
    keterangan TEXT,                   -- Catatan tambahan
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);