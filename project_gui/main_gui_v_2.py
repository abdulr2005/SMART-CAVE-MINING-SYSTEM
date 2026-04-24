
import os
os.environ["ULTRALYTICS_OFFLINE"] = "1"

#import ultralytics  # now won't hang on is_online()
import sys
import ultralytics
import cv2
import json
import socket
import threading
import numpy as np
import time
from collections import deque
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QGroupBox, QLineEdit, QTextEdit,
    QFileDialog, QFrame, QTabWidget, QSizePolicy, QSlider,
    QScrollArea, QGridLayout, QSpacerItem, QSplitter,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QRect, QPointF, QRectF
from PyQt6.QtGui import (
    QImage, QPixmap, QFont, QPainter, QPen, QColor, QBrush,
    QLinearGradient, QKeySequence, QShortcut, QPolygonF,
)

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
SETTINGS_FILE     = "visionos_settings.json"
PPE_CONF          = 0.40
GEM_CONF          = 0.40
DEFAULT_PPE_MODEL = r"C:\Users\abdul\Desktop\PPE Detection.v1i.yolov8\runs\detect\train11\weights\best.pt"
DEFAULT_GEM_MODEL = r"C:\Users\abdul\Desktop\PPE Detection.v1i.yolov8\best_v_2.pt"

HQ_IP    = "192.168.4.1"
CAR_IP   = "192.168.4.1"   # same as HQ — all traffic goes through HQ
HQ_PORT  = 4210
CAR_PORT = 4210              # same port as HQ

SPARKLINE_LEN = 60   # number of historical samples kept per sensor


def _load_settings() -> dict:
    try:
        return json.loads(Path(SETTINGS_FILE).read_text())
    except Exception:
        return {}


def _save_settings(d: dict):
    try:
        Path(SETTINGS_FILE).write_text(json.dumps(d, indent=2))
    except Exception:
        pass


# ── Shared UDP socket ─────────────────────────────────────────────────────────
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    udp_sock.bind(("", HQ_PORT))
except OSError as e:
    print(f"[WARN] Could not bind to port {HQ_PORT}: {e}")
udp_sock.settimeout(1.0)

send_sock = udp_sock
recv_sock = udp_sock


# ─────────────────────────────────────────────────────────────────────────────
#  DESIGN TOKENS
# ─────────────────────────────────────────────────────────────────────────────
C = {
    "bg":      "#06080e",
    "surface": "#0b1018",
    "panel":   "#0f1822",
    "border":  "#182535",
    "accent":  "#00d4ff",
    "accent2": "#0055ee",
    "green":   "#00f07a",
    "red":     "#ff2244",
    "amber":   "#ffbb44",
    "purple":  "#c87cff",
    "text":    "#b8cedd",
    "muted":   "#354d63",
    "grid":    "#0d1520",
}

