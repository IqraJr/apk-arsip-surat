import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QPushButton, QGraphicsOpacityEffect, 
                             QGraphicsDropShadowEffect, QMessageBox, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from .db_manager import connect_db
from .backup_manager import BackupManager
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.backup_mgr = BackupManager(self)
        self.cards = []
        self.setup_ui()
        QTimer.singleShot(200, self.refresh_data)

    def get_stats(self):
        stats = {'masuk': 0, 'keluar': 0, 'dokumen': 0}
        try:
            db = connect_db()
            if db:
                cursor = db.cursor()
                cursor.execute("SELECT kategori, COUNT(*) FROM surat GROUP BY kategori")
                for kat, jml in cursor.fetchall():
                    k = str(kat).lower()
                    if k in stats: stats[k] = jml
                db.close()
        except Exception as e: print(f"Error DB: {e}")
        return stats

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setSpacing(30)

        # 1. Header Section
        header_container = QWidget()
        header_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1e3c72, stop:1 #2a5298);
                border-radius: 20px;
                padding: 20px;
            }
        """)
        header_layout = QVBoxLayout(header_container)
        
        self.title = QLabel("📊 Dashboard Analitik")
        self.title.setStyleSheet("font-size: 32px; font-weight: bold; color: white; border: none; background: transparent;")
        
        self.subtitle = QLabel("Ringkasan Data Surat & Dokumen")
        self.subtitle.setStyleSheet("font-size: 14px; color: rgba(255, 255, 255, 0.8); border: none; background: transparent; margin-top: 5px;")
        
        header_layout.addWidget(self.title)
        header_layout.addWidget(self.subtitle)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(Qt.GlobalColor.black)
        shadow.setOffset(0, 4)
        header_container.setGraphicsEffect(shadow)
        
        self.main_layout.addWidget(header_container)

        # 2. Container Kartu
        self.card_widget = QWidget()
        self.card_widget.setMinimumHeight(180)
        self.card_layout = QHBoxLayout(self.card_widget)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(20)
        self.main_layout.addWidget(self.card_widget)

        # --- TOMBOL BACKUP & RESTORE ---
        tools_container = QWidget()
        tools_layout = QHBoxLayout(tools_container)
        tools_layout.setContentsMargins(0, 10, 0, 10)
        tools_layout.setSpacing(15)

        lbl_tools = QLabel("🛠️ Pemeliharaan Data:")
        lbl_tools.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        
        btn_backup = QPushButton("💾 Backup Data (ZIP)")
        btn_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_backup.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; padding: 10px 20px; border-radius: 8px; font-weight: bold; font-size: 13px; }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        btn_backup.clicked.connect(self.backup_mgr.create_backup)

        btn_restore = QPushButton("♻️ Restore Data (ZIP)")
        btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restore.setStyleSheet("""
            QPushButton { background-color: #c0392b; color: white; padding: 10px 20px; border-radius: 8px; font-weight: bold; font-size: 13px; }
            QPushButton:hover { background-color: #e74c3c; }
        """)
        btn_restore.clicked.connect(self.backup_mgr.restore_backup)

        tools_layout.addWidget(lbl_tools)
        tools_layout.addWidget(btn_backup)
        tools_layout.addWidget(btn_restore)
        tools_layout.addStretch()
        
        self.main_layout.addWidget(tools_container)

        # 3. Chart Section (Expanded)
        chart_container = QWidget()
        chart_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        chart_container_layout = QVBoxLayout(chart_container)
        chart_container_layout.setContentsMargins(0, 0, 0, 0)
        
        chart_header = QLabel("📈 Distribusi Data")
        chart_header.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; padding: 10px 0; border: none; background: transparent;")
        chart_container_layout.addWidget(chart_header)
        
        self.chart_frame = QFrame()
        self.chart_frame.setStyleSheet("""
            QFrame {
                background: white; 
                border-radius: 20px; 
                border: 2px solid #e0e0e0;
                padding: 10px;
            }
        """)
        
        chart_shadow = QGraphicsDropShadowEffect()
        chart_shadow.setBlurRadius(15)
        chart_shadow.setColor(Qt.GlobalColor.gray)
        chart_shadow.setOffset(0, 3)
        self.chart_frame.setGraphicsEffect(chart_shadow)
        
        self.chart_vbox = QVBoxLayout(self.chart_frame)
        self.chart_vbox.setContentsMargins(0, 0, 0, 0) 
        
        chart_container_layout.addWidget(self.chart_frame)
        self.main_layout.addWidget(chart_container, stretch=1)

    def load_cards(self):
        for card in self.cards: card.setParent(None)
        self.cards.clear()

        data = self.get_stats()
        configs = [
            ("📨 SURAT MASUK", data['masuk'], "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #667eea, stop:1 #764ba2)", "#5568d3"),
            ("📤 SURAT KELUAR", data['keluar'], "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f093fb, stop:1 #f5576c)", "#e54858"),
            ("📋 DOKUMEN", data['dokumen'], "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4facfe, stop:1 #00f2fe)", "#00d9e5")
        ]

        for title, val, gradient, hover_color in configs:
            card = QFrame()
            card.setMinimumHeight(150)
            card.setStyleSheet(f"""
                QFrame {{ background: {gradient}; border-radius: 18px; border: none; }}
                QFrame:hover {{ background: {hover_color}; }}
                QLabel {{ color: white; background: transparent; border: none; }}
            """)
            
            v = QVBoxLayout(card)
            v.setContentsMargins(25, 20, 25, 20)
            v.setSpacing(10)
            
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("font-weight: 600; font-size: 14px; letter-spacing: 0.5px;")
            
            v_lbl = QLabel(str(val))
            v_lbl.setStyleSheet("font-size: 48px; font-weight: bold; margin-top: 10px;")
            
            info_lbl = QLabel("Total Data")
            info_lbl.setStyleSheet("font-size: 11px; opacity: 0.9;")
            
            v.addWidget(t_lbl)
            v.addWidget(v_lbl)
            v.addWidget(info_lbl)
            v.addStretch()
            
            self.cards.append(card)
            self.card_layout.addWidget(card)

    def update_chart(self):
        while self.chart_vbox.count():
            child = self.chart_vbox.takeAt(0)
            if child.widget(): child.widget().deleteLater()

        data = self.get_stats()
        sizes = [data['masuk'], data['keluar'], data['dokumen']]
        labels = ['Surat Masuk', 'Surat Keluar', 'Dokumen']
        
        if sum(sizes) == 0:
            lbl = QLabel("📭 Belum ada data tersedia")
            lbl.setStyleSheet("color: #95a5a6; font-size: 16px; font-weight: 500; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.chart_vbox.addWidget(lbl)
            return

        plt.style.use('seaborn-v0_8-pastel')
        
        fig, ax = plt.subplots(figsize=(10, 5)) 
        fig.patch.set_facecolor('white')
        
        colors = ['#667eea', '#f5576c', '#00f2fe']
        
        wedges, texts, autotexts = ax.pie(
            sizes, 
            autopct='%1.1f%%',
            colors=colors,
            startangle=90,
            pctdistance=0.85, 
            textprops={'fontsize': 12, 'weight': 'bold'},
            wedgeprops=dict(width=0.5, edgecolor='w') 
        )
        
        # [PERBAIKAN WARNA FONT PERSENTASE]
        # Mengubah warna teks persentase menjadi HITAM agar kontras dengan warna pie yang cerah
        for autotext in autotexts:
            autotext.set_color('#2c3e50') # Warna Biru Gelap / Hitam
            autotext.set_weight('bold')
            autotext.set_fontsize(13) # Sedikit diperbesar
        
        ax.axis('equal')
        
        ax.legend(wedges, labels,
                  title="Kategori",
                  loc="center left",
                  bbox_to_anchor=(1, 0, 0.5, 1))
        
        plt.tight_layout()
        
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        canvas.updateGeometry()
        
        self.chart_vbox.addWidget(canvas)

    def refresh_data(self):
        self.load_cards()
        self.update_chart()