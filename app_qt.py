import sys
import cv2

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from engine.cv_engine import process_frame
from engine.game_logic import GameState
from ui_qt.main_window import MainWindow


fases = [
    {"nome": "prologo", "tipo": "video", "arquivo": "assets/prolog.mp4"},
    {"nome": "alianca", "tipo": "gesto_duplo", "gestos": ["A", "B"]},
    {"nome": "fase_1", "tipo": "video", "arquivo": "assets/prolog.mp4"},
    {"nome": "boo", "tipo": "objeto", "objeto": "cat"},
    {"nome": "fase_2", "tipo": "video", "arquivo": "assets/prolog.mp4"},
    {"nome": "estadio", "tipo": "gesto_unico", "gesto": "A"},
    {"nome": "fase_3", "tipo": "video", "arquivo": "assets/prolog.mp4"}
]

app = QApplication(sys.argv)
game = GameState(fases)
window = MainWindow(game)
window.showFullScreen()

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("❌ Câmera não abriu")
    sys.exit(1)

frame_count = 0

# Inicia menu (looping do prólogo ou imagem)
window.video.play_file(fases[0]["arquivo"], loop=True)

def tick():
    global frame_count

    ok, frame = cap.read()
    if not ok:
        return

    dados = process_frame(frame, frame_count)
    frame_count += 1

    evento = game.update(
        dados.get("gesto0"),
        dados.get("gesto1"),
        dados.get("objetos", [])
    )

    window.update_state(game, dados, frame, evento)

timer = QTimer()
timer.timeout.connect(tick)
timer.start(33)

def cleanup():
    cap.release()

app.aboutToQuit.connect(cleanup)
sys.exit(app.exec())