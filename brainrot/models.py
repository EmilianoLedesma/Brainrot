"""Pinned, checksum-verified detector weights from the official OpenCV Zoo."""

import hashlib

import requests

from .domain.jobs import PermanentError

FACE_MODEL_PATH = "models/face_detection_yunet_2023mar.onnx"
FACE_MODEL_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
FACE_MODEL_URL = (
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/"
    "f12e12798e8314f7c074a6656816c048dcc95b7a/"
    "models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
)


def fetch_face_model() -> bytes:
    response = requests.get(FACE_MODEL_URL, timeout=60)
    response.raise_for_status()
    if hashlib.sha256(response.content).hexdigest() != FACE_MODEL_SHA256:
        raise PermanentError("face model checksum does not match the pinned OpenCV model")
    return response.content
