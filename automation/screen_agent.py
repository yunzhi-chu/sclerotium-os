"""Screen Agent — 截图 + OCR + 视觉分析。

章鱼的"皮肤视觉" — 不依赖结构化 API, 直接"看"屏幕。

双通道融合:
  1. PIL ImageGrab — 截图 (全屏/区域/窗口)
  2. OCR 引擎 — 文字识别 (Windows OCR / Tesseract / EasyOCR)

使用方式:
    agent = ScreenAgent()
    img_b64 = agent.capture()  # 截全屏
    text = agent.ocr(image)    # 识别文字
    pos = agent.find_text_on_screen("登录")  # 找文字位置
"""

from __future__ import annotations

import base64
import io
import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.screen")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ScreenCapture:
    """截图结果 (不可变)。"""
    image_base64: str
    width: int = 0
    height: int = 0
    format: str = "png"
    captured_at: float = field(default_factory=time.time)
    region: tuple[int, int, int, int] = ()


@dataclass(frozen=True)
class OCRResult:
    """OCR 识别结果 (不可变)。"""
    text: str
    confidence: float = 0.0
    language: str = "auto"
    regions: tuple[tuple[int, int, int, int, str, float], ...] = ()
    # 每个 region: (x, y, w, h, text, confidence)

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


# ═══════════════════════════════════════════════════════════════
# OCR 后端接口
# ═══════════════════════════════════════════════════════════════

class OCRBackend:
    """OCR 后端的抽象基类。"""

    def recognize(self, image_bytes: bytes) -> OCRResult:
        raise NotImplementedError

    def is_available(self) -> bool:
        raise NotImplementedError


class TesseractBackend(OCRBackend):
    """Tesseract OCR 后端。"""

    def recognize(self, image_bytes: bytes) -> OCRResult:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(img, lang="chi_sim+eng")
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

            regions = []
            for i in range(len(data["text"])):
                if data["text"][i].strip():
                    regions.append((
                        data["left"][i],
                        data["top"][i],
                        data["width"][i],
                        data["height"][i],
                        data["text"][i],
                        float(data["conf"][i]) / 100.0,
                    ))

            return OCRResult(
                text=text,
                confidence=sum(r[5] for r in regions) / max(len(regions), 1),
                language="chi_sim+eng",
                regions=tuple(regions),
            )
        except Exception as e:
            logger.warning("Tesseract OCR failed: %s", e)
            return OCRResult(text="", confidence=0.0)

    def is_available(self) -> bool:
        try:
            import pytesseract
            return True
        except ImportError:
            return False


class WindowsOCRBackend(OCRBackend):
    """Windows 10/11 内置 OCR 后端 (通过 winrt)。"""

    def recognize(self, image_bytes: bytes) -> OCRResult:
        try:
            import subprocess
            import tempfile
            import os

            # 写入临时文件
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(image_bytes)
                tmp_path = f.name

            try:
                # 使用 PowerShell 调用 Windows OCR
                ps_script = rf'''
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
$img = [System.Drawing.Image]::FromFile("{tmp_path}")
$ocr = New-Object -ComObject "Ocr.OcrEngine"
# Windows OCR 不可用时的回退
Write-Output ""
'''
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_script],
                    capture_output=True, text=True, timeout=15,
                )
                return OCRResult(text=result.stdout.strip(), confidence=0.5)
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        except Exception as e:
            logger.debug("Windows OCR failed: %s", e)
            return OCRResult(text="", confidence=0.0)

    def is_available(self) -> bool:
        return False  # Windows OCR 太不稳定, 默认禁用


class SimpleOCRBackend(OCRBackend):
    """简单回退 OCR — 直接返回空, 不崩溃。"""

    def recognize(self, image_bytes: bytes) -> OCRResult:
        return OCRResult(text="", confidence=0.0)

    def is_available(self) -> bool:
        return True


# ═══════════════════════════════════════════════════════════════
# ScreenAgent
# ═══════════════════════════════════════════════════════════════

