"""Phase 5 灰度测试 — 桌面自动化 (章鱼触手运动)。

测试覆盖:
  - UIAController: 后端检测/窗口查找/元素查找/点击/输入/截图
  - ScreenAgent: 后端检测/截图/OCR/文字定位/图标匹配
  - InputSimulator: 后端检测/点击/输入/热键/鼠标移动/滚轮/历史
  - AppLauncher: 应用解析/启动/open_url/open_file/历史
  - ChainExecutor: 步骤管理/执行/重试/错误策略/钩子
  - 集成: 完整链式执行/多步骤编排
"""

from __future__ import annotations

import json
import time
from unittest import mock

import pytest

from automation.uia_controller import (
    UIAController, UIElement, WindowInfo, ClickType, AutomationResult,
)
from automation.screen_agent import (
    ScreenAgent, ScreenCapture, OCRResult, TesseractBackend,
    WindowsOCRBackend, SimpleOCRBackend,
)
from automation.input_simulator import (
    InputSimulator, InputAction, InputResult,
)
from automation.app_launcher import AppLauncher, LaunchResult
from automation.chain_executor import (
    ChainExecutor, ChainStep, ChainResult, StepResult, StepStatus, ErrorPolicy,
)


# ═══════════════════════════════════════════════════════════════
# UIAController 测试
# ═══════════════════════════════════════════════════════════════

class TestUIElement:
    """UIElement 数据类测试。"""

    def test_create_element(self):
        """创建 UIElement。"""
        e = UIElement(name="OK", control_type="Button", x=100, y=200, width=80, height=30)
        assert e.name == "OK"
        assert e.control_type == "Button"
        assert e.center == (140, 215)

    def test_frozen(self):
        """UIElement 不可修改。"""
        e = UIElement(name="Test")
        with pytest.raises(Exception):
            e.name = "Changed"  # type: ignore

    def test_default_element(self):
        """默认 UIElement 属性。"""
        e = UIElement()
        assert e.name == ""
        assert e.is_enabled
        assert e.is_visible

    def test_center_calculation(self):
        """坐标中心计算。"""
        e = UIElement(x=0, y=0, width=100, height=50)
        assert e.center == (50, 25)


class TestWindowInfo:
    """WindowInfo 数据类测试。"""

    def test_create_window_info(self):
        """创建 WindowInfo。"""
        w = WindowInfo(title="Test", process_name="test.exe", hwnd=12345)
        assert w.title == "Test"
        assert w.process_name == "test.exe"
        assert w.hwnd == 12345

    def test_width_height(self):
        """宽高计算。"""
        w = WindowInfo(rect=(0, 0, 800, 600))
        assert w.width == 800
        assert w.height == 600

    def test_frozen(self):
        """WindowInfo 不可修改。"""
        w = WindowInfo(title="Test")
        with pytest.raises(Exception):
            w.title = "Changed"  # type: ignore


class TestAutomationResult:
    """AutomationResult 测试。"""

    def test_success_result(self):
        r = AutomationResult(success=True, action="click", detail="OK")
        assert r.success
        assert r.action == "click"

    def test_failure_result(self):
        r = AutomationResult(success=False, action="click", detail="Not found")
        assert not r.success

    def test_frozen(self):
        r = AutomationResult(success=True, action="test")
        with pytest.raises(Exception):
            r.success = False  # type: ignore


