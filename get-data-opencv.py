# ===================== Importando Libs =======================

import cv2
import numpy as np
import ultralytics as YOLO
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time
import pandas as pd


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
    num_hands=1
)

# ============== Configura Res e ademais utilidades do OpenCV ===================

dataset = []
modo_gravacao = None
frames_restantes = 0
contador = {"A":0, "B":0, "C":0, "D":0, "E":0}

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

        coords_wrist = [] # Para normalizar em relação ao pulso
        if resultados.hand_landmarks:
            for hand_landmarks in resultados.hand_landmarks:
                coords_wrist.extend(coords_norm(hand_landmarks)) # Para normalizar em relação ao pulso
                for landmark in hand_landmarks:
                    x = int(landmark.x * imagem.shape[1])
                    y = int(landmark.y * imagem.shape[0])
                    cv2.circle(imagem, (x,y), 5, (0,0,255), -1)
                
                for start_idx, end_idx in HAND_CONNECTIONS:
                    start = hand_landmarks[start_idx]
                    end = hand_landmarks[end_idx]
                    x1, y1 = int(start.x * imagem.shape[1]), int(start.y * imagem.shape[0])
                    x2, y2 = int(end.x * imagem.shape[1]), int(end.y * imagem.shape[0])
                    cv2.line(imagem, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # ------------- // -------------

        # ---------- Desenha o FPS na tela --------------

        tempo_agora = time.time()
        fps = 1 / (tempo_agora - tempo_antes)
        tempo_antes = tempo_agora

        fps_text = f"FPS: {int(fps)}"

        cv2.putText(imagem, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0))

        # ----------- Grava Coords -------------

        if modo_gravacao is not None and len(coords_wrist) > 0:
            dataset.append(coords_wrist + [modo_gravacao])
            contador[modo_gravacao] += 1
            frames_restantes -= 1
            if frames_restantes <= 0:
                modo_gravacao = None

        
        for i, (gesto, total) in enumerate(contador.items()):
            cv2.putText(imagem, f"{gesto}: {total}", (10, 60 + 30 * i),
                        cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 255), 2)


        # ----------- // -------------

        cv2.imshow("Test", imagem)

        # ---------- Keys Control ----------------
        tecla = cv2.waitKey(1) % 0XFF

        if tecla == ord("a"): modo_gravacao, frames_restantes = "A", 100
        if tecla == ord("b"): modo_gravacao, frames_restantes = "B", 100
        if tecla == ord("c"): modo_gravacao, frames_restantes = "C", 100
        if tecla == ord("d"): modo_gravacao, frames_restantes = "D", 100
        if tecla == ord("e"): modo_gravacao, frames_restantes = "E", 100

        if tecla == 27: break

# =========== Salva os Dados ===========

df = pd.DataFrame(dataset)
df.to_csv("data/coords_to_train.csv", index=False)

# ========= // =============

camera.release()
cv2.destroyAllWindows()
print("Tchau")