"""Sclerotium OS — 桌面自动化 (章鱼触手运动控制)。

多通道桌面操控:
  - UIA (Windows Accessibility) → 结构化元素访问
  - OCR + Vision → 截图分析
  - Input simulation → 键盘/鼠标控制
  - App launcher → 应用启动
  - Chain executor → 多步骤编排

五层操作通道 (从精确到粗糙):
  1. UIA 结构化元素 (最精确, 最可靠)
  2. OCR 文字定位 (中等, 视觉回退)
  3. 图标模板匹配 (低精度, 视觉回退)
  4. 坐标点击 (精确但脆弱)
  5. 快捷键模拟 (最粗糙, 最后手段)
"""

from automation.uia_controller import (
    UIAController, UIElement, WindowInfo, ClickType, AutomationResult,
)
from automation.screen_agent import (
    ScreenAgent, ScreenCapture, OCRResult, OCRBackend,
)
from automation.input_simulator import (
    InputSimulator, InputAction, InputResult,
)
from automation.app_launcher import AppLauncher, LaunchResult
from automation.chain_executor import (
    ChainExecutor, ChainStep, ChainResult, StepResult, StepStatus, ErrorPolicy,
)

__all__ = [
    "UIAController", "UIElement", "WindowInfo", "ClickType", "AutomationResult",
    "ScreenAgent", "ScreenCapture", "OCRResult", "OCRBackend",
    "InputSimulator", "InputAction", "InputResult",
    "AppLauncher", "LaunchResult",
    "ChainExecutor", "ChainStep", "ChainResult", "StepResult", "StepStatus", "ErrorPolicy",
]
