import sys
import os
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox, QProgressBar
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import yt_dlp

DOWNLOADS_DIR = os.path.join(os.path.expanduser("~"), "Downloads")

# PyInstaller 번들 실행 시 동봉된 바이너리 경로를 PATH에 추가
if getattr(sys, "frozen", False):
    _BIN_DIR = sys._MEIPASS
    os.environ["PATH"] = _BIN_DIR + os.pathsep + os.environ.get("PATH", "")
    FFMPEG_DIR = _BIN_DIR
else:
    FFMPEG_DIR = None  # 시스템 PATH의 ffmpeg 사용


class FetchThread(QThread):
    result = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            opts = {
                "quiet": True,
                "skip_download": True,
                "extractor_args": {"youtube": {
                    "player_client": ["android"],
                    "skip": ["dash", "hls"],
                }},
            }
            if FFMPEG_DIR:
                opts["ffmpeg_location"] = FFMPEG_DIR
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=False)

            # 썸네일을 스레드 안에서 다운로드 (메인 스레드 블로킹 방지)
            thumbnail_bytes = b""
            thumb_url = info.get("thumbnail", "")
            if thumb_url:
                try:
                    resp = requests.get(thumb_url, timeout=10)
                    resp.raise_for_status()
                    thumbnail_bytes = resp.content
                except Exception:
                    pass

            self.result.emit({
                "title": info.get("title", ""),
                "view_count": info.get("view_count", 0),
                "thumbnail_bytes": thumbnail_bytes,
            })
        except Exception as e:
            self.error.emit(str(e))


class DownloadThread(QThread):
    progress = pyqtSignal(int)   # 0–100
    finished = pyqtSignal(str)   # 저장 경로
    error = pyqtSignal(str)

    def __init__(self, url, save_dir):
        super().__init__()
        self.url = url
        self.save_dir = save_dir

    def _hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                self.progress.emit(int(downloaded / total * 100))
        elif d["status"] == "finished":
            self.progress.emit(100)

    def run(self):
        try:
            opts = {
                "format": "bestvideo+bestaudio/best",
                "merge_output_format": "mp4",
                "outtmpl": os.path.join(self.save_dir, "%(title)s.%(ext)s"),
                "progress_hooks": [self._hook],
                "quiet": True,
                "js_runtimes": {"node": {}},
                "remote_components": ["ejs:github"],
            }
            if FFMPEG_DIR:
                opts["ffmpeg_location"] = FFMPEG_DIR
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                filename = ydl.prepare_filename(info)
            self.finished.emit(filename)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Info Viewer")
        self.setMinimumWidth(600)
        self.fetch_thread = None
        self.download_thread = None
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        # 입력부
        row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("유튜브 URL을 입력하세요...")
        self.url_input.returnPressed.connect(self._on_fetch)
        self.fetch_btn = QPushButton("조회")
        self.fetch_btn.setFixedWidth(70)
        self.fetch_btn.clicked.connect(self._on_fetch)
        row.addWidget(self.url_input)
        row.addWidget(self.fetch_btn)
        root.addLayout(row)

        # 썸네일
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedHeight(315)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet("background-color: #1a1a1a;")
        root.addWidget(self.thumbnail_label)

        # 정보부
        self.title_label = QLabel("제목: -")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.view_label = QLabel("조회수: -")
        self.view_label.setStyleSheet("font-size: 13px;")

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 12px; color: gray;")

        root.addWidget(self.title_label)
        root.addWidget(self.view_label)
        root.addWidget(self.status_label)

        # 다운로드 버튼
        self.download_btn = QPushButton("다운로드")
        self.download_btn.setFixedHeight(36)
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._on_download)
        root.addWidget(self.download_btn)

        # 진행 표시줄
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        root.addWidget(self.progress_bar)

    def _on_fetch(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "입력 오류", "URL을 입력해주세요.")
            return
        if "youtube.com" not in url and "youtu.be" not in url:
            QMessageBox.warning(self, "입력 오류", "유효한 유튜브 URL을 입력해주세요.")
            return

        self.fetch_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.status_label.setText("조회 중...")
        self.title_label.setText("제목: -")
        self.view_label.setText("조회수: -")
        self.thumbnail_label.clear()
        self.progress_bar.setVisible(False)

        self.fetch_thread = FetchThread(url)
        self.fetch_thread.result.connect(self._on_result)
        self.fetch_thread.error.connect(self._on_error)
        self.fetch_thread.start()

    def _on_result(self, data):
        self.title_label.setText(f"제목: {data['title']}")
        self.view_label.setText(f"조회수: {data['view_count']:,}")
        self.status_label.setText("완료")
        self.fetch_btn.setEnabled(True)
        self.download_btn.setEnabled(True)

        if data["thumbnail_bytes"]:
            pixmap = QPixmap()
            pixmap.loadFromData(data["thumbnail_bytes"])
            scaled = pixmap.scaledToHeight(315, Qt.SmoothTransformation)
            self.thumbnail_label.setPixmap(scaled)
        else:
            self.thumbnail_label.setText("썸네일을 불러올 수 없습니다.")

    def _on_error(self, msg):
        self.status_label.setText("오류 발생")
        self.fetch_btn.setEnabled(True)
        QMessageBox.critical(self, "오류", f"정보를 가져오지 못했습니다.\n\n{msg}")

    def _on_download(self):
        url = self.url_input.text().strip()
        self.download_btn.setEnabled(False)
        self.fetch_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setText("다운로드 중...")

        self.download_thread = DownloadThread(url, DOWNLOADS_DIR)
        self.download_thread.progress.connect(self.progress_bar.setValue)
        self.download_thread.finished.connect(self._on_download_finished)
        self.download_thread.error.connect(self._on_download_error)
        self.download_thread.start()

    def _on_download_finished(self, path):
        self.status_label.setText(f"저장 완료: {path}")
        self.download_btn.setEnabled(True)
        self.fetch_btn.setEnabled(True)
        QMessageBox.information(self, "다운로드 완료", f"저장 위치:\n{path}")

    def _on_download_error(self, msg):
        self.status_label.setText("다운로드 오류")
        self.download_btn.setEnabled(True)
        self.fetch_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "다운로드 오류", f"다운로드에 실패했습니다.\n\n{msg}")

    def closeEvent(self, event):
        for thread in (self.fetch_thread, self.download_thread):
            if thread and thread.isRunning():
                thread.quit()
                thread.wait(3000)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