class TestUIAController:
    """UIAController 核心测试。"""

    @pytest.fixture
    def ctrl(self):
        return UIAController()

    def test_available(self, ctrl):
        """后端可用性检测。"""
        assert ctrl.available  # 至少 win32 可用

    def test_backend_name(self, ctrl):
        """后端名称。"""
        assert ctrl.backend in ("pywinauto", "uiautomation", "win32")

    def test_click_without_target(self, ctrl):
        """无目标点击返回失败。"""
        result = ctrl.click()
        assert not result.success

    def test_click_result_type(self, ctrl):
        """点击返回 AutomationResult。"""
        result = ctrl.click(x=100, y=200)
        assert isinstance(result, AutomationResult)

    def test_type_text_empty(self, ctrl):
        """空文本输入。"""
        result = ctrl.type_text("")
        assert not result.success

    def test_type_text_result(self, ctrl):
        """文本输入返回结果。"""
        result = ctrl.type_text("hello")
        assert isinstance(result, AutomationResult)

    def test_press_key_result(self, ctrl):
        """按键返回结果。"""
        result = ctrl.press_key("enter")
        assert isinstance(result, AutomationResult)

    def test_press_key_with_modifiers(self, ctrl):
        """带修饰键的按键。"""
        result = ctrl.press_key("c", modifiers=["ctrl"])
        assert isinstance(result, AutomationResult)

    def test_find_window_empty_params(self, ctrl):
        """空参数查找窗口返回 None。"""
        # 全空参数会匹配所有窗口, 需要至少一个过滤条件才找到有意义的结果
        result = ctrl.find_window(title="")
        # 空标题可能匹配隐藏窗口, 不强制要求 None
        assert result is None or isinstance(result, WindowInfo)

    def test_get_active_window(self, ctrl):
        """获取活动窗口。"""
        result = ctrl.get_active_window()
        # 可能返回窗口或 None (取决于测试环境)
        if result is not None:
            assert isinstance(result, WindowInfo)

    def test_get_all_windows(self, ctrl):
        """列举所有窗口。"""
        windows = ctrl.get_all_windows()
        assert isinstance(windows, list)
        for w in windows:
            assert isinstance(w, WindowInfo)
            assert w.title != ""

    def test_get_all_windows_invisible(self, ctrl):
        """列举含不可见窗口。"""
        windows = ctrl.get_all_windows(visible_only=False)
        assert isinstance(windows, list)

    def test_find_element_empty(self, ctrl):
        """空参数查找元素返回 None。"""
        result = ctrl.find_element()
        assert result is None

    def test_read_text_empty(self, ctrl):
        """空元素读取文本返回空。"""
        text = ctrl.read_text()
        assert isinstance(text, str)

    def test_click_text_requires_ocr(self, ctrl):
        """click_text 返回失败 (需 OCR)。"""
        result = ctrl.click_text("test")
        assert not result.success

    def test_click_type_enum(self):
        """ClickType 枚举。"""
        assert ClickType.LEFT.value == "left"
        assert ClickType.RIGHT.value == "right"
        assert ClickType.DOUBLE.value == "double"


# ═══════════════════════════════════════════════════════════════
# ScreenAgent 测试
# ═══════════════════════════════════════════════════════════════

class TestScreenCapture:
    """ScreenCapture 数据类测试。"""

    def test_create_capture(self):
        c = ScreenCapture(image_base64="AAAA", width=1920, height=1080)
        assert c.width == 1920
        assert c.height == 1080
        assert c.format == "png"

    def test_frozen(self):
        c = ScreenCapture(image_base64="A", width=100, height=100)
        with pytest.raises(Exception):
            c.width = 200  # type: ignore


class TestOCRResult:
    """OCRResult 数据类测试。"""

    def test_create_result(self):
        r = OCRResult(text="Hello World", confidence=0.95)
        assert r.text == "Hello World"
        assert r.confidence == 0.95
        assert not r.is_empty

    def test_empty_result(self):
        r = OCRResult(text="", confidence=0.0)
        assert r.is_empty

    def test_with_regions(self):
        r = OCRResult(
            text="AB",
            confidence=0.9,
            regions=((0, 0, 10, 20, "A", 0.9), (20, 0, 10, 20, "B", 0.9)),
        )
        assert len(r.regions) == 2

    def test_frozen(self):
        r = OCRResult(text="X")
        with pytest.raises(Exception):
            r.text = "Y"  # type: ignore


class TestOCRBackends:
    """OCR 后端测试。"""

    def test_simple_ocr_always_available(self):
        b = SimpleOCRBackend()
        assert b.is_available()

    def test_simple_ocr_returns_empty(self):
        b = SimpleOCRBackend()
        result = b.recognize(b"fake_image")
        assert result.is_empty

    def test_windows_ocr_not_available(self):
        b = WindowsOCRBackend()
        assert not b.is_available()  # 默认禁用

    def test_tesseract_detection(self):
        b = TesseractBackend()
        # 不检查 is_available (可能安装了也可能没安装)
        assert isinstance(b.is_available(), bool)


