"""Test Tencent iLink Bot API via wechat-link v0.4."""
import time
import wechat_link

def main():
    client = wechat_link.Client()

    # Step 1: Get QR code
    print("[1/4] 获取登录二维码...")
    qr = client.get_bot_qrcode(bot_type=3)
    print(f"      ret={qr.ret} qrcode={qr.qrcode[:20]}...")

    # Show QR in terminal
    client.print_qrcode_terminal(qr.qrcode_img_content)
    print(f"      或用浏览器: {qr.qrcode_img_content}")

    # Step 2: Wait for scan
    print("[2/4] 等待扫码 (60s)...")
    ilink_user_id = None
    bot_token = None
    for i in range(30):
        time.sleep(2)
        status = client.get_qrcode_status(qr.qrcode)
        uid = getattr(status, 'ilink_user_id', None)
        token = getattr(status, 'bot_token', None)
        base = getattr(status, 'baseurl', None)
        bid = getattr(status, 'ilink_bot_id', None)
        print(f"      轮询 {i+1}: user={uid}, bot={bid}, token={'yes' if token else 'no'}", end="\r")
        if uid:
            ilink_user_id = uid
            bot_token = token
            print(f"\n      登录成功! user_id={ilink_user_id} bot_token={'yes' if bot_token else 'no'}")
            break

    if not ilink_user_id:
        print("\n      超时 - 未扫描")
        return

    # Step 3: Get config
    print("[3/4] 获取配置...")
    try:
        if bot_token:
            client.bot_token = bot_token
        config = client.get_config(ilink_user_id=str(ilink_user_id))
        context_token = getattr(config, 'context_token', '') or getattr(config, 'token', '')
        print(f"      token={'yes' if context_token else 'no'}")
    except Exception as e:
        print(f"      config failed: {e}, continuing...")
        context_token = ""

    # Step 4: Listen
    print("[4/4] 监听消息 (Ctrl+C 退出)...")
    cursor = ""
    try:
        while True:
            updates = client.get_updates(cursor=cursor)
            cursor = updates.next_cursor if hasattr(updates, 'next_cursor') else ""
            items = updates.__dict__.get('items', []) or getattr(updates, 'items', [])
            if items:
                for msg in items:
                    sender = getattr(msg, 'sender', '') or msg.__dict__.get('sender', '')
                    text = getattr(msg, 'text', '') or msg.__dict__.get('text', '')
                    print(f"\n      [{sender}]: {text[:200]}")

                    if sender and text:
                        try:
                            token = context_token or getattr(updates, 'context_token', '') or bot_token or ''
                            client.send_text(
                                to_user_id=str(sender),
                                text=f"[菌核] 收到: {text[:100]}",
                                context_token=token,
                            )
                            print(f"      已回复")
                        except Exception as e:
                            print(f"      回复失败: {e}")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n      已退出")

if __name__ == "__main__":
    main()
