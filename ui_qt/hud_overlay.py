from PySide6.QtWidgets import QLabel, QFrame, QGraphicsOpacityEffect, QWidget
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PySide6.QtGui import QFont

class HUDOverlay(QFrame):
    """HUD centralizado com título e subtítulo"""
    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")
        self.resize(parent.width(), parent.height())

        self.fase_title = QLabel(self)
        self.fase_title.setAlignment(Qt.AlignCenter)
        self.fase_title.setStyleSheet("""
            color: #FFD700;
            font-family: 'Press Start 2P', monospace;
            font-size: 48px;
            font-weight: bold;
            text-shadow: 2px 2px 4px #000000;
        """)

        self.subtitle = QLabel(self)
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setStyleSheet("""
            color: #FFCC66;
            font-family: 'Press Start 2P', monospace;
            font-size: 28px;
            text-shadow: 1px 1px 3px #000000;
        """)

    def resizeEvent(self, event):
        w, h = self.parent().width(), self.parent().height()
        self.setGeometry(0, 0, w, h)
        self.fase_title.setGeometry(0, h//4, w, 80)
        self.subtitle.setGeometry(0, h//4 + 80, w, 50)
        super().resizeEvent(event)

    def set_title(self, title, subtitle=None):
        self.fase_title.setText(title)
        self.subtitle.setText(subtitle if subtitle else "")


class FloatingTextOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: white;")
        self.label.setFont(QFont("Arial", 48, QFont.Bold))

        self.effect = QGraphicsOpacityEffect()
        self.label.setGraphicsEffect(self.effect)
        self.effect.setOpacity(0.0)

        self.anim_timer = QTimer()
        self.anim_timer.setInterval(30)
        self.anim_timer.timeout.connect(self._update_opacity)
        self._target_opacity = 1.0
        self._fade_speed = 0.05
        self._state = "hidden"
        self.hide()

    def show_text(self, text: str, duration: int = 2000):
        self.label.setText(text)
        self.label.adjustSize()
        # centraliza
        pw, ph = self.parent().width(), self.parent().height()
        lw, lh = self.label.width(), self.label.height()
        self.label.move((pw - lw)//2, (ph - lh)//2)

        self._target_opacity = 1.0
        self.effect.setOpacity(0.0)
        self._state = "fading_in"
        self.show()
        self.anim_timer.start()

        QTimer.singleShot(duration, self._start_fade_out)

    def _start_fade_out(self):
        self._state = "fading_out"
        self._target_opacity = 0.0

    def _update_opacity(self):
        current = self.effect.opacity()
        if self._state == "fading_in":
            current += self._fade_speed
            if current >= self._target_opacity:
                current = self._target_opacity
                self._state = "visible"
        elif self._state == "fading_out":
            current -= self._fade_speed
            if current <= self._target_opacity:
                current = self._target_opacity
                self._state = "hidden"
                self.anim_timer.stop()
                self.hide()
        self.effect.setOpacity(current)
