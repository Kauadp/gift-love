import cv2
from PySide6.QtWidgets import QLabel, QFrame
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QTimer, Qt, Signal


class VideoWidget(QFrame):
    finished = Signal()  # Sinal emitido quando vídeo termina (sem loop)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame { 
                background: #0a0a0f; 
                border: 5px solid #8B4789;
                border-radius: 2px;
            }
        """)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setGeometry(0, 0, self.width(), self.height())

        self.cap = None
        self.loop = True
        self.video_finished_emitted = False

        self.timer = QTimer()
        self.timer.timeout.connect(self._next_frame)

    def resizeEvent(self, event):
        self.label.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def play_file(self, path, loop=True):
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(path)
        self.loop = loop
        self.video_finished_emitted = False
        self.timer.start(33)
        print(f"[VIDEO] Iniciando {path} - loop={loop}")

    def stop(self):
        """Para o vídeo"""
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.label.clear()

    def _next_frame(self):
        if not self.cap:
            return
        ok, frame = self.cap.read()
        if not ok:
            if self.loop:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                return
            else:
                # Vídeo terminou (sem loop)
                print("[VIDEO] Terminou (sem loop)")
                self.timer.stop()
                if not self.video_finished_emitted:
                    self.video_finished_emitted = True
                    self.finished.emit()
                return
        self._show_frame(frame)

    def _show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch*w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self.width(), self.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.label.setPixmap(pix)