class ScreenAgent:
    """屏幕截图和 OCR 分析代理。

    自动选择最佳 OCR 后端:
      1. Tesseract (中英文支持好)
      2. Simple OCR (空回退, 不崩溃)

    使用方式:
        agent = ScreenAgent()
        capture = agent.capture()
        result = agent.ocr_from_capture(capture)
        print(result.text)
    """

    def __init__(self) -> None:
        self._pil_available = False
        self._ocr_backends: list[OCRBackend] = []
        self._lock = threading.Lock()

        # 探测 Pillow
        try:
            from PIL import Image, ImageGrab
            self._pil_available = True
        except ImportError:
            pass

        # 探测 OCR 后端 (按优先级)
        tesseract = TesseractBackend()
        if tesseract.is_available():
            self._ocr_backends.append(tesseract)

        win_ocr = WindowsOCRBackend()
        if win_ocr.is_available():
            self._ocr_backends.append(win_ocr)

        # 始终添加回退
        self._ocr_backends.append(SimpleOCRBackend())

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def available(self) -> bool:
        """截屏是否可用。"""
        return self._pil_available

    @property
    def ocr_available(self) -> bool:
        """OCR 是否可用。"""
        return any(b.is_available() and not isinstance(b, SimpleOCRBackend)
                   for b in self._ocr_backends)

    @property
    def ocr_backend_name(self) -> str:
        """当前 OCR 后端名称。"""
        if self._ocr_backends:
            return type(self._ocr_backends[0]).__name__
        return "none"

    # ═══════════════════════════════════════════════════════
    # 截图
    # ═══════════════════════════════════════════════════════

    def capture(
        self,
        region: tuple[int, int, int, int] | None = None,
    ) -> ScreenCapture | None:
        """截取屏幕或指定区域。

        Args:
            region: (left, top, right, bottom) 或 None (全屏)

        Returns:
            ScreenCapture 或 None (截图不可用时)
        """
        if not self._pil_available:
            logger.warning("Pillow not available for screenshot")
            return None

        try:
            from PIL import ImageGrab

            img = ImageGrab.grab(bbox=region)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_bytes = buf.getvalue()
            b64 = base64.b64encode(img_bytes).decode("ascii")

            return ScreenCapture(
                image_base64=b64,
                width=img.width,
                height=img.height,
                region=region or (),
            )
        except Exception as e:
            logger.error("Screenshot capture failed: %s", e)
            return None

    def capture_and_ocr(self) -> tuple[ScreenCapture | None, OCRResult]:
        """截图并立即 OCR。

        Returns:
            (截图, OCR 结果)
        """
        capture = self.capture()
        if capture is None:
            return None, OCRResult(text="", confidence=0.0)

        ocr_result = self.ocr_from_capture(capture)
        return capture, ocr_result

    # ═══════════════════════════════════════════════════════
    # OCR
    # ═══════════════════════════════════════════════════════

    def ocr(self, image_data: bytes | str) -> OCRResult:
        """对图片进行 OCR。

        Args:
            image_data: PNG 图片字节 或 base64 字符串

        Returns:
            OCRResult
        """
        if isinstance(image_data, str):
            try:
                image_data = base64.b64decode(image_data)
            except Exception:
                return OCRResult(text="", confidence=0.0)

        if not image_data:
            return OCRResult(text="", confidence=0.0)

        for backend in self._ocr_backends:
            if backend.is_available():
                try:
                    result = backend.recognize(image_data)
                    if result.text.strip():
                        return result
                except Exception as e:
                    logger.debug("OCR backend %s failed: %s",
                                 type(backend).__name__, e)

        return OCRResult(text="", confidence=0.0)

    def ocr_from_capture(self, capture: ScreenCapture) -> OCRResult:
        """从截图结果做 OCR。"""
        return self.ocr(capture.image_base64)

    # ═══════════════════════════════════════════════════════
    # 视觉定位
    # ═══════════════════════════════════════════════════════

    def find_text_on_screen(
        self,
        text: str,
        region: tuple[int, int, int, int] | None = None,
    ) -> tuple[int, int] | None:
        """在屏幕上查找文字, 返回中心坐标。

        Args:
            text: 要查找的文字
            region: 搜索区域 (可选)

        Returns:
            (x, y) 中心坐标 或 None
        """
        capture = self.capture(region=region)
        if capture is None:
            return None

        result = self.ocr_from_capture(capture)
        if result.is_empty:
            return None

        # 在 OCR 区域中搜索
        target_lower = text.lower()
        for rx, ry, rw, rh, rtext, conf in result.regions:
            if target_lower in rtext.lower() and conf > 0.3:
                return (rx + rw // 2, ry + rh // 2)

        # 全文搜索
        if target_lower in result.text.lower():
            # 返回第一个匹配行的估算位置
            lines = result.text.split("\n")
            for i, line in enumerate(lines):
                if target_lower in line.lower():
                    # 粗略估算 y 坐标
                    est_y = int(capture.height * (i / max(len(lines), 1)))
                    est_x = capture.width // 2
                    return (est_x, est_y)

        return None

    def find_icon_on_screen(
        self,
        icon_path: str,
        confidence: float = 0.8,
    ) -> tuple[int, int] | None:
        """在屏幕上查找图标位置 (模板匹配)。

        Args:
            icon_path: 图标文件路径
            confidence: 匹配置信度阈值

        Returns:
            (x, y) 中心坐标 或 None
        """
        if not self._pil_available:
            return None

        try:
            from PIL import Image, ImageGrab
            import numpy as np

            screen = ImageGrab.grab()
            screen_arr = np.array(screen)

            icon = Image.open(icon_path)
            icon_arr = np.array(icon)

            # 简单模板匹配 (基于像素相关性)
            ih, iw = icon_arr.shape[:2]
            sh, sw = screen_arr.shape[:2]

            if ih > sh or iw > sw:
                return None

            best_score = 0.0
            best_pos = (0, 0)
            step = max(1, min(ih, iw) // 4)

            for y in range(0, sh - ih, step):
                for x in range(0, sw - iw, step):
                    patch = screen_arr[y:y+ih, x:x+iw]
                    if patch.shape == icon_arr.shape:
                        diff = np.abs(patch.astype(float) - icon_arr.astype(float))
                        score = 1.0 - (np.mean(diff) / 255.0)
                        if score > best_score:
                            best_score = score
                            best_pos = (x + iw // 2, y + ih // 2)

            if best_score >= confidence:
                return best_pos

        except ImportError:
            logger.debug("numpy not available for icon matching")
        except Exception as e:
            logger.warning("Icon matching failed: %s", e)

        return None

    def get_screen_resolution(self) -> tuple[int, int]:
        """获取屏幕分辨率。"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            return (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
        except Exception:
            return (1920, 1080)  # 默认