STYLE = f"""
QMainWindow, QWidget {{
    background: {C['bg']};
    color: {C['text']};
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}}
QScrollBar:vertical {{
    background: {C['bg']}; width: 6px; border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {C['border']}; border-radius: 3px; min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QGroupBox {{
    border: 1px solid {C['border']};
    border-radius: 10px;
    margin-top: 22px;
    padding: 14px 10px 10px 10px;
    font-weight: 700;
    font-size: 10px;
    letter-spacing: 1.5px;
    color: {C['muted']};
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {C['muted']};
}}
QLineEdit {{
    background: {C['bg']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 8px 12px;
    color: {C['text']};
    font-size: 12px;
}}
QLineEdit:focus {{ border-color: {C['accent']}; }}
QTextEdit {{
    background: {C['bg']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 8px;
    color: {C['text']};
    font-family: 'Consolas', monospace;
    font-size: 11px;
}}
QComboBox {{
    background: {C['panel']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 8px 12px;
    color: {C['text']};
    min-height: 36px;
}}
QComboBox:hover {{ border-color: {C['accent']}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {C['panel']};
    border: 1px solid {C['border']};
    color: {C['text']};
    selection-background-color: {C['accent2']};
    outline: none;
}}
QSlider::groove:horizontal {{
    background: {C['border']}; height: 4px; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {C['accent']};
    width: 14px; height: 14px; border-radius: 7px; margin: -5px 0;
}}
QSlider::sub-page:horizontal {{
    background: {C['accent']}; border-radius: 2px;
}}
QTabWidget::pane {{
    border: 1px solid {C['border']};
    border-radius: 10px;
    background: {C['surface']};
    margin-top: -1px;
}}
QTabBar::tab {{
    background: {C['panel']};
    border: 1px solid {C['border']};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 9px 22px;
    margin-right: 4px;
    font-weight: 700;
    font-size: 12px;
    color: {C['muted']};
    min-width: 155px;
}}
QTabBar::tab:selected {{
    background: {C['surface']};
    color: {C['accent']};
}}
QTabBar::tab:hover:!selected {{ color: {C['text']}; }}
QPushButton {{
    background: {C['panel']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 9px 14px;
    color: {C['text']};
    font-weight: 700;
    font-size: 12px;
    min-height: 36px;
}}
QPushButton:hover {{
    border-color: {C['accent']};
    color: {C['accent']};
}}
QPushButton:pressed {{ background: {C['bg']}; }}
QPushButton#BtnPrimary {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {C['accent2']}, stop:1 {C['accent']});
    border: none; color: #000;
}}
QPushButton#BtnPrimary:hover {{ color: #000; opacity: 0.9; }}
QPushButton#BtnGreen {{
    background: rgba(0,240,122,0.08);
    border-color: {C['green']}; color: {C['green']};
}}
QPushButton#BtnGreen:hover {{ background: rgba(0,240,122,0.20); }}
QPushButton#BtnRed {{
    background: rgba(255,34,68,0.08);
    border-color: {C['red']}; color: {C['red']};
}}
QPushButton#BtnRed:hover {{ background: rgba(255,34,68,0.20); }}
QPushButton#BtnAmber {{
    background: rgba(255,187,68,0.08);
    border-color: {C['amber']}; color: {C['amber']};
}}
QPushButton#BtnAmber:hover {{ background: rgba(255,187,68,0.20); }}
QPushButton#BtnPurple {{
    background: rgba(200,124,255,0.08);
    border-color: {C['purple']}; color: {C['purple']};
}}
QPushButton#BtnPurple:hover {{ background: rgba(200,124,255,0.20); }}
QPushButton#DPadBtn {{
    background: {C['panel']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    min-height: 48px;
    min-width: 48px;
    font-size: 18px;
}}
QPushButton#DPadBtn:hover {{
    background: rgba(0,212,255,0.15);
    border-color: {C['accent']};
}}
QPushButton#DPadBtn:pressed {{
    background: rgba(0,212,255,0.30);
}}
QLabel#Logo {{
    font-size: 18px; font-weight: 800;
    letter-spacing: 3px; color: {C['accent']};
}}
QLabel#Badge {{
    background: {C['panel']};
    border: 1px solid {C['border']};
    border-radius: 20px; padding: 3px 12px;
    font-size: 11px; font-family: Consolas;
    color: {C['muted']}; font-weight: 700;
}}
QLabel#BadgeLive {{
    background: rgba(0,240,122,0.08);
    border: 1px solid {C['green']};
    border-radius: 20px; padding: 3px 12px;
    font-size: 11px; font-family: Consolas;
    color: {C['green']}; font-weight: 700;
}}
QLabel#BadgeWarn {{
    background: rgba(255,187,68,0.08);
    border: 1px solid {C['amber']};
    border-radius: 20px; padding: 3px 12px;
    font-size: 11px; font-family: Consolas;
    color: {C['amber']}; font-weight: 700;
}}
QLabel#BadgeDanger {{
    background: rgba(255,34,68,0.08);
    border: 1px solid {C['red']};
    border-radius: 20px; padding: 3px 12px;
    font-size: 11px; font-family: Consolas;
    color: {C['red']}; font-weight: 700;
}}
QLabel#SectionTitle {{
    font-size: 10px; font-weight: 700;
    letter-spacing: 2px; color: {C['muted']};
}}
QLabel#AlertItem {{
    background: rgba(255,34,68,0.07);
    border-left: 3px solid {C['red']};
    border-radius: 4px;
    padding: 4px 8px;
    font-family: Consolas;
    font-size: 11px;
    color: {C['text']};
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  DETECTORS
# ─────────────────────────────────────────────────────────────────────────────
_PAL = [(0, 212, 255), (0, 240, 122), (255, 34, 68), (200, 124, 255), (255, 187, 68)]


def _col(cid: int):
    return _PAL[cid % len(_PAL)]


class GemDetector:
    def __init__(self):
        self.model = None
        self.names = {}

    def load(self, path: str) -> str:
        try:
            from ultralytics import YOLO
            pt = Path(path)
            if pt.is_dir():
                pts = list(pt.rglob("*.pt"))
                pt  = pts[0] if pts else pt / "best.pt"
            self.model = YOLO(str(pt))
            self.names = self.model.names
            return f"✅ Gemstone model: {pt.name}"
        except Exception as e:
            return f"❌ Gemstone load failed: {e}"

    def detect(self, frame: np.ndarray):
        if not self.model:
            return frame, 0
        vis = frame.copy()
        results = self.model(frame, conf=GEM_CONF, imgsz=320, verbose=False)[0]
        count = len(results.boxes)
        for box in results.boxes:
            c = int(box.cls[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            col = _col(c)
            cv2.rectangle(vis, (x1, y1), (x2, y2), col, 2)
            cv2.putText(vis, f"{self.names.get(c, c)} {float(box.conf[0]):.0%}",
                        (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2)
        return vis, count


class PPEDetector:
    PPE_MAP = {0: "Person", 4: "Helmet", 9: "Vest"}

    def __init__(self):
        self.model = None
        self.names = {}

    def load(self, path: str) -> str:
        try:
            from ultralytics import YOLO
            self.model = YOLO(path)
            self.names = self.model.names
            return f"✅ PPE model: {Path(path).name}"
        except Exception as e:
            return f"❌ PPE load failed: {e}"

    def detect(self, frame: np.ndarray):
        if not self.model:
            return frame, False, 0
        vis     = frame.copy()
        results = self.model(frame, conf=PPE_CONF, imgsz=320, verbose=False)[0]
        ids     = [int(b.cls[0]) for b in results.boxes]
        safe    = (0 in ids) and (4 in ids) and (9 in ids)
        count   = len(results.boxes)
        for box in results.boxes:
            c = int(box.cls[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            col   = (0, 240, 122) if c in (4, 9) else (255, 34, 68)
            label = self.PPE_MAP.get(c, self.names.get(c, f"ID {c}"))
            cv2.rectangle(vis, (x1, y1), (x2, y2), col, 2)
            cv2.putText(vis, label, (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2)
        return vis, safe, count


# ─────────────────────────────────────────────────────────────────────────────
#  WORKER THREADS
# ─────────────────────────────────────────────────────────────────────────────

class InferenceWorker(QThread):
    result = pyqtSignal(np.ndarray, str, str, int)

    def __init__(self, gem: GemDetector, ppe: PPEDetector):
        super().__init__()
        self.gem    = gem
        self.ppe    = ppe
        self.mode   = "Gemstone"
        self._frame = None
        self._stop  = False
        self._lock  = threading.Lock()

    def push(self, frame: np.ndarray):
        with self._lock:
            self._frame = frame

    def set_mode(self, mode: str):
        self.mode = mode

    def run(self):
        while not self._stop:
            with self._lock:
                f = self._frame
                self._frame = None
            if f is not None:
                if "Gem" in self.mode:
                    out, count = self.gem.detect(f)
                    self.result.emit(out, "GEMSTONE ANALYSIS ACTIVE", C["accent"], count)
                else:
                    out, safe, count = self.ppe.detect(f)
                    txt   = "SYSTEM STATE: SAFE ✓" if safe else "SYSTEM STATE: DANGER ✗"
                    color = C["green"] if safe else C["red"]
                    self.result.emit(out, txt, color, count)
            else:
                self.msleep(8)

    def stop(self):
        self._stop = True


class WebcamThread(QThread):
    frame_ready   = pyqtSignal(np.ndarray)
    status_update = pyqtSignal(str)
    raw_frame     = pyqtSignal(np.ndarray)   # unprocessed frame for screenshot

    def __init__(self, index=0):
        super().__init__()
        self.index = index
        self._stop = threading.Event()

    def run(self):
        cap = cv2.VideoCapture(self.index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        if not cap.isOpened():
            self.status_update.emit("❌ Cannot open camera")
            return
        self.status_update.emit("✅ Camera stream active")
        while not self._stop.is_set():
            ret, frame = cap.read()
            if ret:
                self.raw_frame.emit(frame.copy())
                self.frame_ready.emit(frame)
            else:
                time.sleep(0.01)
        cap.release()

    def stop(self):
        self._stop.set()


class VideoFileThread(QThread):
    frame_ready   = pyqtSignal(np.ndarray)
    status_update = pyqtSignal(str)
    raw_frame     = pyqtSignal(np.ndarray)

    def __init__(self, path: str):
        super().__init__()
        self.path  = path
        self._stop = threading.Event()

    def run(self):
        cap   = cv2.VideoCapture(self.path)
        fps   = cap.get(cv2.CAP_PROP_FPS) or 30
        delay = 1.0 / fps
        self.status_update.emit(f"✅ Playing: {Path(self.path).name}")
        while not self._stop.is_set():
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            self.raw_frame.emit(frame.copy())
            self.frame_ready.emit(frame)
            time.sleep(delay)
        cap.release()

    def stop(self):
        self._stop.set()


class UDPListener(QThread):
    received   = pyqtSignal(str, float)   # (message, latency_ms)

    def run(self):
        while True:
            try:
                t0   = time.perf_counter()
                data, _ = recv_sock.recvfrom(1024)
                lat  = (time.perf_counter() - t0) * 1000
                self.received.emit(data.decode(errors="replace"), lat)
            except socket.timeout:
                pass
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
#  CUSTOM WIDGETS
# ─────────────────────────────────────────────────────────────────────────────

class VideoFrame(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._idle = True
        self.setStyleSheet(f"background: {C['bg']}; border-radius: 10px;")

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._idle:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            # Corner brackets
            pen = QPen(QColor(C["border"]), 2)
            p.setPen(pen)
            sz = 22
            w, h = self.width(), self.height()
            for x, y, dx, dy in [(10,10,1,1),(w-10,10,-1,1),(10,h-10,1,-1),(w-10,h-10,-1,-1)]:
                p.drawLine(x, y, x + dx*sz, y)
                p.drawLine(x, y, x, y + dy*sz)
            # Scan grid
            pen2 = QPen(QColor(C["grid"]), 1)
            p.setPen(pen2)
            for gx in range(0, w, 40):
                p.drawLine(gx, 0, gx, h)
            for gy in range(0, h, 40):
                p.drawLine(0, gy, w, gy)
            # Center icon
            p.setPen(QColor(C["muted"]))
            p.setFont(QFont("Segoe UI", 36))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "📡")
            p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            r = self.rect()
            r.setTop(r.center().y() + 44)
            p.drawText(r, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                       "FEED  DISCONNECTED")
            p.end()

    def show_frame(self, frame: np.ndarray):
        self._idle = False
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qi = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        px = QPixmap.fromImage(qi).scaled(
            self.width(), self.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(px)

    def set_idle(self):
        self._idle = True
        self.clear()
        self.update()


class SparklineWidget(QWidget):
    """Fully flexible line chart — grows/shrinks with its grid cell."""

    def __init__(self, label: str, unit: str = "", color: str = None, maxlen: int = SPARKLINE_LEN):
        super().__init__()
        self.label  = label
        self.unit   = unit
        self.color  = QColor(color or C["accent"])
        self.data   = deque(maxlen=maxlen)
        self.setMinimumSize(120, 80)          # sensible floor only
        self.setSizePolicy(                   # expands in both directions
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setStyleSheet(
            f"background: {C['bg']}; border: 1px solid {C['border']}; border-radius: 10px;"
        )
        self._last = "—"

    def push(self, value: float):
        self.data.append(value)
        self._last = f"{value:.1f}{self.unit}"
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Rounded background
        p.setBrush(QBrush(QColor(C["bg"])))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, 10, 10)

        # Scale font sizes proportionally to widget height
        lbl_fs  = max(7,  int(h * 0.07))
        val_fs  = max(11, int(h * 0.18))
        pad_x   = max(10, int(w * 0.03))
        pad_top = max(6,  int(h * 0.06))

        # Label row
        p.setFont(QFont("Consolas", lbl_fs, QFont.Weight.Bold))
        p.setPen(QColor(C["muted"]))
        lbl_h = lbl_fs + 6
        p.drawText(
            QRect(pad_x, pad_top, w - pad_x * 2, lbl_h),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.label.upper(),
        )

        # Value row
        val_top = pad_top + lbl_h + 2
        val_h   = val_fs + 8
        p.setFont(QFont("Consolas", val_fs, QFont.Weight.Bold))
        p.setPen(self.color)
        p.drawText(
            QRect(pad_x, val_top, w - pad_x * 2, val_h),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._last,
        )

        # Sparkline area starts below the value row
        spark_top = val_top + val_h + max(4, int(h * 0.04))
        plot_h    = h - spark_top - max(8, int(h * 0.06))

        if len(self.data) < 2 or plot_h < 10:
            p.end()
            return

        vals   = list(self.data)
        mn, mx = min(vals), max(vals)
        rng    = mx - mn if mx != mn else 1.0
        plot_w = w - pad_x * 2

        # Fill gradient
        grad = QLinearGradient(0, spark_top, 0, spark_top + plot_h)
        grad.setColorAt(0, QColor(self.color.red(), self.color.green(), self.color.blue(), 80))
        grad.setColorAt(1, QColor(self.color.red(), self.color.green(), self.color.blue(), 0))
        pts = []
        for i, v in enumerate(vals):
            x = pad_x + (i / (len(vals) - 1)) * plot_w
            y = spark_top + plot_h - ((v - mn) / rng) * plot_h
            pts.append(QPointF(x, y))
        bottom_y = spark_top + plot_h
        poly = QPolygonF(pts + [QPointF(pts[-1].x(), bottom_y), QPointF(pts[0].x(), bottom_y)])
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(poly)

        # Line — thickness scales with widget height
        line_w = max(1.5, h * 0.012)
        pen = QPen(self.color, line_w)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolyline(QPolygonF(pts))

        p.end()


class StatCard(QFrame):
    def __init__(self, label: str, init_val="—"):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background: {C['bg']};
                border: 1px solid {C['border']};
                border-radius: 8px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)
        self.val = QLabel(init_val)
        self.val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.val.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        self.val.setStyleSheet(f"color: {C['accent']};")
        lbl = QLabel(label.upper())
        lbl.setObjectName("SectionTitle")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.val)
        lay.addWidget(lbl)

    def update_value(self, v: str, color: str = None):
        self.val.setText(v)
        col = color or C["accent"]
        self.val.setStyleSheet(
            f"color: {col}; font-size: 16px; font-weight: 800; font-family: Consolas;"
        )


class DirectionalPad(QWidget):
    """WASD-style d-pad for car control."""
    command = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setFixedSize(170, 160)
        grid = QGridLayout(self)
        grid.setSpacing(5)
        grid.setContentsMargins(8, 8, 8, 8)

        def _btn(icon, cmd, row, col):
            b = QPushButton(icon)
            b.setObjectName("DPadBtn")
            b.clicked.connect(lambda: self.command.emit(cmd))
            grid.addWidget(b, row, col)
            return b

        _btn("▲", "FORWARD",  0, 1)
        _btn("◀️", "LEFT",     1, 0)
        _btn("■", "STOP",     1, 1)
        _btn("▶️", "RIGHT",    1, 2)
        _btn("▼", "BACKWARD", 2, 1)


class SectionHeader(QWidget):
    def __init__(self, title: str):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 4)
        lay.setSpacing(7)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {C['accent']}; font-size: 7px;")
        lay.addWidget(dot)
        lbl = QLabel(title.upper())
        lbl.setObjectName("SectionTitle")
        lay.addWidget(lbl)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {C['border']};")
        lay.addWidget(line, 1)


def _badge(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Badge")
    return lbl


def _refresh_style(w):
    w.style().unpolish(w)
    w.style().polish(w)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VisionOS Pro  v2  ·  Smart Monitoring + HQ + Car Control")
        self.resize(1480, 900)
        self.setMinimumSize(820, 580)
        self.setStyleSheet(STYLE)

        self._cfg = _load_settings()

        self.gem_det = GemDetector()
        self.ppe_det = PPEDetector()

        self.inf = InferenceWorker(self.gem_det, self.ppe_det)
        self.inf.result.connect(self._on_frame)
        self.inf.start()

        self.cam_thread    = None
        self._last_frame   = None   # raw frame for screenshot
        self._fps_count    = 0
        self._sensor_registered   = False
        self._last_sensor_time    = time.time()
        self._car_speed    = 200    # default PWM

        self.udp_listener = UDPListener()
        self.udp_listener.received.connect(self._on_udp_received)
        self.udp_listener.start()

        self._build_ui()
        self._apply_saved_settings()
        self._setup_shortcuts()

        self._fps_timer = QTimer()
        self._fps_timer.timeout.connect(self._tick_fps)
        self._fps_timer.start(1000)

        self._ping_timer = QTimer()
        self._ping_timer.timeout.connect(self._ping_hq)
        QTimer.singleShot(1000, self._start_ping)

        # Auto-reconnect: if sensor data stops for > 8 s, restart pings
        self._watchdog = QTimer()
        self._watchdog.timeout.connect(self._sensor_watchdog)
        self._watchdog.start(4000)

        QTimer.singleShot(600, self._reload_models)

    # ─────────────────────────────────────────────────────────────────────────
    #  BUILD UI
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._make_header())
        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)
        bl.addWidget(self._make_sidebar())
        bl.addWidget(self._make_main(), 1)
        lay.addWidget(body, 1)

    # ── Header ───────────────────────────────────────────────────────────────

    def _make_header(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"background: {C['surface']}; border-bottom: 1px solid {C['border']};")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(12)

        logo = QLabel("🛰  VISION OS  PRO  v2")
        logo.setObjectName("Logo")
        lay.addWidget(logo)
        lay.addStretch()

        self.badge_ai   = _badge("⬤  AI: STANDBY")
        self.badge_udp  = _badge("⬤  UDP: IDLE")
        self.badge_ping = _badge("⬤  PING: — ms")
        self.badge_cam  = _badge("⬤  CAM: OFF")
        self.badge_car  = _badge("⬤  CAR: IDLE")
        for b in (self.badge_ai, self.badge_udp, self.badge_ping, self.badge_cam, self.badge_car):
            lay.addWidget(b)

        btn_ss = QPushButton("📷")
        btn_ss.setFixedSize(36, 36)
        btn_ss.setToolTip("Screenshot")
        btn_ss.clicked.connect(self._take_screenshot)
        btn_ss.setStyleSheet(f"""
            QPushButton {{ background: {C['panel']}; border: 1px solid {C['border']};
                           border-radius: 18px; font-size: 15px; }}
            QPushButton:hover {{ border-color: {C['accent']}; }}
        """)
        lay.addWidget(btn_ss)

        return bar

    # ── Sidebar ──────────────────────────────────────────────────────────────

    def _make_sidebar(self) -> QWidget:
        inner = QWidget()
        inner.setStyleSheet(f"background: {C['surface']};")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(6)

        lay.addWidget(SectionHeader("Analytics Module"))
        self.module_combo = QComboBox()
        self.module_combo.addItems(["💎  Gemstone Module", "🦺  PPE Safety Module"])
        self.module_combo.currentTextChanged.connect(self._on_module_change)
        lay.addWidget(self.module_combo)

        lay.addWidget(SectionHeader("Model Paths"))
        lay.addWidget(QLabel("PPE Model (.pt):"))
        self.ppe_path_edit = QLineEdit(self._cfg.get("ppe_model", DEFAULT_PPE_MODEL))
        lay.addWidget(self.ppe_path_edit)
        lay.addWidget(QLabel("Gemstone Model (.pt):"))
        self.gem_path_edit = QLineEdit(self._cfg.get("gem_model", DEFAULT_GEM_MODEL))
        lay.addWidget(self.gem_path_edit)

        lay.addWidget(SectionHeader("Confidence Threshold"))
        conf_row = QHBoxLayout()
        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(10, 90)
        self.conf_slider.setValue(int(self._cfg.get("conf", 40)))
        self.conf_lbl = QLabel(f"{self.conf_slider.value()}%")
        self.conf_lbl.setFixedWidth(38)
        self.conf_lbl.setStyleSheet(f"color:{C['accent']}; font-family:Consolas; font-weight:700;")
        self.conf_slider.valueChanged.connect(lambda v: self.conf_lbl.setText(f"{v}%"))
        conf_row.addWidget(self.conf_slider, 1)
        conf_row.addWidget(self.conf_lbl)
        cw = QWidget(); cw.setLayout(conf_row)
        lay.addWidget(cw)

        btn_sync = QPushButton("🔄  Sync Models")
        btn_sync.setObjectName("BtnPrimary")
        btn_sync.clicked.connect(self._reload_models)
        lay.addWidget(btn_sync)

        lay.addWidget(SectionHeader("Input Sources"))
        btn_cam = QPushButton("🎥  Activate Webcam")
        btn_cam.setObjectName("BtnGreen")
        btn_cam.clicked.connect(self._start_webcam)
        lay.addWidget(btn_cam)

        btn_file = QPushButton("📂  Analyze Image / Video")
        btn_file.setObjectName("BtnAmber")
        btn_file.clicked.connect(self._upload_file)
        lay.addWidget(btn_file)

        btn_stop = QPushButton("🛑  Kill Stream")
        btn_stop.setObjectName("BtnRed")
        btn_stop.clicked.connect(self._stop_cam)
        lay.addWidget(btn_stop)

        lay.addWidget(SectionHeader("System Log"))
        self.vision_log = QTextEdit()
        self.vision_log.setReadOnly(True)
        self.vision_log.setMinimumHeight(150)
        lay.addWidget(self.vision_log)

        btn_save = QPushButton("💾  Save Settings")
        btn_save.clicked.connect(self._persist_settings)
        lay.addWidget(btn_save)

        lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setFixedWidth(300)
        scroll.setStyleSheet(
            f"background: {C['surface']}; border-right: 1px solid {C['border']};"
        )
        return scroll

    # ── Main ─────────────────────────────────────────────────────────────────

    def _make_main(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 14, 16, 16)
        lay.setSpacing(12)
        tabs = QTabWidget()
        tabs.addTab(self._make_vision_tab(),    "🔬  Vision Analytics")
        tabs.addTab(self._make_hq_tab(),        "📡  HQ + Car Control")
        tabs.addTab(self._make_sensors_tab(),   "📊  Sensor History")
        tabs.addTab(self._make_alerts_tab(),    "⚠️  Alert Log")
        lay.addWidget(tabs)
        return w

    # ── Vision Tab ───────────────────────────────────────────────────────────

    def _make_vision_tab(self) -> QWidget:
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        stats_row = QHBoxLayout()
        self.stat_det = StatCard("Detections")
        self.stat_fps = StatCard("FPS")
        self.stat_mod = StatCard("Module", "GEM")
        self.stat_mod.update_value("GEM", C["accent"])
        for s in (self.stat_det, self.stat_fps, self.stat_mod):
            stats_row.addWidget(s)
        lay.addLayout(stats_row)

        self.video_frame = VideoFrame()
        lay.addWidget(self.video_frame, 1)

        self.status_bar = QLabel("AWAITING SIGNAL")
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_status("AWAITING SIGNAL", C["muted"])
        lay.addWidget(self.status_bar)

        return page

    # ── HQ + Car Tab ─────────────────────────────────────────────────────────

    def _make_hq_tab(self) -> QWidget:
        page = QWidget()
        lay  = QHBoxLayout(page)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(14)

        left     = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(10)

        # Connection settings
        conn_box = QGroupBox("UDP Connection")
        conn_lay = QGridLayout(conn_box)
        conn_lay.addWidget(QLabel("HQ IP:"),  0, 0)
        self.hq_ip = QLineEdit(self._cfg.get("hq_ip", HQ_IP))
        self.hq_ip.setMaximumWidth(140)
        conn_lay.addWidget(self.hq_ip, 0, 1)
        conn_lay.addWidget(QLabel("Car IP:"), 1, 0)
        self.car_ip = QLineEdit(self._cfg.get("car_ip", CAR_IP))
        self.car_ip.setMaximumWidth(140)
        conn_lay.addWidget(self.car_ip, 1, 1)
        conn_lay.addWidget(QLabel("HQ Port:"),  0, 2)
        self.hq_port = QLineEdit(str(self._cfg.get("hq_port", HQ_PORT)))
        self.hq_port.setMaximumWidth(70)
        conn_lay.addWidget(self.hq_port, 0, 3)
        conn_lay.addWidget(QLabel("Car Port:"), 1, 2)
        self.car_port = QLineEdit(str(self._cfg.get("car_port", CAR_PORT)))
        self.car_port.setMaximumWidth(70)
        conn_lay.addWidget(self.car_port, 1, 3)

        # Ping button
        btn_ping = QPushButton("🔔 Test Ping")
        btn_ping.clicked.connect(self._manual_ping)
        conn_lay.addWidget(btn_ping, 2, 0, 1, 4)
        left_lay.addWidget(conn_box)

        # HQ sensor state cards
        state_box  = QGroupBox("Remote Sensor State  (HQ)")
        state_grid = QGridLayout(state_box)
        state_grid.setSpacing(8)
        self.state_cards = {}
        for i, (k, v) in enumerate([
            ("STATE","—"), ("TEMP","— °C"), ("HUMIDITY","— %"),
            ("GAS","—"),   ("FLOOD","—"),   ("SEISMIC","—"),
        ]):
            card = StatCard(k, v)
            state_grid.addWidget(card, i // 3, i % 3)
            self.state_cards[k] = card
        left_lay.addWidget(state_box)

        # Car encoder state
        enc_box  = QGroupBox("Car Encoder Data  (Live)")
        enc_grid = QGridLayout(enc_box)
        enc_grid.setSpacing(8)
        self.enc_cards = {}
        for i, (k, v) in enumerate([
            ("ENC LEFT","—"), ("ENC RIGHT","—"), ("DISTANCE","— cm"), ("CAR STATE","IDLE")
        ]):
            card = StatCard(k, v)
            enc_grid.addWidget(card, 0, i)
            self.enc_cards[k] = card
        left_lay.addWidget(enc_box)

        # Obstacle alert label (hidden by default)
        self.obstacle_lbl = QLabel("No obstacle detected")
        self.obstacle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.obstacle_lbl.setStyleSheet(f"""
            font-size: 13px; padding: 10px; border-radius: 8px;
            background: rgba(0,232,122,0.06);
            border: 1px solid {C['border']};
            color: {C['muted']};
        """)
        left_lay.addWidget(self.obstacle_lbl)

        # Commands row
        cmd_box = QGroupBox("Commands  →  HQ  +  Car")
        cmd_lay = QHBoxLayout(cmd_box)
        cmd_lay.setSpacing(10)
        for label, obj, cmd in [
            ("▶️  START",   "BtnGreen", "START"),
            ("↩  REVERSE", "BtnAmber", "REVERSE"),
            ("■  STOP",    "BtnRed",   "STOP"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName(obj)
            btn.setMinimumHeight(52)
            btn.clicked.connect(lambda _, c=cmd: self._send_cmd_both(c))
            cmd_lay.addWidget(btn)
        left_lay.addWidget(cmd_box)

        # ── D-Pad + Speed ─────────────────────────────────────────────────────
        dpad_box = QGroupBox("Directional Control  (Car only)  ·  W A S D  +  Space")
        dpad_outer = QHBoxLayout(dpad_box)

        self.dpad = DirectionalPad()
        self.dpad.command.connect(self._send_car_dir)
        dpad_outer.addWidget(self.dpad)

        speed_col = QVBoxLayout()
        speed_col.setSpacing(6)
        speed_lbl = QLabel("SPEED")
        speed_lbl.setObjectName("SectionTitle")
        speed_col.addWidget(speed_lbl)
        self.speed_slider = QSlider(Qt.Orientation.Vertical)
        self.speed_slider.setRange(80, 255)
        self.speed_slider.setValue(self._cfg.get("car_speed", 200))
        self.speed_slider.setFixedHeight(100)
        self.speed_val_lbl = QLabel(str(self.speed_slider.value()))
        self.speed_val_lbl.setStyleSheet(f"color:{C['accent']}; font-family:Consolas; font-weight:700;")
        self.speed_val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speed_slider.valueChanged.connect(self._on_speed_change)
        speed_col.addWidget(self.speed_slider)
        speed_col.addWidget(self.speed_val_lbl)
        speed_col.addStretch()
        dpad_outer.addLayout(speed_col)

        left_lay.addWidget(dpad_box)

        # Custom command
        custom_box = QGroupBox("Custom Command  →  HQ only")
        custom_lay = QHBoxLayout(custom_box)
        self.custom_edit = QLineEdit()
        self.custom_edit.setPlaceholderText("Type command and press Enter or Send…")
        self.custom_edit.returnPressed.connect(self._send_custom)
        send_btn = QPushButton("📤  Send")
        send_btn.setObjectName("BtnPrimary")
        send_btn.clicked.connect(self._send_custom)
        custom_lay.addWidget(self.custom_edit, 1)
        custom_lay.addWidget(send_btn)
        left_lay.addWidget(custom_box)
        left_lay.addStretch()

        lay.addWidget(left, 55)

        # Right: UDP log
        right     = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(6)
        right_lay.addWidget(SectionHeader("UDP Communication Log"))
        self.udp_log = QTextEdit()
        self.udp_log.setReadOnly(True)
        right_lay.addWidget(self.udp_log, 1)

        btn_clear = QPushButton("🗑  Clear Log")
        btn_clear.clicked.connect(self.udp_log.clear)
        right_lay.addWidget(btn_clear)

        lay.addWidget(right, 45)
        return page

    # ── Sensors History Tab ───────────────────────────────────────────────────

    def _make_sensors_tab(self) -> QWidget:
        page = QWidget()
        lay  = QGridLayout(page)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        # Equal stretch on every row and column → cells grow with the window
        for col in range(2):
            lay.setColumnStretch(col, 1)
        for row in range(3):
            lay.setRowStretch(row, 1)

        self.sparks = {}
        specs = [
            ("TEMP",     "°C",   C["accent"],  0, 0),
            ("HUMIDITY", "%",    C["purple"],  0, 1),
            ("GAS",      " ppm", C["amber"],   1, 0),
            ("FLOOD",    "",     C["red"],      1, 1),
            ("SEISMIC",  "",     C["green"],    2, 0),
            ("DISTANCE", " cm",  C["accent2"], 2, 1),
        ]
        for key, unit, col, row, column in specs:
            sp = SparklineWidget(key, unit, col)
            self.sparks[key] = sp
            lay.addWidget(sp, row, column)

        return page

    # ── Alerts Tab ───────────────────────────────────────────────────────────

    def _make_alerts_tab(self) -> QWidget:
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        hdr = QHBoxLayout()
        hdr.addWidget(SectionHeader("Danger & Warning Events"))
        hdr.addStretch()
        btn_clr = QPushButton("🗑  Clear Alerts")
        btn_clr.clicked.connect(self._clear_alerts)
        hdr.addWidget(btn_clr)
        lay.addLayout(hdr)

        self.alert_scroll = QScrollArea()
        self.alert_scroll.setWidgetResizable(True)
        self.alert_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.alert_inner = QWidget()
        self.alert_layout = QVBoxLayout(self.alert_inner)
        self.alert_layout.setSpacing(5)
        self.alert_layout.addStretch()
        self.alert_scroll.setWidget(self.alert_inner)
        lay.addWidget(self.alert_scroll, 1)

        return page

    # ─────────────────────────────────────────────────────────────────────────
    #  KEYBOARD SHORTCUTS
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        for key, cmd in [
            ("W", "FORWARD"),
            ("A", "LEFT"),
            ("S", "BACKWARD"),
            ("D", "RIGHT"),
            ("Space", "STOP"),
        ]:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(lambda c=cmd: self._send_car_dir(c))

        # Arrow keys as fallback
        for key, cmd in [
            ("Up",    "FORWARD"),
            ("Left",  "LEFT"),
            ("Down",  "BACKWARD"),
            ("Right", "RIGHT"),
        ]:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(lambda c=cmd: self._send_car_dir(c))

    # ─────────────────────────────────────────────────────────────────────────
    #  SETTINGS
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_saved_settings(self):
        pass  # values already applied via _cfg in widget creation

    def _persist_settings(self):
        d = {
            "ppe_model": self.ppe_path_edit.text(),
            "gem_model": self.gem_path_edit.text(),
            "hq_ip":     self.hq_ip.text(),
            "car_ip":    self.car_ip.text(),
            "hq_port":   int(self.hq_port.text()),
            "car_port":  int(self.car_port.text()),
            "conf":      self.conf_slider.value(),
            "car_speed": self.speed_slider.value(),
        }
        _save_settings(d)
        self._log_vision("💾 Settings saved to visionos_settings.json")

    # ─────────────────────────────────────────────────────────────────────────
    #  VISION LOGIC
    # ─────────────────────────────────────────────────────────────────────────

    def _on_module_change(self, text: str):
        mode = "Gemstone" if "Gem" in text else "PPE"
        self.inf.set_mode(mode)
        self.stat_mod.update_value(mode[:3].upper(), C["accent"])
        self._log_vision(f"Switched → {text.strip()}")

    def _reload_models(self):
        global PPE_CONF, GEM_CONF
        PPE_CONF = GEM_CONF = self.conf_slider.value() / 100
        self._log_vision("Syncing AI cores…")
        s1 = self.ppe_det.load(self.ppe_path_edit.text())
        s2 = self.gem_det.load(self.gem_path_edit.text())
        self._log_vision(s1)
        self._log_vision(s2)
        self.badge_ai.setObjectName("BadgeLive")
        self.badge_ai.setText("⬤  AI: READY")
        _refresh_style(self.badge_ai)

    def _start_webcam(self):
        self._stop_cam()
        self._log_vision("Initializing optic stream…")
        self.cam_thread = WebcamThread(0)
        self.cam_thread.frame_ready.connect(self.inf.push)
        self.cam_thread.raw_frame.connect(self._store_raw)
        self.cam_thread.status_update.connect(self._log_vision)
        self.cam_thread.start()
        self.badge_cam.setObjectName("BadgeLive")
        self.badge_cam.setText("⬤  CAM: LIVE")
        _refresh_style(self.badge_cam)

    def _upload_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "",
            "Media (*.png *.jpg *.jpeg *.bmp *.mp4 *.avi *.mov *.mkv)"
        )
        if not path:
            return
        if Path(path).suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp"):
            frame = cv2.imread(path)
            if frame is not None:
                self._last_frame = frame.copy()
                self._log_vision(f"📂 Analyzing: {Path(path).name}")
                self.video_frame._idle = False
                self.inf.push(frame)
        else:
            self._stop_cam()
            self.cam_thread = VideoFileThread(path)
            self.cam_thread.frame_ready.connect(self.inf.push)
            self.cam_thread.raw_frame.connect(self._store_raw)
            self.cam_thread.status_update.connect(self._log_vision)
            self.cam_thread.start()
            self.badge_cam.setObjectName("BadgeLive")
            self.badge_cam.setText("⬤  CAM: LIVE")
            _refresh_style(self.badge_cam)

    def _stop_cam(self):
        if self.cam_thread:
            self.cam_thread.stop()
            self.cam_thread.wait(600)
            self.cam_thread = None
        self.video_frame.set_idle()
        self.badge_cam.setObjectName("Badge")
        self.badge_cam.setText("⬤  CAM: OFF")
        _refresh_style(self.badge_cam)
        self._set_status("FEED DISCONNECTED", C["muted"])
        self._log_vision("Optic stream terminated")

    def _store_raw(self, frame: np.ndarray):
        self._last_frame = frame

    def _take_screenshot(self):
        if self._last_frame is None:
            self._log_vision("⚠ No active frame to screenshot")
            return
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"screenshot_{ts}.png"
        cv2.imwrite(path, self._last_frame)
        self._log_vision(f"📷 Screenshot saved → {path}")

    def _on_frame(self, frame: np.ndarray, status: str, color: str, count: int):
        self.video_frame.show_frame(frame)
        self._set_status(status, color)
        self.stat_det.update_value(str(count), color)
        self._fps_count += 1

    def _tick_fps(self):
        self.stat_fps.update_value(str(self._fps_count), C["accent"])
        self._fps_count = 0

    def _set_status(self, text: str, color: str):
        self.status_bar.setText(text)
        self.status_bar.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 2px;
            padding: 10px;
            border: 1px solid {color}55;
            border-radius: 8px;
            background: {color}11;
            color: {color};
        """)

    def _log_vision(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.vision_log.append(
            f'<span style="color:{C["muted"]}">[{ts}]</span> '
            f'<span style="color:{C["text"]}">{msg}</span>'
        )

    # ─────────────────────────────────────────────────────────────────────────
    #  CAR DIRECTIONAL CONTROL
    # ─────────────────────────────────────────────────────────────────────────

    def _on_speed_change(self, val: int):
        self._car_speed = val
        self.speed_val_lbl.setText(str(val))
        hq_ip   = self.hq_ip.text().strip()
        hq_port = int(self.hq_port.text().strip())
        self._send_to(hq_ip, hq_port, f"SPEED:{val}")

    def _send_car_dir(self, cmd: str):
        """Send a directional command to the car only."""
        hq_ip   = self.hq_ip.text().strip()
        hq_port = int(self.hq_port.text().strip())
        self._send_to(hq_ip, hq_port, cmd)

        # ✅ FIX: single braces for a normal dict (was erroneously double-braced)
        badge_map = {
            "FORWARD":  ("BadgeLive", "⬤  CAR: FWD"),
            "BACKWARD": ("BadgeWarn", "⬤  CAR: REV"),
            "LEFT":     ("BadgeLive", "⬤  CAR: LEFT"),
            "RIGHT":    ("BadgeLive", "⬤  CAR: RIGHT"),
            "STOP":     ("Badge",     "⬤  CAR: IDLE"),
        }
        obj, text = badge_map.get(cmd, ("Badge", "⬤  CAR: —"))
        self.badge_car.setObjectName(obj)
        self.badge_car.setText(text)
        _refresh_style(self.badge_car)

    # ─────────────────────────────────────────────────────────────────────────
    #  UDP LOGIC
    # ─────────────────────────────────────────────────────────────────────────

    def _send_to(self, ip: str, port: int, cmd: str):
        try:
            send_sock.sendto(cmd.encode(), (ip, port))
            self._log_udp(
                f'📤 Sent → <b style="color:{C["accent"]}">{cmd}</b> to {ip}:{port}'
            )
        except Exception as e:
            self._log_udp(f'<span style="color:{C["red"]}">❌ Send error: {e}</span>')

    def _send_cmd_both(self, cmd: str):
        # Single port design: all commands go to HQ only.
        # HQ forwards to Car automatically.
        hq_ip   = self.hq_ip.text().strip()
        hq_port = int(self.hq_port.text().strip())
        self._send_to(hq_ip, hq_port, cmd)

        # Clear obstacle alert when user sends any command
        if cmd in ("START", "STOP"):
            self.obstacle_lbl.setText("No obstacle detected")
            self.obstacle_lbl.setStyleSheet(f"""
                font-size: 13px; padding: 10px; border-radius: 8px;
                background: rgba(0,232,122,0.06);
                border: 1px solid {C['border']};
                color: {C['muted']};
            """)
        elif cmd == "REVERSE":
            self.obstacle_lbl.setText("↩  Reversing back to start...")
            self.obstacle_lbl.setStyleSheet(f"""
                font-size: 13px; padding: 10px; border-radius: 8px;
                background: rgba(255,170,51,0.08);
                border: 1px solid {C['amber']};
                color: {C['amber']};
            """)

        # ✅ FIX: single braces for a normal dict (was erroneously double-braced)
        badge_map = {
            "START":   ("BadgeLive", "⬤  CAR: FWD"),
            "REVERSE": ("BadgeWarn", "⬤  CAR: REV"),
            "STOP":    ("Badge",     "⬤  CAR: IDLE"),
        }
        obj, text = badge_map.get(cmd, ("Badge", "⬤  CAR: —"))
        self.badge_car.setObjectName(obj)
        self.badge_car.setText(text)
        _refresh_style(self.badge_car)

    def _send_custom(self):
        cmd = self.custom_edit.text().strip()
        if cmd:
            hq_ip   = self.hq_ip.text().strip()
            hq_port = int(self.hq_port.text().strip())
            self._send_to(hq_ip, hq_port, cmd)
            self.custom_edit.clear()

    def _manual_ping(self):
        """One-shot ping with RTT display."""
        try:
            ip   = self.hq_ip.text().strip()
            port = int(self.hq_port.text().strip())
            t0   = time.perf_counter()
            send_sock.sendto(b"PING", (ip, port))
            rtt  = (time.perf_counter() - t0) * 1000
            self._log_udp(f'🔔 PING sent → {ip}:{port}  ({rtt:.1f} ms)')
        except Exception as e:
            self._log_udp(f'<span style="color:{C["red"]}">❌ Ping error: {e}</span>')

    def _on_udp_received(self, msg: str, lat: float):
        self._log_udp(
            f'📥 <span style="color:{C["green"]}">{msg}</span>'
            f' <span style="color:{C["muted"]}">({lat:.1f}ms)</span>'
        )
        self.badge_udp.setObjectName("BadgeLive")
        self.badge_udp.setText("⬤  UDP: LIVE")
        _refresh_style(self.badge_udp)

        self.badge_ping.setObjectName("BadgeLive")
        self.badge_ping.setText(f"⬤  {lat:.0f} ms")
        _refresh_style(self.badge_ping)

        if msg.startswith("OBSTACLE:"):
            self._handle_obstacle(msg)
            return

        if msg.startswith("ENC:"):
            self._parse_encoder(msg)
            return

        # Sensor telemetry
        try:
            parts = {}
            for item in msg.split(","):
                if ":" in item:
                    k, v = item.split(":", 1)
                    parts[k.strip()] = v.strip()

            mapping = {
                "T":     "TEMP",
                "H":     "HUMIDITY",
                "G":     "GAS",
                "F":     "FLOOD",
                "EQ":    "SEISMIC",
                "STATE": "STATE",
            }
            units = {"T": " °C", "H": " %"}

            is_danger_event = False

            for raw, card_key in mapping.items():
                if raw not in parts:
                    continue
                val = parts[raw] + units.get(raw, "")
                danger = (
                    (raw == "STATE"  and parts[raw] != "SAFE") or
                    (raw == "EQ"     and parts[raw] == "1")    or
                    (raw == "F"      and parts[raw] == "1")    or
                    (raw == "G"      and int(parts.get("G","0")) > 500)
                )
                safe_  = raw == "STATE" and parts[raw] == "SAFE"
                color  = C["red"] if danger else (C["green"] if safe_ else C["accent"])
                self.state_cards[card_key].update_value(val, color)
                if danger:
                    is_danger_event = True

                # Push to sparklines
                if raw in ("T", "H") and card_key in self.sparks:
                    try:
                        self.sparks[card_key].push(float(parts[raw]))
                    except ValueError:
                        pass
                if raw == "G" and "GAS" in self.sparks:
                    try:
                        self.sparks["GAS"].push(float(parts[raw]))
                    except ValueError:
                        pass
                if raw == "F" and "FLOOD" in self.sparks:
                    try:
                        self.sparks["FLOOD"].push(float(parts[raw]))
                    except ValueError:
                        pass
                if raw == "EQ" and "SEISMIC" in self.sparks:
                    try:
                        self.sparks["SEISMIC"].push(float(parts[raw]))
                    except ValueError:
                        pass

            if is_danger_event:
                self._add_alert(f"DANGER → {msg}")

            self._last_sensor_time = time.time()
            if not self._sensor_registered:
                self._sensor_registered = True
                self._ping_timer.stop()

        except Exception as e:
            self._log_udp(f'<span style="color:{C["amber"]}">⚠ Parse error: {e}</span>')

    def _parse_encoder(self, msg: str):
        try:
            parts = {}
            for item in msg[4:].split(","):
                if ":" in item:
                    k, v = item.split(":", 1)
                    parts[k.strip()] = v.strip()

            enc_left  = parts.get("L", "—")
            enc_right = parts.get("R", "—")
            dist_raw  = parts.get("DIST", None)
            dist      = (dist_raw + " cm") if dist_raw else "—"
            car_state = parts.get("STATE", "—")

            color_map  = {"FWD": C["green"], "REV": C["amber"], "IDLE": C["muted"]}
            state_col  = color_map.get(car_state, C["accent"])

            self.enc_cards["ENC LEFT"].update_value(enc_left,  C["accent"])
            self.enc_cards["ENC RIGHT"].update_value(enc_right, C["accent"])
            self.enc_cards["DISTANCE"].update_value(dist,       C["accent"])
            self.enc_cards["CAR STATE"].update_value(car_state, state_col)

            if dist_raw and "DISTANCE" in self.sparks:
                try:
                    self.sparks["DISTANCE"].push(float(dist_raw))
                except ValueError:
                    pass

            badge_text = {"FWD": "⬤  CAR: FWD", "REV": "⬤  CAR: REV", "IDLE": "⬤  CAR: IDLE"}
            badge_obj  = {"FWD": "BadgeLive",    "REV": "BadgeWarn",    "IDLE": "Badge"}
            self.badge_car.setObjectName(badge_obj.get(car_state, "Badge"))
            self.badge_car.setText(badge_text.get(car_state, "⬤  CAR: —"))
            _refresh_style(self.badge_car)

        except Exception as e:
            self._log_udp(f'<span style="color:{C["amber"]}">⚠ Encoder parse error: {e}</span>')

    def _start_ping(self):
        self._ping_hq()
        self._ping_timer.start(4000)

    def _ping_hq(self):
        if self._sensor_registered:
            self._ping_timer.stop()
            return
        try:
            ip   = self.hq_ip.text().strip()
            port = int(self.hq_port.text().strip())
            send_sock.sendto(b"REGISTER", (ip, port))
        except Exception:
            pass

    def _sensor_watchdog(self):
        """If sensor data has not arrived for > 8 s, restart registration pings."""
        if self._sensor_registered and (time.time() - self._last_sensor_time) > 8.0:
            self._sensor_registered = False
            self.badge_udp.setObjectName("BadgeWarn")
            self.badge_udp.setText("⬤  UDP: RECONNECT")
            _refresh_style(self.badge_udp)
            self._ping_hq()
            self._ping_timer.start(4000)

    def _handle_obstacle(self, msg: str):
        """
        Car detected an obstacle — stop, show alert, wait for user to press REVERSE.
        msg format: OBSTACLE:<distance_cm>
        """
        try:
            dist = msg.split(":")[1].strip()
        except Exception:
            dist = "?"

        # Update car state card
        self.enc_cards["CAR STATE"].update_value("BLOCKED", C["red"])

        # Update header badge
        self.badge_car.setObjectName("BadgeWarn")
        self.badge_car.setText("⬤  CAR: BLOCKED")
        _refresh_style(self.badge_car)

        # Show prominent alert in UDP log
        self._log_udp(
            f'<span style="color:{C["red"]}; font-weight:800; font-size:14px;">'
            f'🚨 OBSTACLE DETECTED at {dist} cm — Press REVERSE to go back!</span>'
        )

        # Pop-up style alert in the obstacle label
        self.obstacle_lbl.setText(f"🚨 OBSTACLE at {dist} cm  —  Press REVERSE")
        self.obstacle_lbl.setStyleSheet(f"""
            font-size: 14px; font-weight: 800; padding: 12px;
            border-radius: 8px; letter-spacing: 1px;
            background: rgba(255,51,85,0.12);
            border: 1px solid {C['red']};
            color: {C['red']};
        """)

    def _log_udp(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.udp_log.append(
            f'<span style="color:{C["muted"]}">[{ts}]</span> {msg}'
        )

    # ─────────────────────────────────────────────────────────────────────────
    #  ALERTS
    # ─────────────────────────────────────────────────────────────────────────

    def _add_alert(self, text: str):
        ts   = datetime.now().strftime("%H:%M:%S")
        lbl  = QLabel(f"[{ts}]  {text}")
        lbl.setObjectName("AlertItem")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"""
            background: rgba(255,34,68,0.07);
            border-left: 3px solid {C['red']};
            border-radius: 4px;
            padding: 5px 10px;
            font-family: Consolas;
            font-size: 11px;
            color: {C['text']};
        """)
        # Insert before the trailing stretch
        count = self.alert_layout.count()
        self.alert_layout.insertWidget(count - 1, lbl)
        # Auto-scroll
        QTimer.singleShot(50, lambda: self.alert_scroll.verticalScrollBar().setValue(
            self.alert_scroll.verticalScrollBar().maximum()
        ))

    def _clear_alerts(self):
        while self.alert_layout.count() > 1:
            item = self.alert_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ─────────────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._ping_timer.stop()
        self._watchdog.stop()
        self._stop_cam()
        self.inf.stop()
        event.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("VisionOS Pro v2")
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())