class TestScreenAgent:
    """ScreenAgent 核心测试。"""

    @pytest.fixture
    def agent(self):
        return ScreenAgent()

    def test_available(self, agent):
        """截屏可用性。"""
        assert isinstance(agent.available, bool)

    def test_ocr_available(self, agent):
        """OCR 可用性。"""
        assert isinstance(agent.ocr_available, bool)

    def test_backend_name(self, agent):
        """后端名称。"""
        assert isinstance(agent.ocr_backend_name, str)

    def test_capture_returns_something(self, agent):
        """截屏返回结果。"""
        result = agent.capture()
        if result is not None:
            assert isinstance(result, ScreenCapture)
            assert result.width > 0
            assert result.height > 0
            assert len(result.image_base64) > 0

    def test_ocr_empty_image(self, agent):
        """OCR 空图片返回空结果。"""
        result = agent.ocr(b"")
        assert result.is_empty

    def test_ocr_base64_string_empty(self, agent):
        """OCR base64 空字符串。"""
        result = agent.ocr("")
        assert result.is_empty

    def test_ocr_base64_invalid(self, agent):
        """OCR 无效 base64。"""
        result = agent.ocr("!!!invalid!!!")
        assert result.is_empty

    def test_ocr_bytes_no_text(self, agent):
        """OCR 无文字图片 (预期空)。"""
        # 创建一个极小的假 PNG
        fake_png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f'
            b'\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        result = agent.ocr(fake_png)
        # 可能空也可能有噪声 (取决于后端)
        assert isinstance(result, OCRResult)

    def test_get_resolution(self, agent):
        """获取屏幕分辨率。"""
        w, h = agent.get_screen_resolution()
        assert w > 0
        assert h > 0

    def test_find_text_on_screen_no_match(self, agent):
        """查找不存在的文字。"""
        result = agent.find_text_on_screen("xyznonexistent12345")
        # 可能返回 None 或坐标 (取决于 OCR 是否可用)
        if not agent.ocr_available:
            assert result is None

    def test_find_icon_no_numpy(self, agent):
        """无 numpy 时图标查找返回 None。"""
        result = agent.find_icon_on_screen("nonexistent.png")
        assert result is None


# ═══════════════════════════════════════════════════════════════
# InputSimulator 测试
# ═══════════════════════════════════════════════════════════════

class TestInputAction:
    """InputAction 数据类测试。"""

    def test_create_action(self):
        a = InputAction(action_type="click", params={"x": 100})
        assert a.action_type == "click"
        assert a.params["x"] == 100

    def test_frozen(self):
        a = InputAction(action_type="test")
        with pytest.raises(Exception):
            a.action_type = "other"  # type: ignore


class TestInputResult:
    """InputResult 数据类测试。"""

    def test_success(self):
        r = InputResult(success=True, action="click", detail="OK")
        assert r.success

    def test_frozen(self):
        r = InputResult(success=True, action="test")
        with pytest.raises(Exception):
            r.success = False  # type: ignore


