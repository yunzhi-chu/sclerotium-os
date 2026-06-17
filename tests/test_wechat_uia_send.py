"""Test: send a WeChat message via UIA."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platforms.wechat_uia import WeChatUIA

wx = WeChatUIA()
if not wx.connect():
    print("[FAIL] Connect failed")
    sys.exit(1)

print("[OK] Connected")

# Test 1: send to filehelper
print("[TEST] Sending to 文件传输助手...")
ok = wx.send_text("文件传输助手", "菌核 UIA 测试消息 - " + __import__('time').strftime("%H:%M:%S"))
print(f"  Result: {'OK' if ok else 'FAIL'}")

wx.cleanup()
print("[DONE] Check your WeChat 文件传输助手 for the test message")
