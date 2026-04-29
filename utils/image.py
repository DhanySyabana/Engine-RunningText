import os
import cv2
from dotenv import load_dotenv

load_dotenv()

# --- OPTIMIZATION: Lazy-loaded super-resolution model ---
# Model is only loaded when superRes() is actually called,
# not at module import time. Saves memory and startup CPU.
_sr = None
_sr_initialized = False

def _get_sr():
    global _sr, _sr_initialized
    if not _sr_initialized:
        _sr = cv2.dnn_superres.DnnSuperResImpl_create()
        path = os.getenv("SUPERRES_MODEL_PATH", "utils/ESPCN_x3.pb")
        _sr.readModel(path)
        _sr.setModel("espcn", 3)
        _sr_initialized = True
    return _sr

def preprocess(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)
    return equalized

def superRes(img):
    sr = _get_sr()
    result = sr.upsample(img)
    return result
