
# ===================== Importando Libs =======================

import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from ultralytics import YOLO
import cv2 
import time
import joblib
from collections import deque, Counter

yolo = YOLO("models/yolo26n.pt")
model_mlp = joblib.load("models/modelo_mlp.pkl")
scaler = joblib.load("models/scaler.pkl")

# ===================== Funções Auxiliares =======================

# ----- Função para normalizar coordenadas em referência ao pulso --------

def coords_norm(landmark_list):
    x0 = landmark_list[0].x
    y0 = landmark_list[0].y
    z0 = landmark_list[0].z

    temp_landmark_list = []
    for lm in landmark_list:
        temp_landmark_list.append(lm.x - x0)   
        temp_landmark_list.append(lm.y - y0)   
        temp_landmark_list.append(lm.z - z0)   

    return temp_landmark_list


# ----------- Classe para Estado do jogo -------------------

class GameState:
    def __init__(self, fases):
        self.fases = fases
        self.fase_atual = 0
        self.estado = "JOGANDO"
        self.cooldown = 0
        self.video_cap = None
        self.cooldown_time = 0

    def check_fase(self, g0, g1, objetos=None):

        if self.fase_atual >= len(self.fases):
            return False

        fase = self.fases[self.fase_atual]
        tipo = fase["tipo"]

        if tipo == "gesto_unico":
            return g0 == fase["gesto"] or g1 == fase["gesto"]

        if tipo == "gesto_duplo":
            a, b = fase["gestos"]
            return ((g0 == a and g1 == b) or
                    (g0 == b and g1 == a))
        
        if tipo == "objeto":
            if objetos is None:
                return False
            return fase["objeto"] in objetos

        return False


    def start_video(self, path):
        self.video_cap = cv2.VideoCapture(path)


    def play_video_step(self):

        if self.video_cap is None:
            return None

        ok, frame = self.video_cap.read()

        if not ok:
            self.video_cap.release()   # ← corrigido
            self.video_cap = None
            self.fase_atual += 1
            return "video_done"

        return frame


    def update(self, g0, g1, objetos=None):

        if time.time() < self.cooldown_time:
            return "aguardando"

        fase = self.fases[self.fase_atual]
        tipo = fase["tipo"]

        if tipo == "gesto_duplo":
            if g0 == "Nenhum" or g1 == "Nenhum":
                return None

        if tipo == "gesto_unico":
            if g0 == "Nenhum" and g1 == "Nenhum":
                return None
            
        if tipo == "video":
            return None

        if self.check_fase(g0, g1, objetos):
            self.fase_atual += 1
            self.cooldown_time = time.time() + 1.0
            return "fase_ok"

        return None



# ============ Configuração Game ================

fases = [
    {
        "nome": "prologo_carnaval",
        "tipo": "video",
        "arquivo": "assets/prolog.mp4"
    },

    {
        "nome": "alianca",
        "tipo": "gesto_duplo",
        "gestos": ["A", "B"]
    },

    {
        "nome": "video_fase1",
        "tipo": "video",
        "arquivo": "assets/fase1.mp4"
    },

    {
        "nome": "boo",
        "tipo": "objeto",
        "objeto": "cat"
    },

    {
        "nome": "video_fase2",
        "tipo": "video",
        "arquivo": "assets/fase2.mp4"
    },

    {
        "nome": "rio_branco",
        "tipo": "gesto_duplo",
        "gestos": ["C", "D"]
    },

    {
        "nome": "video_fase3",
        "tipo": "video",
        "arquivo": "assets/fase3.mp4"
    }
]

game = GameState(fases)

# ============ Configurando o MediaPipe ==================

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),      # polegar
    (0, 5), (5, 6), (6, 7), (7, 8),      # indicador
    (0, 9), (9, 10), (10, 11), (11, 12), # médio
    (0, 13), (13, 14), (14, 15), (15, 16), # anelar
    (0, 17), (17, 18), (18, 19), (19, 20), # mindinho
    (5, 9), (9, 13), (13, 17)            # palma base
]

BaseOptions = python.BaseOptions
HandLandmarker = vision.HandLandmarker
HandLandmarkerOptions = vision.HandLandmarkerOptions
VisionRunningMode = vision.RunningMode

options = HandLandmarkerOptions(
    base_options = BaseOptions(model_asset_path="models/hand_landmarker.task"),
    running_mode = VisionRunningMode.IMAGE,
    num_hands=2
)

# ============== Configura Res e ademais utilidades do OpenCV ===================

dataset = []
modo_gravacao = None
frames_restantes = 0
gestos_maos = ["Nenhum", "Nenhum"]
probs_maos = [0.0, 0.0]
gestos_val = [
    deque(maxlen=7),   # mão 0
    deque(maxlen=7)    # mão 1
]

