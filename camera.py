import platform
import cv2
import numpy as np
from PySide6.QtGui import QImage

PREVIEW_WIDTH = 560
PREVIEW_HEIGHT = 315

CONTROL_DEFAULTS = {
    "brightness": 0,
    "contrast": 0,
    "gamma": 100,
    "saturation": 0,
    "gain": 0,
}

CONTROL_RANGES = {
    "brightness": (-100, 100),
    "contrast": (-100, 100),
    "gamma": (20, 300),
    "saturation": (-100, 100),
    "gain": (-100, 100),
}


def clamp_control(name: str, value: int) -> int:
    minimum, maximum = CONTROL_RANGES[name]
    return max(minimum, min(maximum, value))


class Camera:
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.capture = self._open_camera(camera_index)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    def _open_camera(self, camera_index: int) -> cv2.VideoCapture:
        if platform.system() == "Windows":
            capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        else:
            capture = cv2.VideoCapture(camera_index)

        if capture.isOpened():
            return capture

        capture.release()
        for fallback_index in range(0, 5):
            if fallback_index == camera_index:
                continue
            if platform.system() == "Windows":
                fallback = cv2.VideoCapture(fallback_index, cv2.CAP_DSHOW)
            else:
                fallback = cv2.VideoCapture(fallback_index)
            if fallback.isOpened():
                print(f"Camera index {camera_index} failed; using fallback camera index {fallback_index}.")
                return fallback
            fallback.release()

        return capture

    def is_open(self) -> bool:
        return self.capture.isOpened()

    def read_frame(self):
        if not self.capture.isOpened():
            return None
        success, frame = self.capture.read()
        if not success or frame is None:
            return None
        return frame

    def release(self) -> None:
        if self.capture.isOpened():
            self.capture.release()


def adjust_image(frame: np.ndarray, control_values: dict) -> np.ndarray:
    image = frame.astype(np.float32)
    brightness = float(control_values["brightness"])
    contrast = 1.0 + float(control_values["contrast"]) / 100.0
    gain = 1.0 + float(control_values["gain"]) / 100.0

    image = image * contrast * gain + brightness
    image = np.clip(image, 0, 255).astype(np.uint8)

    if control_values["saturation"] != 0:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] *= 1.0 + float(control_values["saturation"]) / 100.0
        hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
        image = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    gamma_value = max(0.2, float(control_values["gamma"]) / 100.0)
    inv_gamma = 1.0 / gamma_value
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)], dtype=np.uint8)
    image = cv2.LUT(image, table)
    return image


def to_gray(frame: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Mild blur to reduce sensor noise but preserve edges for accurate binarization
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return gray


def to_binary(gray_image: np.ndarray) -> np.ndarray:
    if gray_image.size == 0:
        return gray_image
    # Otsu thresholding
    threshold, binary = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Apply mild morphological filtering to remove tiny speckles without over-smoothing
    try:
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open, iterations=1)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close, iterations=1)
    except Exception:
        pass
    return binary


def scale_roi_to_frame(roi: tuple[int, int, int, int], frame: np.ndarray) -> tuple[int, int, int, int]:
    x_min, y_min, x_max, y_max = roi
    frame_height, frame_width = frame.shape[:2]
    x_ratio = frame_width / PREVIEW_WIDTH
    y_ratio = frame_height / PREVIEW_HEIGHT
    return (
        int(round(max(0, x_min * x_ratio))),
        int(round(max(0, y_min * y_ratio))),
        int(round(min(frame_width, x_max * x_ratio))),
        int(round(min(frame_height, y_max * y_ratio))),
    )


def crop_roi(image: np.ndarray, roi: tuple[int, int, int, int]) -> np.ndarray:
    x_min, y_min, x_max, y_max = roi
    return image[y_min:y_max, x_min:x_max]


def image_to_qimage(image: np.ndarray):
    if image is None or image.size == 0:
        return None
    if image.ndim == 2:
        height, width = image.shape
        return QImage(image.data, width, height, width, QImage.Format.Format_Grayscale8)
    height, width, channels = image.shape
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return QImage(rgb.data, width, height, width * channels, QImage.Format.Format_RGB888)
