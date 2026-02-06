
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

yolo = YOLO("yolo26n.pt")
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

        # ------------- // -------------

        # ---------- Desenha o FPS na tela --------------

        tempo_agora = time.time()
        fps = 1 / (tempo_agora - tempo_antes)
        tempo_antes = tempo_agora

        fps_text = f"FPS: {int(fps)}"

        cv2.putText(imagem, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0))

        # ----------- Grava Coords -------------

        # ----------- // -------------

        cv2.imshow("Test", imagem)

        # ---------- Keys Control ----------------
        tecla = cv2.waitKey(1) % 0XFF

        if tecla == 27: break

# ========= // =============

camera.release()
cv2.destroyAllWindows()
print("Tchau")