probs_val = [
    deque(maxlen=7),
    deque(maxlen=7)
]
fase_msg_timer = 0

frame_count = 0

with HandLandmarker.create_from_options(options) as detector:
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# ================== Looping para rodar câmera ========================

    tempo_antes = 0
    while True:
        sucesso, imagem = camera.read()
        if not sucesso:
            print("Falha ao abrir câmera")
            break

        imageRGB = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data = imageRGB)
        
        resultados = detector.detect(mp_image)

        if game.fase_atual >= len(game.fases):
            cv2.putText(imagem, "JOGO FINALIZADO", (200,200),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
            cv2.imshow("Test", imagem)
            if cv2.waitKey(1) == 27:
                break
            continue

        fase = game.fases[game.fase_atual]

        if fase["tipo"] == "video":

            if game.video_cap is None:
                game.start_video(fase["arquivo"])

            frame = game.play_video_step()

            if isinstance(frame, np.ndarray):
                cv2.imshow("Test", frame)
                if cv2.waitKey(30) == 27:
                    break
                continue

        if fase_msg_timer > 0:
            cv2.putText(imagem, "Avancou de Fase!", (200,200),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,255,0), 3)
            fase_msg_timer -= 1

        if frame_count % 10 == 0:
            objetos_cache = []
            resultados_yolo = yolo(imagem.copy(), verbose=False)
            for box in resultados_yolo[0].boxes:
                cls = int(box.cls[0].cpu().numpy())
                label = yolo.names[cls]
                conf = float(box.conf[0].cpu().numpy())
                if label == "cat" and conf > 0.6:
                    objetos_cache.append({
                        "label": label,
                        "conf": conf
                    })
                    
        frame_count += 1

        # ---- Desenhar linhas e points do MediaPipe --------

        if resultados.hand_landmarks:
            pred_hands = ["Nenhum", "Nenhum"]
            prob_hands = [0.0, 0.0]

            for idx, hand_landmarks in enumerate(resultados.hand_landmarks):

                if idx >= 2:
                    break

                # desenhar pontos
                for landmark in hand_landmarks:
                    x = int(landmark.x * imagem.shape[1])
                    y = int(landmark.y * imagem.shape[0])
                    cv2.circle(imagem, (x,y), 5, (0,0,255), -1)

                # desenhar conexões
                for start_idx, end_idx in HAND_CONNECTIONS:
                    start = hand_landmarks[start_idx]
                    end = hand_landmarks[end_idx]
                    x1, y1 = int(start.x * imagem.shape[1]), int(start.y * imagem.shape[0])
                    x2, y2 = int(end.x * imagem.shape[1]), int(end.y * imagem.shape[0])
                    cv2.line(imagem, (x1, y1), (x2, y2), (0,255,0), 2)

                coords = coords_norm(hand_landmarks)

                if len(coords) == 63:
                    coords_array = np.array(coords).reshape(1, -1)
                    coords_scaled = scaler.transform(coords_array)

                    pred = model_mlp.predict(coords_scaled)[0]
                    prob = np.max(model_mlp.predict_proba(coords_scaled)[0])

                    gestos_val[idx].append(pred)
                    probs_val[idx].append(prob)

                    gesto_final = Counter(gestos_val[idx]).most_common(1)[0][0]
                    prob_final = np.mean(probs_val[idx])

                    pred_hands[idx] = gesto_final
                    prob_hands[idx] = prob_final

            for i in range(2):
                cv2.putText(imagem,
                    f"Hand{i}: {pred_hands[i]} ({prob_hands[i]:.2f})",
                    (10, 60 + i*40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0,0,255),
                    2)
                
            # ----------- Lógica Game -------------

            gesto0, gesto1 = pred_hands[0], pred_hands[1]
            evento = None
            objetos_detectados = [o["label"] for o in objetos_cache]
            evento = game.update(gesto0, gesto1, objetos_detectados)

            if evento == "fase_ok":
                fase_msg_timer = 30

        # ------------- // -------------

        # ---------- Desenha o FPS na tela --------------

        tempo_agora = time.time()
        delta = tempo_agora - tempo_antes
        fps = 1/delta if delta > 0 else 0

        tempo_antes = tempo_agora

        fps_text = f"FPS: {int(fps)}"

        cv2.putText(imagem, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0))

        # ----------- // -------------

        cv2.imshow("Test", imagem)

        # ---------- Keys Control ----------------
        tecla = cv2.waitKey(1) % 0XFF

        if tecla == 27: break

# ========= // =============

camera.release()
cv2.destroyAllWindows()
print("Tchau")