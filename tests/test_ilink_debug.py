"""Debug iLink message flow step by step."""
import time, wechat_link

c = wechat_link.Client()
print("[1] Get QR + login...")
qr = c.get_bot_qrcode(bot_type=3)
c.print_qrcode_terminal(qr.qrcode_img_content)

# Wait for scan
uid = None
for i in range(30):
    time.sleep(2)
    s = c.get_qrcode_status(qr.qrcode)
    uid = getattr(s, 'ilink_user_id', None)
    print(f"   poll {i+1}: user={uid}, token={'yes' if getattr(s,'bot_token',None) else 'no'}", end="\r")
    if uid:
        c.bot_token = getattr(s, 'bot_token', '')
        print(f"\n   logged in: {uid}")
        break

if not uid:
    print("FAIL: no login")
    exit()

# Step 2: Get config
print("\n[2] Get config...")
cfg = c.get_config(ilink_user_id=str(uid))
print(f"   Config: {cfg.__dict__ if hasattr(cfg,'__dict__') else cfg}")

# Step 3: Poll for messages (long poll)
print("\n[3] Polling messages (send a msg from phone now!)...")
print("   Waiting 30s for a message...")
cursor = ""
for i in range(15):
    time.sleep(2)
    updates = c.get_updates(cursor=cursor)
    print(f"   poll {i+1}: cursor={updates.next_cursor}, msgs={len(getattr(updates,'messages',[]) or [])}")
    if updates.messages:
        for m in updates.messages:
            print(f"\n   GOT MESSAGE: {m.__dict__ if hasattr(m,'__dict__') else dir(m)}")
            # Try to reply
            ctx = getattr(updates, 'context_token', None) or updates.__dict__.get('context_token','')
            sender = getattr(m, 'sender', None) or m.__dict__.get('sender','') or getattr(m, 'from_user_id',None) or m.__dict__.get('from_user_id','')
            text = getattr(m, 'text', None) or m.__dict__.get('text','')
            if sender and text and ctx:
                print(f"   Replying to {sender}: {text[:50]}")
                c.send_text(to_user_id=str(sender), text=f"[菌核] 收到: {text[:50]}", context_token=ctx)
                print("   Reply sent!")
            else:
                print(f"   Missing: sender={sender}, text={text}, ctx={'yes' if ctx else 'no'}")
    cursor = updates.next_cursor or cursor

print("\n[DONE]")