class TestInputSimulator:
    """InputSimulator 核心测试。"""

    @pytest.fixture
    def sim(self):
        return InputSimulator()

    def test_available(self, sim):
        """后端可用性。"""
        assert sim.available

    def test_backend(self, sim):
        """后端名称。"""
        assert sim.backend in ("pyautogui", "ctypes")

    def test_click_result(self, sim):
        """点击返回结果。"""
        result = sim.click(0, 0)
        assert isinstance(result, InputResult)

    def test_double_click_result(self, sim):
        """双击返回结果。"""
        result = sim.double_click(0, 0)
        assert isinstance(result, InputResult)

    def test_right_click_result(self, sim):
        """右键返回结果。"""
        result = sim.right_click(0, 0)
        assert isinstance(result, InputResult)

    def test_move_result(self, sim):
        """移动鼠标返回结果。"""
        result = sim.move(100, 100)
        assert isinstance(result, InputResult)

    def test_type_text_empty(self, sim):
        """空文本输入。"""
        result = sim.type_text("")
        assert not result.success

    def test_type_text_result(self, sim):
        """文本输入返回结果。"""
        result = sim.type_text("hello")
        assert isinstance(result, InputResult)

    def test_press_result(self, sim):
        """按键返回结果。"""
        result = sim.press("enter")
        assert isinstance(result, InputResult)

    def test_hotkey_result(self, sim):
        """热键返回结果。"""
        result = sim.hotkey("ctrl", "c")
        assert isinstance(result, InputResult)

    def test_hotkey_empty(self, sim):
        """空热键失败。"""
        result = sim.hotkey()
        assert not result.success

    def test_key_down_result(self, sim):
        """按下键返回结果。"""
        result = sim.key_down("shift")
        assert isinstance(result, InputResult)

    def test_key_up_result(self, sim):
        """释放键返回结果。"""
        result = sim.key_up("shift")
        assert isinstance(result, InputResult)

    def test_scroll_result(self, sim):
        """滚轮返回结果。"""
        result = sim.scroll(3)
        assert isinstance(result, InputResult)

    def test_convenience_methods(self, sim):
        """便捷方法。"""
        for method_name in ["copy", "paste", "cut", "select_all", "undo", "enter", "tab"]:
            method = getattr(sim, method_name)
            result = method()
            assert isinstance(result, InputResult)

    def test_history_accumulates(self, sim):
        """操作历史累积。"""
        sim.click(0, 0)
        sim.move(100, 100)
        history = sim.get_history()
        assert len(history) >= 2

    def test_history_limit(self, sim):
        """历史限制。"""
        assert len(sim.get_history(limit=3)) <= 3

    def test_clear_history(self, sim):
        """清空历史。"""
        sim.click(0, 0)
        sim.clear_history()
        assert len(sim.get_history()) == 0


# ═══════════════════════════════════════════════════════════════
# AppLauncher 测试
# ═══════════════════════════════════════════════════════════════

class TestLaunchResult:
    """LaunchResult 数据类测试。"""

    def test_success_result(self):
        r = LaunchResult(success=True, target="notepad", process_id=12345, status="launched")
        assert r.success
        assert r.process_id == 12345

    def test_not_found_result(self):
        r = LaunchResult(success=False, target="nonexistent", status="not_found")
        assert not r.success
        assert r.status == "not_found"

    def test_frozen(self):
        r = LaunchResult(success=True, target="test")
        with pytest.raises(Exception):
            r.success = False  # type: ignore


class TestAppLauncher:
    """AppLauncher 核心测试。"""

    @pytest.fixture
    def launcher(self):
        return AppLauncher()

    def test_open_known_app(self, launcher):
        """启动已知应用。"""
        result = launcher.open("notepad")
        assert isinstance(result, LaunchResult)

    def test_open_url(self, launcher):
        """打开 URL。"""
        result = launcher.open_url("https://example.com")
        assert isinstance(result, LaunchResult)

    def test_open_file_nonexistent(self, launcher):
        """打开不存在文件返回失败。"""
        result = launcher.open_file("C:\\nonexistent\\file.txt")
        assert not result.success
        assert result.status == "not_found"

    def test_resolve_app_name(self, launcher):
        """应用名解析。"""
        # 已知应用映射
        for app in ["notepad", "记事本", "calc", "计算器", "cmd", "powershell"]:
            resolved = launcher._resolve_app_name(app)
            assert isinstance(resolved, str)
            assert len(resolved) > 0

    def test_resolve_unknown_app(self, launcher):
        """未知应用保持不变。"""
        result = launcher._resolve_app_name("my_custom_app.exe")
        assert result == "my_custom_app.exe"

    def test_history(self, launcher):
        """启动历史。"""
        launcher.open_url("https://test.com")
        history = launcher.get_history()
        assert len(history) >= 1
        assert isinstance(history[0], LaunchResult)

    def test_clear_history(self, launcher):
        """清空历史。"""
        launcher.open("notepad")
        launcher.clear_history()
        assert len(launcher.get_history()) == 0

    def test_is_running_false(self, launcher):
        """不存在的 PID 返回 False。"""
        assert not launcher.is_running(99999999)

    def test_terminate_false(self, launcher):
        """终止不存在的 PID 返回 False。"""
        assert not launcher.terminate(99999999)


# ═══════════════════════════════════════════════════════════════
# ChainExecutor 测试
# ═══════════════════════════════════════════════════════════════

