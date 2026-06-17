"""WeChat HTTP API Client — Gewechat / WeChatFerry 统一客户端.

支持的桥接方案:
  - gewechat:  个人微信 IPAD 协议 (Docker部署, 开源免费)
  - wechatferry: Windows WeChat DLL注入 (本地, 需要Windows微信客户端运行)
  - mock:      测试用模拟客户端

Gewechat API 参考: https://github.com/patric04/gewechat
WeChatFerry API: https://github.com/lich0821/WeChatFerry
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from urllib.request import Request, urlopen

logger = logging.getLogger("sclerotium.wechat.client")


# ═══════════════════════════════════════════════════════════════
# Data Classes (immutable)
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class WxMessage:
    """Normalized incoming WeChat message."""
    msg_id: str
    from_user: str           # wxid_xxx
    to_user: str             # wxid_xxx or chatroom id
    content: str
    msg_type: int = 1        # 1=text, 3=image, 34=voice, 43=video, 49=link
    timestamp: int = 0
    is_group: bool = False
    group_id: str = ""
    sender_name: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WxContact:
    """WeChat contact."""
    wxid: str
    nickname: str = ""
    remark: str = ""          # 备注名
    avatar: str = ""
    gender: int = 0           # 0=unknown, 1=male, 2=female
    country: str = ""
    province: str = ""
    city: str = ""


@dataclass(frozen=True)
class WxGroup:
    """WeChat group chat."""
    chatroom_id: str
    name: str = ""
    owner_wxid: str = ""
    member_count: int = 0
    members: tuple[str, ...] = ()
    notice: str = ""


# ═══════════════════════════════════════════════════════════════
# Base Client
# ═══════════════════════════════════════════════════════════════

class BaseWeChatClient:
    """Abstract base for WeChat bridge clients."""

    async def login_qrcode(self) -> dict:
        """Get login QR code. Returns {qrcode_url, uuid, app_id}."""
        raise NotImplementedError

    async def check_login(self, uuid: str) -> dict:
        """Check login status. Returns {status, wxid, nickname}."""
        raise NotImplementedError

    async def send_text(self, to_wxid: str, content: str, at_list: list[str] | None = None) -> str:
        """Send text message. Returns message_id."""
        raise NotImplementedError

    async def send_image(self, to_wxid: str, image_path: str) -> str:
        """Send image. Returns message_id."""
        raise NotImplementedError

    async def send_file(self, to_wxid: str, file_path: str) -> str:
        """Send file. Returns message_id."""
        raise NotImplementedError

    async def get_contacts(self) -> list[WxContact]:
        """Get all contacts."""
        raise NotImplementedError

    async def get_groups(self) -> list[WxGroup]:
        """Get all groups."""
        raise NotImplementedError

    async def get_group_members(self, chatroom_id: str) -> list[WxContact]:
        """Get group members."""
        raise NotImplementedError

    async def create_group(self, wxids: list[str], name: str = "") -> str:
        """Create group chat. Returns chatroom_id."""
        raise NotImplementedError

    async def set_remark(self, wxid: str, remark: str) -> bool:
        """Set remark for a contact."""
        raise NotImplementedError

    async def accept_friend(self, v3: str, v4: str) -> bool:
        """Accept friend request."""
        raise NotImplementedError

    async def get_profile(self) -> dict:
        """Get self profile."""
        raise NotImplementedError

    def on_message(self, callback: Callable[[WxMessage], Any]) -> None:
        """Register message callback."""
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════
# Gewechat Client (HTTP API)
# ═══════════════════════════════════════════════════════════════

class GewechatClient(BaseWeChatClient):
    """Gewechat HTTP API client.

    Gewechat runs as a Docker container providing a REST API.
    Start with: docker run -p 2531:2531 -p 2532:2532 gewechat/gewechat
    """

    def __init__(self, base_url: str = "http://localhost:2531", token: str = ""):
        self._base = base_url.rstrip("/")
        self._token = token
        self._app_id: str = ""
        self._wxid: str = ""
        self._nickname: str = ""
        self._logged_in: bool = False
        self._callbacks: list[Callable[[WxMessage], Any]] = []
        self._callback_port: int = 0

    # ── Auth ──────────────────────────────────────────────────

    async def login_qrcode(self) -> dict:
        """Get QR code URL for WeChat login."""
        data = await self._post("/v2/api/login/getLoginQrCode", {})
        if data.get("ret") == 200:
            qr_data = data.get("data", {})
            self._app_id = qr_data.get("appId", "")
            return {
                "qrcode_url": qr_data.get("qrImgUrl", qr_data.get("qrData", "")),
                "uuid": qr_data.get("uuid", ""),
                "app_id": self._app_id,
            }
        return {"error": data.get("msg", "Failed to get QR code"), "raw": data}

    async def check_login(self, uuid: str) -> dict:
        """Poll login status."""
        data = await self._post("/v2/api/login/checkLogin", {
            "appId": self._app_id,
            "uuid": uuid,
        })
        if data.get("ret") == 200:
            login_data = data.get("data", {})
            status = login_data.get("status", 0)
            # status: 0=pending, 1=scanned, 2=confirmed, 3=logged_in
            if status == 3 or login_data.get("loginInfo"):
                self._logged_in = True
                login_info = login_data.get("loginInfo", login_data)
                self._wxid = login_info.get("wxid", login_info.get("userName", ""))
                self._nickname = login_info.get("nickName", login_info.get("nickname", ""))
                return {"status": "logged_in", "wxid": self._wxid, "nickname": self._nickname}
            elif status == 2:
                return {"status": "confirmed", "wxid": self._wxid}
            elif status == 1:
                return {"status": "scanned"}
            else:
                return {"status": "pending"}
        return {"status": "error", "msg": data.get("msg", "Unknown error")}

    # ── Messaging ─────────────────────────────────────────────

    async def send_text(self, to_wxid: str, content: str, at_list: list[str] | None = None) -> str:
        """Send text message. Use @at_list for group mentions."""
        payload: dict[str, Any] = {
            "appId": self._app_id,
            "toWxid": to_wxid,
            "content": content,
        }
        if at_list:
            payload["ats"] = ",".join(at_list)

        data = await self._post("/v2/api/message/postText", payload)
        if data.get("ret") == 200:
            msg_data = data.get("data", {})
            msg_id = str(msg_data.get("newMsgId", msg_data.get("msgId", "")))
            logger.info("WeChat text sent to %s: %s", to_wxid, content[:50])
            return msg_id
        logger.error("WeChat send failed: %s", data)
        return ""

    async def send_image(self, to_wxid: str, image_path: str) -> str:
        """Send image by path."""
        import base64, os
        if not os.path.exists(image_path):
            logger.error("Image not found: %s", image_path)
            return ""

        # Gewechat image upload flow: upload → get CDN URL → send
        try:
            with open(image_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
            payload = {
                "appId": self._app_id,
                "toWxid": to_wxid,
                "imgBuf": img_data,
            }
            data = await self._post("/v2/api/message/postImage", payload)
            if data.get("ret") == 200:
                return str(data.get("data", {}).get("newMsgId", ""))
        except Exception as e:
            logger.error("WeChat image send failed: %s", e)
        return ""

    async def send_file(self, to_wxid: str, file_path: str) -> str:
        """Send file by path."""
        import os
        if not os.path.exists(file_path):
            logger.error("File not found: %s", file_path)
            return ""

        filename = os.path.basename(file_path)
        payload = {
            "appId": self._app_id,
            "toWxid": to_wxid,
            "fileUrl": file_path,
            "fileName": filename,
        }
        data = await self._post("/v2/api/message/postFile", payload)
        if data.get("ret") == 200:
            return str(data.get("data", {}).get("newMsgId", ""))
        return ""

    # ── Contacts ──────────────────────────────────────────────

    async def get_contacts(self) -> list[WxContact]:
        """Get all contacts list."""
        data = await self._post("/v2/api/contacts/fetchContactsList", {
            "appId": self._app_id,
        })
        if data.get("ret") != 200:
            return []

        contacts = []
        for item in data.get("data", {}).get("friends", data.get("data", [])):
            contacts.append(WxContact(
                wxid=item.get("userName", item.get("wxid", "")),
                nickname=item.get("nickName", item.get("nickname", "")),
                remark=item.get("remark", item.get("remarkName", "")),
                avatar=item.get("bigHeadImgUrl", item.get("avatar", "")),
                gender=item.get("sex", item.get("gender", 0)),
                country=item.get("country", ""),
                province=item.get("province", ""),
                city=item.get("city", ""),
            ))
        logger.info("Loaded %d WeChat contacts", len(contacts))
        return contacts

    # ── Groups ────────────────────────────────────────────────

    async def get_groups(self) -> list[WxGroup]:
        """Get group chat list."""
        data = await self._post("/v2/api/group/chatRoomList", {
            "appId": self._app_id,
        })
        if data.get("ret") != 200:
            return []

        groups = []
        for item in data.get("data", {}).get("chatRooms", data.get("data", [])):
            groups.append(WxGroup(
                chatroom_id=item.get("userName", item.get("chatroomId", "")),
                name=item.get("nickName", item.get("name", "")),
                owner_wxid=item.get("chatRoomOwner", ""),
                member_count=item.get("memberCount", item.get("member_count", 0)),
            ))
        logger.info("Loaded %d WeChat groups", len(groups))
        return groups

    async def get_group_members(self, chatroom_id: str) -> list[WxContact]:
        """Get group chat members."""
        data = await self._post("/v2/api/group/getChatRoomMemberList", {
            "appId": self._app_id,
            "chatroomId": chatroom_id,
        })
        if data.get("ret") != 200:
            return []

        members = []
        for item in data.get("data", {}).get("memberList", data.get("data", [])):
            members.append(WxContact(
                wxid=item.get("userName", item.get("wxid", "")),
                nickname=item.get("nickName", item.get("nickname", "")),
                remark=item.get("displayName", item.get("remark", "")),
            ))
        return members

    async def create_group(self, wxids: list[str], name: str = "") -> str:
        """Create group chat."""
        payload = {
            "appId": self._app_id,
            "userNames": ",".join(wxids),
        }
        if name:
            payload["chatRoomName"] = name
        data = await self._post("/v2/api/group/createChatRoom", payload)
        if data.get("ret") == 200:
            return data.get("data", {}).get("chatroomId", data.get("data", {}).get("userName", ""))
        return ""

    # ── Profile / Friends ─────────────────────────────────────

    async def get_profile(self) -> dict:
        """Get self WeChat profile."""
        data = await self._post("/v2/api/login/getLoginInfo", {
            "appId": self._app_id,
        })
        if data.get("ret") == 200:
            info = data.get("data", {})
            return {
                "wxid": info.get("wxid", self._wxid),
                "nickname": info.get("nickName", self._nickname),
                "avatar": info.get("bigHeadImgUrl", ""),
            }
        return {"wxid": self._wxid, "nickname": self._nickname}

    async def set_remark(self, wxid: str, remark: str) -> bool:
        """Set remark/alias for a contact."""
        data = await self._post("/v2/api/contacts/setFriendRemark", {
            "appId": self._app_id,
            "toWxid": wxid,
            "remark": remark,
        })
        return data.get("ret") == 200

    async def accept_friend(self, v3: str, v4: str) -> bool:
        """Accept a friend request using encryptUserName and ticket."""
        data = await self._post("/v2/api/contacts/acceptFriend", {
            "appId": self._app_id,
            "encryptUserName": v3,
            "ticket": v4,
        })
        return data.get("ret") == 200

    # ── Callback (message receiving) ───────────────────────────

    def on_message(self, callback: Callable[[WxMessage], Any]) -> None:
        """Register a callback for incoming messages."""
        self._callbacks.append(callback)

    def start_callback_server(self, port: int = 2532) -> None:
        """Start a lightweight HTTP server to receive Gewechat callbacks.

        Gewechat pushes new messages to a configurable callback URL.
        We start a tiny server to receive them and dispatch to callbacks.
        """
        self._callback_port = port
        async def _run():
            from aiohttp import web

            async def handle_callback(request: web.Request) -> web.Response:
                try:
                    body = await request.json()
                    msg = self._parse_callback(body)
                    if msg:
                        for cb in self._callbacks:
                            try:
                                result = cb(msg)
                                if asyncio.iscoroutine(result):
                                    asyncio.ensure_future(result)
                            except Exception as e:
                                logger.debug("WeChat callback error: %s", e)
                except Exception as e:
                    logger.error("WeChat callback parse error: %s", e)
                return web.json_response({"ret": 200, "msg": "ok"})

            app = web.Application()
            app.router.add_post("/wechat/callback", handle_callback)
            app.router.add_post("/", handle_callback)
            runner = web.AppRunner(app)
            await runner.setup()
            try:
                site = web.TCPSite(runner, "0.0.0.0", port)
                await site.start()
                logger.info("WeChat callback server on :%d", port)
            except OSError as e:
                if "10048" in str(e) or "address already in use" in str(e).lower():
                    logger.info("WeChat callback port %d in use, skipping server", port)
                else:
                    raise

            try:
                while True:
                    await asyncio.sleep(3600)
            except asyncio.CancelledError:
                await runner.cleanup()

        asyncio.ensure_future(_run())

    def _parse_callback(self, data: dict) -> WxMessage | None:
        """Parse Gewechat callback into WxMessage."""
        msg_type = data.get("msgType", data.get("type", 0))
        from_user = data.get("fromUserName", data.get("fromUser", ""))
        to_user = data.get("toUserName", data.get("toUser", ""))
        content = data.get("content", data.get("msg", ""))

        # Detect group messages (chatroom IDs end with @chatroom)
        is_group = "@chatroom" in from_user
        group_id = from_user if is_group else ""

        # For group messages, extract actual sender
        sender_name = ""
        if is_group and ":\n" in content:
            # Format: "sender_wxid:\nactual_content"
            parts = content.split(":\n", 1)
            sender_name = parts[0]
            content = parts[1] if len(parts) > 1 else content

        return WxMessage(
            msg_id=str(data.get("newMsgId", data.get("msgId", int(time.time() * 1000)))),
            from_user=from_user,
            to_user=to_user,
            content=content,
            msg_type=int(msg_type),
            timestamp=data.get("createTime", data.get("timestamp", int(time.time()))),
            is_group=is_group,
            group_id=group_id,
            sender_name=sender_name,
            raw=data,
        )

    # ── HTTP helpers ──────────────────────────────────────────

    async def _post(self, path: str, payload: dict) -> dict:
        """POST JSON to Gewechat API (async)."""
        url = f"{self._base}{path}"
        headers = {
            "Content-Type": "application/json",
            "X-GEWE-TOKEN": self._token,
        }

        def _do():
            req = Request(url, data=json.dumps(payload).encode(), headers=headers)
            resp = urlopen(req, timeout=30)
            return json.loads(resp.read())

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, _do)
        except Exception as e:
            logger.error("Gewechat API error %s: %s", path, e)
            return {"ret": -1, "msg": str(e)}

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    @property
    def wxid(self) -> str:
        return self._wxid

    @property
    def nickname(self) -> str:
        return self._nickname


# ═══════════════════════════════════════════════════════════════
# Client Factory
# ═══════════════════════════════════════════════════════════════

def create_wechat_client(bridge: str = "gewechat", **kwargs) -> BaseWeChatClient:
    """Factory for creating WeChat bridge clients.

    Args:
        bridge: "gewechat" | "wechatferry" | "mock"
        **kwargs: passed to client constructor (base_url, token, etc.)
    """
    if bridge == "gewechat":
        base_url = kwargs.get("base_url", kwargs.get("api_url", "http://localhost:2531"))
        token = kwargs.get("token", "")
        return GewechatClient(base_url=base_url, token=token)

    elif bridge == "wechatferry":
        logger.warning("WeChatFerry bridge not yet implemented, falling back to Gewechat mock")
        return GewechatClient(**kwargs)

    else:
        # Return mock-capable GewechatClient (will fail gracefully on real calls)
        logger.warning("Unknown WeChat bridge '%s', using Gewechat with no token", bridge)
        return GewechatClient(**kwargs)
