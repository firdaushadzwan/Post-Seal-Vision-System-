from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QImage, QPainter, QPen, QColor, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QTextEdit,
    QVBoxLayout,
    QGridLayout,
    QGroupBox,
    QWidget,
    QMenu,
    QSizePolicy,
)

from arduino_serial import ArduinoSerial
import camera as cam
import inspection as insp
import cv2
import os
import sys
# Ensure this file's directory is on sys.path so local modules like arduino_serial import reliably
sys.path.insert(0, os.path.dirname(__file__))

CONTROL_LABELS = ["brightness", "saturation", "gamma", "gain", "contrast"]
INSPECTION_LABELS = [
    "upper sealing",
    "offset sealing",
]

class ImageLabel(QLabel):
    actionRequested = Signal(str, str)
    roiDefined = Signal(tuple)

    def __init__(self, title: str, width: int = cam.PREVIEW_WIDTH, height: int = cam.PREVIEW_HEIGHT):
        super().__init__()
        self.setText(title)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(width, height)
        self.setStyleSheet("background-color: black; border: 1px solid #444; color: white;")
        self._pixmap = None
        self._draw_rect = None
        self._start_pos = None
        self._roi_rects: list[tuple[str, tuple[int, int, int, int]]] = []
        self._pending_roi_label: str | None = None

    def set_pixmap(self, pixmap):
        self._pixmap = pixmap
        super().setPixmap(pixmap)
        self.update()

    def set_roi_rects(self, rois: list[tuple[str, tuple[int, int, int, int]]]):
        self._roi_rects = rois
        self.update()

    def set_pending_roi_label(self, label: str | None):
        self._pending_roi_label = label
        if label is None:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)
        self.update()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction(self._create_action("Start inspection", "action", "start inspection"))
        menu.addSeparator()
        inspection_menu = menu.addMenu("Inspection")
        for label in INSPECTION_LABELS:
            inspection_menu.addAction(self._create_action(label, "inspection", label))
        control_menu = menu.addMenu("Camera control")
        for label in CONTROL_LABELS:
            control_menu.addAction(self._create_action(label, "control", label))
        menu.exec(event.globalPos())

    def _create_action(self, text: str, category: str, value: str):
        action = QAction(text, self)
        action.triggered.connect(lambda checked=False, category=category, value=value: self.actionRequested.emit(category, value))
        return action

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._pending_roi_label:
            self._start_pos = event.position()
            self._draw_rect = None
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._start_pos is None:
            return
        end_pos = event.position()
        self._draw_rect = (
            int(self._start_pos.x()),
            int(self._start_pos.y()),
            int(end_pos.x()),
            int(end_pos.y()),
        )
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self._start_pos is None:
            super().mouseReleaseEvent(event)
            return

        if self._draw_rect is not None:
            x0, y0, x1, y1 = self._draw_rect
            x_min, x_max = sorted((x0, x1))
            y_min, y_max = sorted((y0, y1))
            if abs(x_min - x_max) >= 8 and abs(y_min - y_max) >= 8:
                self.roiDefined.emit((x_min, y_min, x_max, y_max))
        self._start_pos = None
        self._draw_rect = None
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._pixmap is None:
            return

        painter = QPainter(self)
        pen = QPen(QColor(0, 255, 0), 2)
        painter.setPen(pen)
        for label, rect in self._roi_rects:
            x_min, y_min, x_max, y_max = rect
            painter.drawRect(x_min, y_min, x_max - x_min, y_max - y_min)
            painter.fillRect(x_min + 1, y_min + 1, min(140, x_max - x_min - 2), 18, QColor(0, 0, 0, 150))
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(x_min + 4, y_min + 14, label)

        if self._draw_rect:
            pen = QPen(QColor(255, 255, 0), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            x0, y0, x1, y1 = self._draw_rect
            painter.drawRect(x0, y0, x1 - x0, y1 - y0)

        if self._pending_roi_label:
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(10, 20, f"Draw ROI for: {self._pending_roi_label}")


class MainWindow(QMainWindow):
    def __init__(self, camera_index: int = 0):
        super().__init__()
        self.setWindowTitle("Post Seal Vision System")
        self.camera = cam.Camera(camera_index)
        self.control_values = dict(cam.CONTROL_DEFAULTS)
        self.pending_roi_label: str | None = None
        self.selected_control: str | None = None
        self.running_inspection = False
        self.roi_map: dict[str, tuple[int, int, int, int]] = {}
        # unit alignment feature removed
        # self.unit_alignment_state kept for backward-compat if needed, but not used
        self.unit_alignment_state = {"count": 0, "has_full_group": False}
        self.last_inspection_summary: dict | None = None
        # Arduino serial helper (non-blocking; ArduinoSerial handles missing pyserial)
        try:
            self.arduino = ArduinoSerial(port="COM3", baudrate=9600)
        except Exception:
            self.arduino = None

        self._build_ui()
        self._start_timer()

        if not self.camera.is_open():
            self.log("Failed to open camera. Check the connection and camera index.")

    def _build_ui(self):
        container = QWidget()
        self.setCentralWidget(container)
        layout = QGridLayout(container)
        layout.setSpacing(8)

        self.binary_view = ImageLabel("Binarize view")
        self.original_view = ImageLabel("Original view")
        self.gray_view = ImageLabel("Grayscale view")

        self.original_view.actionRequested.connect(self.handle_action)
        self.original_view.roiDefined.connect(self.handle_roi_defined)

        layout.addWidget(self.binary_view, 0, 0)
        layout.addWidget(self.original_view, 0, 1)
        layout.addWidget(self.gray_view, 1, 0)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # Arduino controls removed (handled externally)

        output_group = QGroupBox("Output inspection")
        output_layout = QVBoxLayout(output_group)
        self.count_label = QLabel("Inspections: 0/0")
        self.count_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2ecc71;")
        self.status_label = QLabel("WAITING")
        self.status_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #2ecc71;")
        self.detail_label = QLabel("Define all ROIs and click Start inspection")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("font-size: 16px; color: #e74c3c;")
        output_layout.addWidget(self.count_label)
        output_layout.addWidget(self.status_label)
        output_layout.addWidget(self.detail_label)
        right_layout.addWidget(output_group, stretch=3)

        log_group = QGroupBox("System log")
        log_layout = QVBoxLayout(log_group)
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("background-color: #111; color: #eee;")
        log_layout.addWidget(self.log_display)
        right_layout.addWidget(log_group, stretch=2)

        layout.addWidget(right_panel, 1, 1)
        layout.setRowStretch(0, 2)
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        self.statusBar().showMessage("Right-click original view to open camera controls, inspections, or start inspection.")

    def _start_timer(self) -> None:
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(20)

    def update_frame(self) -> None:
        frame = self.camera.read_frame()
        if frame is None:
            return

        processed = cam.adjust_image(frame, self.control_values)
        gray = cam.to_gray(processed)
        binary = cam.to_binary(gray)

        self._update_image_label(self.original_view, processed)
        self._update_image_label(self.gray_view, gray, is_gray=True)
        self._update_image_label(self.binary_view, binary, is_gray=True)
        self.original_view.set_roi_rects(list(self.roi_map.items()))

        if self.running_inspection:
            self._run_real_time_inspection(frame, gray, binary)

    def _update_image_label(self, label: ImageLabel, image, is_gray: bool = False) -> None:
        if image is None or image.size == 0:
            return
        if is_gray:
            height, width = image.shape
            qimage = QImage(image.data, width, height, width, QImage.Format.Format_Grayscale8)
        else:
            height, width, channels = image.shape
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            qimage = QImage(rgb_image.data, width, height, width * channels, QImage.Format.Format_RGB888)

        pixmap = QPixmap.fromImage(qimage).scaled(
            label.width(), label.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation
        )
        label.set_pixmap(pixmap)

    def handle_action(self, category: str, value: str) -> None:
        if category == "action" and value == "start inspection":
            self.toggle_inspection()
            return
        if category == "control":
            self.selected_control = value
            self.log(f"Selected camera control '{value}'. Press 'd' to increase, 'a' to decrease.")
            return
        if category == "inspection":
            self.pending_roi_label = value
            self.original_view.set_pending_roi_label(value)
            self.log(f"Selected inspection '{value}'. Draw ROI in the original view.")
            return

    def handle_roi_defined(self, preview_roi: tuple[int, int, int, int]) -> None:
        if not self.pending_roi_label:
            return
        self.roi_map[self.pending_roi_label] = preview_roi
        self.original_view.set_roi_rects(list(self.roi_map.items()))
        self.log(f"ROI defined for '{self.pending_roi_label}': {preview_roi}")
        self.pending_roi_label = None
        self.original_view.set_pending_roi_label(None)
        if len(self.roi_map) == len(insp.REQUIRED_INSPECTIONS):
            self.log("All ROIs are defined. You can now start inspection.")

    def toggle_inspection(self) -> None:
        if self.running_inspection:
            self.running_inspection = False
            self.log("Inspection stopped.")
            return

        missing = [name for name in insp.REQUIRED_INSPECTIONS if name not in self.roi_map]
        if missing:
            self.log(f"Cannot start inspection. Missing ROIs: {', '.join(missing)}")
            return

        self.running_inspection = True
        self.log("Inspection started.")
        self.selected_control = None
        self.pending_roi_label = None
        self.original_view.set_pending_roi_label(None)

    def _run_real_time_inspection(self, frame, gray, binary) -> None:
        results = []
        # Only use the required inspections defined in `inspection.py`
        upper_roi = self.roi_map["upper sealing"]
        offset_roi = self.roi_map["offset sealing"]

        upper_frame_roi = cam.scale_roi_to_frame(upper_roi, frame)
        offset_frame_roi = cam.scale_roi_to_frame(offset_roi, frame)

        upper_binary = cam.crop_roi(binary, upper_frame_roi)
        offset_binary = cam.crop_roi(binary, offset_frame_roi)

        results.append(insp.inspect_upper_sealing(upper_binary))
        results.append(insp.inspect_offset_sealing(offset_binary))

        summary = insp.build_summary(results)
        self.last_inspection_summary = summary
        self._display_inspection_result(summary)
        self._log_inspection_summary(results)

    def _display_inspection_result(self, summary: dict) -> None:
        self.count_label.setText(summary["count_text"])
        self.status_label.setText(summary["status"])
        self.detail_label.setText(summary["summary"])
        success_color = "#2ecc71" if summary["passed"] else "#e74c3c"
        self.status_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {success_color};")
        self.detail_label.setStyleSheet(f"font-size: 16px; color: {success_color};")
        # Notify Arduino of PASS/FAIL
        try:
            self._send_arduino_status("PASS" if summary.get("passed", False) else "FAIL")
        except Exception:
            pass

    def _send_arduino_status(self, status: str) -> None:
        if getattr(self, "arduino", None) is None:
            self.log("Arduino serial helper not initialized.")
            return
        try:
            if self.arduino.enabled:
                sent = self.arduino.send_status(status)
                if sent:
                    self.log(f"Arduino status sent: {status}")
                else:
                    self.log(f"Arduino status failed to send: {status}")
            else:
                self.log("Arduino serial port not available.")
        except Exception as e:
            self.log(f"Arduino send error: {e}")

    def _log_inspection_summary(self, results: list[dict]) -> None:
        entry = []
        for result in results:
            if result["name"] == "unit alignment":
                entry.append(f"[unit alignment] count={result['count']} holes={result['hole_count']}")
            else:
                ratio_text = f"{result['ratio']:.1%}"
                entry.append(f"[{result['name']}] {result['message']} ({ratio_text})")
        self.log(" | ".join(entry))

    def log(self, message: str) -> None:
        self.log_display.append(message)
        self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum())

    def keyPressEvent(self, event) -> None:
        if not self.selected_control:
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_D:
            delta = 10
        elif event.key() == Qt.Key.Key_A:
            delta = -10
        elif event.key() == Qt.Key.Key_Escape:
            self.selected_control = None
            self.statusBar().showMessage("Camera control deselected.")
            self.log("Camera control deselected.")
            return
        else:
            super().keyPressEvent(event)
            return

        current_value = self.control_values[self.selected_control]
        new_value = cam.clamp_control(self.selected_control, current_value + delta)
        self.control_values[self.selected_control] = new_value
        self.statusBar().showMessage(f"{self.selected_control} set to {new_value}")
        self.log(f"{self.selected_control} set to {new_value}")

    def closeEvent(self, event) -> None:
        self.camera.release()
        super().closeEvent(event)

def create_main_window(camera_index: int = 0) -> MainWindow:
    return MainWindow(camera_index)