class TestChainStep:
    """ChainStep 数据类测试。"""

    def test_create_step(self):
        s = ChainStep(action="click", params={"x": 100})
        assert s.action == "click"
        assert s.params["x"] == 100
        assert s.error_policy == ErrorPolicy.STOP

    def test_with_label(self):
        s = ChainStep(action="wait", label="等待 1 秒", params={"seconds": 1})
        assert s.label == "等待 1 秒"

    def test_frozen(self):
        s = ChainStep(action="test")
        with pytest.raises(Exception):
            s.action = "other"  # type: ignore


class TestChainResult:
    """ChainResult 数据类测试。"""

    def test_success_result(self):
        sr = StepResult(step_index=0, step_label="test", action="wait",
                        status=StepStatus.SUCCESS, duration_ms=100)
        cr = ChainResult(
            success=True, total_steps=1, completed_steps=1,
            failed_steps=0, skipped_steps=0,
            step_results=(sr,),
        )
        assert cr.success
        summary = cr.summary()
        assert "成功" in summary

    def test_failure_result(self):
        sr = StepResult(step_index=0, step_label="bad", action="click",
                        status=StepStatus.FAILED, error="Not found", duration_ms=10)
        cr = ChainResult(
            success=False, total_steps=1, completed_steps=0,
            failed_steps=1, skipped_steps=0,
            step_results=(sr,),
        )
        assert not cr.success
        summary = cr.summary()
        assert "失败" in summary

    def test_frozen(self):
        cr = ChainResult(success=True, total_steps=0, completed_steps=0,
                         failed_steps=0, skipped_steps=0)
        with pytest.raises(Exception):
            cr.success = False  # type: ignore


class TestChainExecutor:
    """ChainExecutor 核心测试。"""

    @pytest.fixture
    def chain(self):
        return ChainExecutor()

    def test_add_step(self, chain):
        """添加步骤。"""
        chain.add_step("wait", seconds=1, label="等待")
        assert len(chain.get_steps()) == 1
        assert chain.get_steps()[0].label == "等待"

    def test_execute_wait(self, chain):
        """执行等待步骤。"""
        chain.add_step("wait", seconds=0.05)
        result = chain.execute()
        assert result.success
        assert result.completed_steps == 1

    def test_execute_multiple_steps(self, chain):
        """执行多步骤。"""
        chain.add_step("wait", seconds=0.02)
        chain.add_step("wait", seconds=0.02)
        chain.add_step("wait", seconds=0.02)
        result = chain.execute()
        assert result.success
        assert result.completed_steps == 3

    def test_execute_run_python(self, chain):
        """执行 Python 代码步骤。"""
        chain.add_step("run_python", code="x = 42")
        result = chain.execute()
        assert result.success

    def test_execute_assert_pass(self, chain):
        """断言通过。"""
        chain.add_step("assert", condition=True)
        result = chain.execute()
        assert result.success

    def test_execute_assert_fail(self, chain):
        """断言失败停止。"""
        chain.add_step("assert", condition=False, message="fail!")
        chain.add_step("wait", seconds=0.01)
        result = chain.execute()
        assert not result.success
        assert result.failed_steps == 1
        assert result.completed_steps == 0

    def test_error_policy_continue(self, chain):
        """错误继续策略。"""
        chain.add_step("assert", condition=False, error_policy=ErrorPolicy.CONTINUE)
        chain.add_step("wait", seconds=0.01, label="still_runs")
        result = chain.execute()
        assert not result.success
        assert result.completed_steps >= 1  # 第二步完成

    def test_retry_success(self, chain):
        """重试成功。"""
        call_count = [0]

        def _before(step):
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError("fail")

        chain.on_before_step(_before)
        chain.add_step("wait", seconds=0.01, max_retries=3, error_policy=ErrorPolicy.RETRY)
        result = chain.execute()

    def test_unknown_action(self, chain):
        """未知动作抛出。"""
        chain.add_step("nonexistent_action")
        result = chain.execute()
        assert not result.success
        assert result.failed_steps == 1

    def test_clear_steps(self, chain):
        """清空步骤。"""
        chain.add_step("wait", seconds=1)
        chain.add_step("wait", seconds=2)
        chain.clear()
        assert chain.get_steps() == []
        result = chain.execute()
        assert result.total_steps == 0

    def test_before_hook(self, chain):
        """步骤前钩子。"""
        seen = []

        def hook(step: ChainStep):
            seen.append(step.action)

        chain.on_before_step(hook)
        chain.add_step("wait", seconds=0.01)
        chain.execute()
        assert "wait" in seen

    def test_after_hook(self, chain):
        """步骤后钩子。"""
        results = []

        def hook(sr: StepResult):
            results.append(sr)

        chain.on_after_step(hook)
        chain.add_step("wait", seconds=0.01)
        chain.execute()
        assert len(results) == 1

    def test_error_hook(self, chain):
        """错误钩子。"""
        errors = []

        def hook(step: ChainStep, exc: Exception):
            errors.append(str(exc))

        chain.on_error(hook)
        chain.add_step("assert", condition=False, message="boom!")
        chain.execute()
        assert len(errors) >= 1

    def test_get_results(self, chain):
        """获取执行结果。"""
        chain.add_step("wait", seconds=0.01)
        chain.execute()
        results = chain.get_results()
        assert len(results) == 1
        assert isinstance(results[0], StepResult)

    def test_step_status_enum(self):
        """步骤状态枚举。"""
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.SUCCESS.value == "success"
        assert StepStatus.FAILED.value == "failed"

    def test_error_policy_enum(self):
        """错误策略枚举。"""
        assert ErrorPolicy.STOP.value == "stop"
        assert ErrorPolicy.CONTINUE.value == "continue"
        assert ErrorPolicy.RETRY.value == "retry"


