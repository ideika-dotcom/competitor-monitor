"""
Мониторинг конкурентов - Desktop приложение на PyQt6
Ниша: Инъекционная гидроизоляция
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QGroupBox, QScrollArea,
    QFileDialog, QTabWidget, QMessageBox, QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent


class WorkerThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class DropZone(QGroupBox):
    fileDropped = pyqtSignal(str)
    
    def __init__(self, title="Загрузка изображения"):
        super().__init__(title)
        self.setAcceptDrops(True)
        self.selected_file = None
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.icon_label = QLabel("🖼️")
        self.icon_label.setStyleSheet("font-size: 40px;")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.text_label = QLabel("Перетащите скриншот сайта или нажмите для выбора")
        self.text_label.setStyleSheet("color: #94a3b8; font-size: 13px;")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.hint_label = QLabel("PNG, JPG, WEBP до 10MB")
        self.hint_label.setStyleSheet("color: #64748b; font-size: 11px;")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.hide()
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addWidget(self.hint_label)
        layout.addWidget(self.preview_label)
        self.setMinimumHeight(160)
    
    def mousePressEvent(self, event):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите изображение", "", "Изображения (*.png *.jpg *.jpeg *.webp)"
        )
        if file_path:
            self.set_file(file_path)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                self.set_file(file_path)
    
    def set_file(self, file_path: str):
        self.selected_file = file_path
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(280, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview_label.setPixmap(pixmap)
            self.preview_label.show()
            self.icon_label.hide()
            self.text_label.setText(Path(file_path).name)
            self.hint_label.setText("Нажмите для замены")
        self.fileDropped.emit(file_path)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Конкурентная разведка | Инъекционная гидроизоляция")
        self.setMinimumSize(1100, 750)
        self.resize(1250, 850)
        
        self.settings_path = Path(__file__).parent / "settings.json"
        self.api_url = self.load_settings()
        
        self.init_ui()
        self.check_server()
    
    def load_settings(self) -> str:
        try:
            if self.settings_path.exists():
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("api_url", "http://127.0.0.1:8000")
        except Exception:
            pass
        return "http://127.0.0.1:8000"
    
    def save_settings(self, url: str):
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump({"api_url": url}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        top_bar_layout = QHBoxLayout()
        api_label = QLabel("Адрес API:")
        api_label.setStyleSheet("font-weight: bold; color: #38bdf8;")
        
        self.api_input = QLineEdit(self.api_url)
        self.api_input.setPlaceholderText("http://127.0.0.1:8000")
        self.api_input.textChanged.connect(self.on_api_url_changed)
        
        self.status_btn = QPushButton("🔌 Проверить подключение")
        self.status_btn.clicked.connect(self.check_server)
        self.status_btn.setStyleSheet("background-color: #334155; color: #f8fafc; border-radius: 6px; padding: 6px 12px;")
        
        top_bar_layout.addWidget(api_label)
        top_bar_layout.addWidget(self.api_input, stretch=1)
        top_bar_layout.addWidget(self.status_btn)
        main_layout.addLayout(top_bar_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #334155; border-radius: 8px; background: #0f172a; }
            QTabBar::tab { background: #1e293b; color: #94a3b8; padding: 10px 20px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }
            QTabBar::tab:selected { background: #0284c7; color: #ffffff; font-weight: bold; }
        """)
        
        self.tabs.addTab(self.create_text_tab(), "📝 Анализ текста")
        self.tabs.addTab(self.create_image_tab(), "🖼️ Анализ изображения")
        self.tabs.addTab(self.create_parse_tab(), "🌐 Парсинг сайта")
        self.tabs.addTab(self.create_history_tab(), "📋 История")
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tabs, stretch=1)
        
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.hide()
        
        self.results_content_widget = QWidget()
        self.results_content_widget.setStyleSheet("background-color: #0a0f1c;")
        self.results_layout = QVBoxLayout(self.results_content_widget)
        self.results_scroll.setWidget(self.results_content_widget)
        
        main_layout.addWidget(self.results_scroll, stretch=1)
        self.current_worker = None
    
    def on_api_url_changed(self, text: str):
        self.api_url = text.strip()
        self.save_settings(self.api_url)
    
    def check_server(self):
        url = f"{self.api_url}/health"
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                self.status_btn.setText("🟢 Сервер доступен")
                self.status_btn.setStyleSheet("background-color: #065f46; color: #6ee7b7; border-radius: 6px; padding: 6px 12px;")
                return True
        except Exception:
            pass
        
        self.status_btn.setText("🔴 Нет связи с сервером")
        self.status_btn.setStyleSheet("background-color: #991b1b; color: #fca5a5; border-radius: 6px; padding: 6px 12px;")
        return False
    
    def show_backend_error(self):
        QMessageBox.warning(
            self,
            "Ошибка соединения",
            "Ошибка: Backend не запущен.\nЗапустите python run.py в корне проекта."
        )


    def create_text_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        group = QGroupBox("Входные данные конкурента (инъекционная гидроизоляция)")
        g_layout = QVBoxLayout(group)
        
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Вставьте текст с сайта конкурента по гидроизоляции подвалов, фундаментов...")
        self.text_input.setMinimumHeight(150)
        
        self.analyze_text_btn = QPushButton("⚡ Проанализировать текст")
        self.analyze_text_btn.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 10px; border-radius: 6px;")
        self.analyze_text_btn.clicked.connect(self.run_text_analysis)
        
        g_layout.addWidget(self.text_input)
        g_layout.addWidget(self.analyze_text_btn)
        layout.addWidget(group)
        layout.addStretch()
        return widget
    
    def create_image_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        group = QGroupBox("Анализ рекламного баннера или скриншота сайта")
        g_layout = QVBoxLayout(group)
        
        self.drop_zone = DropZone("Загрузите скриншот/баннер")
        self.analyze_image_btn = QPushButton("⚡ Проанализировать изображение")
        self.analyze_image_btn.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 10px; border-radius: 6px;")
        self.analyze_image_btn.clicked.connect(self.run_image_analysis)
        
        g_layout.addWidget(self.drop_zone)
        g_layout.addWidget(self.analyze_image_btn)
        layout.addWidget(group)
        layout.addStretch()
        return widget
    
    def create_parse_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        group = QGroupBox("Автоматический парсинг сайта конкурента")
        g_layout = QVBoxLayout(group)
        
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example-hydro.ru")
        
        self.parse_btn = QPushButton("⚡ Парсить и анализировать")
        self.parse_btn.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 10px; border-radius: 6px;")
        self.parse_btn.clicked.connect(self.run_parse_site)
        
        url_layout.addWidget(QLabel("URL:"))
        url_layout.addWidget(self.url_input, stretch=1)
        url_layout.addWidget(self.parse_btn)
        g_layout.addLayout(url_layout)
        
        layout.addWidget(group)
        layout.addStretch()
        return widget
    
    def create_history_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        h_layout = QHBoxLayout()
        title = QLabel("История запросов")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.clicked.connect(self.load_history)
        clear_btn = QPushButton("🗑️ Очистить")
        clear_btn.clicked.connect(self.clear_history)
        
        h_layout.addWidget(title)
        h_layout.addStretch()
        h_layout.addWidget(refresh_btn)
        h_layout.addWidget(clear_btn)
        layout.addLayout(h_layout)
        
        self.history_scroll_area = QScrollArea()
        self.history_scroll_area.setWidgetResizable(True)
        self.history_content = QWidget()
        self.history_layout = QVBoxLayout(self.history_content)
        self.history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.history_scroll_area.setWidget(self.history_content)
        
        layout.addWidget(self.history_scroll_area)
        return widget
    
    def on_tab_changed(self, index: int):
        if index == 3:
            self.load_history()


    def request_api(self, endpoint: str, method: str = "GET", **kwargs):
        url = f"{self.api_url}{endpoint}"
        try:
            if method == "GET":
                resp = requests.get(url, timeout=60, **kwargs)
            elif method == "POST":
                resp = requests.post(url, timeout=120, **kwargs)
            elif method == "DELETE":
                resp = requests.delete(url, timeout=30, **kwargs)
            else:
                return {"success": False, "error": "Неверный метод"}
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            return {"success": False, "connection_error": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_text_analysis(self):
        text = self.text_input.toPlainText().strip()
        if len(text) < 10:
            QMessageBox.warning(self, "Ошибка", "Введите текст минимум 10 символов.")
            return
        self.progress_bar.show()
        self.current_worker = WorkerThread(self.request_api, "/analyze_text", method="POST", json={"text": text})
        self.current_worker.finished.connect(self.on_analysis_finished)
        self.current_worker.error.connect(self.on_worker_error)
        self.current_worker.start()
    
    def run_image_analysis(self):
        if not self.drop_zone.selected_file:
            QMessageBox.warning(self, "Ошибка", "Выберите изображение.")
            return
        self.progress_bar.show()
        try:
            with open(self.drop_zone.selected_file, "rb") as f:
                file_bytes = f.read()
            
            files = {"file": (Path(self.drop_zone.selected_file).name, file_bytes, "image/jpeg")}
            self.current_worker = WorkerThread(self.request_api, "/analyze_image", method="POST", files=files)
            self.current_worker.finished.connect(self.on_analysis_finished)
            self.current_worker.error.connect(self.on_worker_error)
            self.current_worker.start()
        except Exception as e:
            self.progress_bar.hide()
            QMessageBox.critical(self, "Ошибка файла", str(e))
    
    def run_parse_site(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Введите URL сайта.")
            return
        self.progress_bar.show()
        self.current_worker = WorkerThread(self.request_api, "/parse_demo", method="POST", json={"url": url})
        self.current_worker.finished.connect(self.on_parse_finished)
        self.current_worker.error.connect(self.on_worker_error)
        self.current_worker.start()
    
    def on_analysis_finished(self, result: dict):
        self.progress_bar.hide()
        if result.get("connection_error"):
            self.show_backend_error()
            return
        if not result.get("success"):
            QMessageBox.critical(self, "Ошибка анализа", result.get("error", "Неизвестная ошибка"))
            return
        self.display_results(result.get("analysis", {}))
    
    def on_parse_finished(self, result: dict):
        self.progress_bar.hide()
        if result.get("connection_error"):
            self.show_backend_error()
            return
        if not result.get("success"):
            QMessageBox.critical(self, "Ошибка парсинга", result.get("error", "Неизвестная ошибка"))
            return
        data = result.get("data", {})
        self.display_results(data.get("analysis", {}))
    
    def on_worker_error(self, err: str):
        self.progress_bar.hide()
        QMessageBox.critical(self, "Ошибка потока", err)


    def display_results(self, analysis: dict):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        group = QGroupBox("Результаты анализа конкурента (Инъекционная гидроизоляция)")
        group.setStyleSheet("""
            QGroupBox {
                background-color: #111827;
                border: 1px solid #1e293b;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 24px;
                font-size: 15px;
                font-weight: bold;
                color: #f1f5f9;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 6px 12px;
                color: #38bdf8;
                background-color: #1a2234;
                border: 1px solid #334155;
                border-radius: 6px;
            }
        """)
        g_layout = QVBoxLayout(group)
        
        scores_layout = QHBoxLayout()
        scores = [
            ("Дизайн", analysis.get("design_score", 0)),
            ("Анимация", analysis.get("animation_potential", 0)),
            ("Конверсия", analysis.get("conversion_potential", 0)),
            ("Доверие", analysis.get("trust_score", 0)),
        ]
        for label, val in scores:
            score_card = QFrame()
            score_card.setStyleSheet("""
                QFrame {
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            sc_layout = QVBoxLayout(score_card)
            sc_layout.setContentsMargins(4, 6, 4, 6)
            sc_layout.setSpacing(4)
            
            title_lbl = QLabel(label)
            title_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #94a3b8;")
            title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            val_lbl = QLabel(f"{val}/10")
            val_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #38bdf8;")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            sc_layout.addWidget(title_lbl)
            sc_layout.addWidget(val_lbl)
            scores_layout.addWidget(score_card)
        g_layout.addLayout(scores_layout)
        
        sections = [
            ("Сильные стороны", analysis.get("strengths", [])),
            ("Слабые стороны", analysis.get("weaknesses", [])),
            ("Маркетинговые инсайты", analysis.get("marketing_insights", [])),
            ("Рекламные гипотезы", analysis.get("ad_hypotheses", [])),
            ("Рекомендации", analysis.get("recommendations", [])),
        ]
        for title, items in sections:
            if items:
                sec_label = QLabel(f"• {title}:")
                sec_label.setStyleSheet("font-weight: bold; color: #38bdf8; margin-top: 12px; font-size: 14px;")
                g_layout.addWidget(sec_label)
                for item in items:
                    it_label = QLabel(f"  - {item}")
                    it_label.setWordWrap(True)
                    it_label.setStyleSheet("color: #e2e8f0; font-size: 14px; margin-left: 8px;")
                    g_layout.addWidget(it_label)
        
        self.results_layout.addWidget(group)
        self.results_scroll.show()
    
    def load_history(self):
        result = self.request_api("/history", method="GET")
        if result.get("connection_error"):
            self.show_backend_error()
            return
        
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        items = result.get("items", [])
        if not items:
            self.history_layout.addWidget(QLabel("История пуста"))
            return
        
        for item in items:
            frame = QFrame()
            frame.setStyleSheet("background-color: #1e293b; border-radius: 6px; padding: 8px; margin-bottom: 4px;")
            f_layout = QVBoxLayout(frame)
            req_type = item.get("request_type", "")
            summary = item.get("request_summary", "")
            timestamp = item.get("timestamp", "")
            title_lbl = QLabel(f"[{req_type.upper()}] {summary[:80]}...")
            title_lbl.setStyleSheet("font-weight: bold; color: #38bdf8;")
            time_lbl = QLabel(f"Время: {timestamp}")
            time_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
            f_layout.addWidget(title_lbl)
            f_layout.addWidget(time_lbl)
            self.history_layout.addWidget(frame)
    
    def clear_history(self):
        reply = QMessageBox.question(self, "Подтверждение", "Очистить историю запросов?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            res = self.request_api("/history", method="DELETE")
            if res.get("connection_error"):
                self.show_backend_error()
            else:
                self.load_history()

