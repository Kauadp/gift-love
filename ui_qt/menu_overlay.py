from PySide6.QtWidgets import QLabel, QWidget, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont


class MenuOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.resize(parent.size())

        # Fundo semi-transparente
        self.setStyleSheet("background-color: rgba(20, 15, 25, 180);")

        # ===== TÍTULO PRINCIPAL =====
        self.title = QLabel("FELIZ 1 ANO!", self)
        self.title.setFont(QFont("Press Start 2P", 28, QFont.Bold))
        self.title.setStyleSheet("""
            color: #D4AF37;
            background-color: transparent;
            font-family: 'Press Start 2P', monospace;
        """)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.adjustSize()

        # ===== TEXTO PISCANDO =====
        self.start_label = QLabel("PRESSIONE ESPACO", self)
        self.start_label.setFont(QFont("Press Start 2P", 12))
        self.start_label.setStyleSheet("""
            color: #B565D8;
            background-color: transparent;
            font-family: 'Press Start 2P', monospace;
        """)
        self.start_label.setAlignment(Qt.AlignCenter)
        self.start_label.adjustSize()

        # ===== FADE EFFECT =====
        self.effect = QGraphicsOpacityEffect(self.start_label)
        self.start_label.setGraphicsEffect(self.effect)

        self.anim = QPropertyAnimation(self.effect, b"opacity")
        self.anim.setDuration(1000)
        self.anim.setStartValue(0.3)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.InOutSine)
        self.anim.setLoopCount(-1)
        self.anim.start()

    def resizeEvent(self, event):
        w = self.width()
        h = self.height()
        
        self.title.adjustSize()
        title_x = (w - self.title.width()) // 2
        title_y = h // 3
        self.title.move(title_x, title_y)
        
        self.start_label.adjustSize()
        start_x = (w - self.start_label.width()) // 2
        start_y = title_y + self.title.height() + 60
        self.start_label.move(start_x, start_y)
        
        super().resizeEvent(event)