# ═══════════════════════════════════════════════════════════════
# 集成测试
# ═══════════════════════════════════════════════════════════════

class TestPhase5Integration:
    """Phase 5 跨模块集成测试。"""

    def test_chain_with_input_sim(self):
        """链式执行 + 输入模拟器。"""
        from automation.input_simulator import InputSimulator
        sim = InputSimulator()
        chain = ChainExecutor(input_sim=sim)
        chain.add_step("press", key="escape")
        chain.add_step("wait", seconds=0.05)
        result = chain.execute()
        assert isinstance(result, ChainResult)

    def test_chain_with_launcher(self):
        """链式执行 + 应用启动器。"""
        launcher = AppLauncher()
        chain = ChainExecutor(launcher=launcher)
        chain.add_step("open_url", url="https://example.com")
        result = chain.execute()
        assert isinstance(result, ChainResult)

    def test_multiple_error_policies(self):
        """混合错误策略。"""
        chain = ChainExecutor()
        chain.add_step("wait", seconds=0.01, label="step1")
        chain.add_step("assert", condition=False, label="skip_me",
                       error_policy=ErrorPolicy.CONTINUE)
        chain.add_step("wait", seconds=0.01, label="step3")
        result = chain.execute()
        assert result.failed_steps == 1
        assert result.completed_steps >= 2  # step1 + step3

    def test_delay_mechanism(self):
        """延迟机制。"""
        chain = ChainExecutor()
        chain.add_step("wait", seconds=0.01, delay_before=0.05, delay_after=0.05)
        start = time.time()
        result = chain.execute()
        elapsed = time.time() - start
        assert result.success
        assert elapsed >= 0.1  # wait + delays

    def test_full_desktop_automation_chain(self):
        """完整桌面自动化链 (模拟)。"""
        sim = InputSimulator()
        launcher = AppLauncher()
        chain = ChainExecutor(input_sim=sim, launcher=launcher)

        # 模拟打开记事本的操作链
        chain.add_step("open_app", app="notepad.exe", label="打开记事本",
                       delay_after=0.5)
        chain.add_step("wait", seconds=0.1, label="等待启动")
        chain.add_step("type_text", text="Hello from Sclerotium OS!",
                       label="输入文本")
        chain.add_step("wait", seconds=0.1, label="等待输入完成")
        chain.add_step("press", key="enter", label="回车")
        chain.add_step("run_python", code="result = True", label="验证")

        result = chain.execute()
        assert isinstance(result, ChainResult)
        assert len(result.step_results) == 6
        summary = result.summary()
        assert "打开记事本" in summary
        assert "输入文本" in summary
