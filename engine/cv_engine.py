import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from ultralytics import YOLO
import joblib
import cv2
from collections import deque, Counter

# -------- modelos --------
yolo = YOLO("models/yolo26n.pt")
model_mlp = joblib.load("models/modelo_mlp.pkl")
scaler = joblib.load("models/scaler.pkl")

# -------- mediapipe --------
BaseOptions = python.BaseOptions
HandLandmarker = vision.HandLandmarker
HandLandmarkerOptions = vision.HandLandmarkerOptions
VisionRunningMode = vision.RunningMode

options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path="models/hand_landmarker.task"),
    running_mode=VisionRunningMode.IMAGE,
    num_hands=2
)

# -------- buffers suavização --------
gestos_val = [deque(maxlen=7), deque(maxlen=7)]
probs_val = [deque(maxlen=7), deque(maxlen=7)]

detector = HandLandmarker.create_from_options(options)

# -------- util --------
def coords_norm(landmarks):
    x0, y0, z0 = landmarks[0].x, landmarks[0].y, landmarks[0].z
    out = []
    for lm in landmarks:
        out.extend([lm.x - x0, lm.y - y0, lm.z - z0])
    return out


# -------- função principal --------
def process_frame(frame, frame_count):
    print(f"[DEBUG] Frame {frame_count} - Iniciando processamento")

    imageRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=imageRGB)
    resultados = detector.detect(mp_image)

    pred_hands = ["Nenhum", "Nenhum"]
    prob_hands = [0.0, 0.0]

    if resultados.hand_landmarks:
        print(f"[DEBUG] Mãos detectadas: {len(resultados.hand_landmarks)}")
        for idx, hand_landmarks in enumerate(resultados.hand_landmarks[:2]):
            coords = coords_norm(hand_landmarks)

            if len(coords) == 63:
                arr = np.array(coords).reshape(1, -1)
                arr = scaler.transform(arr)

                pred = model_mlp.predict(arr)[0]
                prob = np.max(model_mlp.predict_proba(arr)[0])

                gestos_val[idx].append(pred)
                probs_val[idx].append(prob)

                pred_hands[idx] = Counter(gestos_val[idx]).most_common(1)[0][0]
                prob_hands[idx] = float(np.mean(probs_val[idx]))

                print(f"[DEBUG] Mão {idx}: {pred_hands[idx]} (prob média: {prob_hands[idx]:.2f})")
    else:
        print("[DEBUG] Nenhuma mão detectada")

    objetos = []
    if frame_count % 10 == 0:
        resultados_yolo = yolo(frame, verbose=False)
        for box in resultados_yolo[0].boxes:
            cls = int(box.cls[0])
            label = yolo.names[cls]
            conf = float(box.conf[0])
            if conf > 0.6:
                objetos.append(label)
                print(f"[DEBUG] Objeto detectado: {label} (conf: {conf:.2f})")

    print("[DEBUG] Processamento concluído")
    return {
        "gesto0": pred_hands[0],
        "gesto1": pred_hands[1],
        "prob0": prob_hands[0],
        "prob1": prob_hands[1],
        "objetos": objetos
    }
