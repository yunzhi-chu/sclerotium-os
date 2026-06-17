"""Quick test: verify wcferry can connect to running WeChat."""
from wcferry import Wcf

print("[wcferry] Connecting to WeChat...")
wcf = Wcf(debug=False)

info = wcf.get_self_info()
print(f"wxid: {info.get('wxid')}")
print(f"name: {info.get('name')}")
print(f"mobile: {info.get('mobile', 'N/A')}")

contacts = wcf.get_contacts()
print(f"contacts: {len(contacts)}")
if contacts:
    for c in contacts[:5]:
        print(f"  - {c.get('name', '?')} ({c.get('wxid', '?')})")

rooms = wcf.get_chatrooms()
print(f"chatrooms: {len(rooms)}")
if rooms:
    for r in rooms[:5]:
        print(f"  - {r.get('name', '?')} ({r.get('wxid', '?')})")

print("[wcferry] SUCCESS!")
wcf.cleanup()
