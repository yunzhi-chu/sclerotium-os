"""WeChat Platform Adapter — 微信个人号完整控制.

支持的桥接方案:
  - gewechat:   个人微信 IPAD 协议 (Docker部署, 开源免费, 推荐)
  - wechatferry: Windows WeChat DLL注入 (本地, 需要微信客户端运行)
  - mock:       测试用模拟客户端

Config:
  - bridge: "gewechat" | "wechatferry" | "mock"
  - api_url: 桥接服务地址 (Gewechat默认 http://localhost:2531)
  - token: Gewechat token (可选)
  - callback_port: 消息回调端口 (默认 2532)
  - auto_accept_friends: 自动接受好友请求 (默认 false)

功能覆盖:
  - 发送/接收消息 (文本/图片/文件)
  - 联系人列表 + 备注管理
  - 群聊列表 + 群成员
  - 创建群聊
  - 接受好友请求
  - 消息回调 → EventBus
  - MCP工具贡献 (wechat_send/wechat_list_contacts/wechat_list_groups/wechat_group_members)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from platforms.base import (
    PlatformAdapter, Message, Conversation,
    ConversationType, MessageType, SendResult,
)
from platforms.wechat_client import (
    GewechatClient, BaseWeChatClient, WxMessage,
    create_wechat_client,
)

logger = logging.getLogger("sclerotium.wechat")


class WeChatAdapter(PlatformAdapter):
    """微信适配器 — 个人号完整控制.

    使用方式:
        wx = WeChatAdapter(config={
            "bridge": "gewechat",
            "api_url": "http://localhost:2531",
            "callback_port": 2532,
        })
        await wx.connect()

        # 获取登录二维码
        qr = await wx.get_qrcode()
        print(f"请扫描: {qr['qrcode_url']}")

        # 等待登录完成
        await wx.wait_for_login(timeout=120)

        # 发送消息
        await wx.send_message("wxid_xxx", "你好! 我是菌核。")

        # 获取联系人
        contacts = await wx.get_contacts()

        await wx.disconnect()
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._client: BaseWeChatClient | None = None
        self._bridge = self.config.get("bridge", "gewechat")
        self._api_url = self.config.get("api_url", "http://localhost:2531")
        self._token = self.config.get("token", "")
        self._callback_port = self.config.get("callback_port", 2532)
        self._auto_accept = self.config.get("auto_accept_friends", False)
        self._poll_task: asyncio.Task | None = None
        self._login_event = asyncio.Event()
        self._profile: dict = {}
        self._contacts_cache: list = []
        self._groups_cache: list = []

    # ═══════════════════════════════════════════════════════════════
    # PlatformAdapter 实现
    # ═══════════════════════════════════════════════════════════════

    @property
    def platform_name(self) -> str:
        return "wechat"

    async def connect(self) -> bool:
        """连接到微信桥接服务."""
        try:
            self._client = create_wechat_client(
                bridge=self._bridge,
                api_url=self._api_url,
                token=self._token,
            )

            # Register message callback
            self._client.on_message(self._on_wx_message)

            # Start callback server for Gewechat push
            if self._bridge == "gewechat" and hasattr(self._client, "start_callback_server"):
                self._client.start_callback_server(self._callback_port)

            self._connected = True
            logger.info("WeChat connected via %s at %s", self._bridge, self._api_url)
            return True

        except Exception as e:
            logger.error("WeChat connect failed: %s", e)
            self._record_error(str(e))
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """断开微信连接."""
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None
        self._client = None
        self._connected = False
        logger.info("WeChat disconnected")

    async def send_message(
        self, target: str, content: str, rich_content: dict | None = None,
    ) -> SendResult:
        """发送微信消息.

        Args:
            target: 目标wxid (联系人wxid_xxx 或 群聊xxxxxxxxxx@chatroom)
            content: 文本内容
            rich_content: 富文本 (可选, 暂未支持)
        """
        if not self._client or not self._connected:
            return SendResult(
                success=False, platform="wechat", target=target,
                error="WeChat not connected",
            )

        try:
            msg_id = await self._client.send_text(target, content)
            if msg_id:
                self._record_send()
                return SendResult(
                    success=True, platform="wechat",
                    message_id=msg_id, target=target,
                )
            return SendResult(
                success=False, platform="wechat", target=target,
                error="Send failed (empty msg_id)",
            )
        except Exception as e:
            self._record_error(str(e))
            return SendResult(
                success=False, platform="wechat", target=target,
                error=str(e),
            )

    async def get_recent_messages(
        self, conversation_id: str, limit: int = 20,
    ) -> list[Message]:
        """获取微信会话的最近消息.

        Note: Gewechat doesn't provide message history API.
        消息通过 callback 实时接收并缓存。
        """
        return []

    async def list_conversations(self, limit: int = 50) -> list[Conversation]:
        """列出微信最近会话 (联系人和群聊混合)."""
        conversations = []

        # Contacts as private conversations
        for c in self._contacts_cache[:limit]:
            name = c.remark or c.nickname or c.wxid
            conversations.append(Conversation(
                conversation_id=c.wxid,
                platform="wechat",
                name=name,
                conversation_type=ConversationType.PRIVATE,
            ))

        # Groups
        for g in self._groups_cache[:limit]:
            conversations.append(Conversation(
                conversation_id=g.chatroom_id,
                platform="wechat",
                name=g.name or g.chatroom_id,
                conversation_type=ConversationType.GROUP,
                member_count=g.member_count,
                members=g.members,
            ))

        return conversations[:limit]

    # ═══════════════════════════════════════════════════════════════
    # Extended Methods (override base defaults)
    # ═══════════════════════════════════════════════════════════════

    async def send_file(self, target: str, file_path: str) -> SendResult:
        """发送文件."""
        if not self._client:
            return SendResult(success=False, platform="wechat", target=target,
                              error="Not connected")

        try:
            msg_id = await self._client.send_file(target, file_path)
            if msg_id:
                self._record_send()
                return SendResult(success=True, platform="wechat",
                                  message_id=msg_id, target=target)
            return SendResult(success=False, platform="wechat", target=target,
                              error="Send file failed")
        except Exception as e:
            return SendResult(success=False, platform="wechat", target=target,
                              error=str(e))

    async def react(self, message_id: str, reaction: str) -> bool:
        """微信不支持emoji反应, 发送文字回复代替."""
        # WeChat doesn't have native reactions, send a reply instead
        return False

    async def create_group(self, name: str, member_ids: list[str]) -> str:
        """创建微信群聊."""
        if not self._client:
            return ""

        try:
            chatroom_id = await self._client.create_group(member_ids, name)
            return chatroom_id
        except Exception as e:
            logger.error("Create group failed: %s", e)
            return ""

    async def health_check(self) -> bool:
        """检查微信连接健康."""
        if not self._client or not self._connected:
            return False
        try:
            profile = await self._client.get_profile()
            return bool(profile.get("wxid"))
        except Exception:
            return False

    def get_tools(self) -> list[dict[str, Any]]:
        """贡献微信专属MCP工具 (Gap 12).

        OpenClaw equivalent: channel-tools.ts → listChannelAgentTools
        """
        return [
            {
                "name": "wechat_send",
                "description": "Send a WeChat message to a contact or group.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "wxid of contact or chatroom_id of group"},
                        "content": {"type": "string", "description": "Message text to send"},
                    },
                    "required": ["target", "content"],
                },
                "category": "wechat",
            },
            {
                "name": "wechat_send_file",
                "description": "Send a file via WeChat.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "wxid or chatroom_id"},
                        "file_path": {"type": "string", "description": "Absolute path to file"},
                    },
                    "required": ["target", "file_path"],
                },
                "category": "wechat",
            },
            {
                "name": "wechat_list_contacts",
                "description": "List all WeChat contacts with nickname and remark.",
                "parameters": {"type": "object", "properties": {}, "required": []},
                "category": "wechat",
            },
            {
                "name": "wechat_list_groups",
                "description": "List all WeChat group chats.",
                "parameters": {"type": "object", "properties": {}, "required": []},
                "category": "wechat",
            },
            {
                "name": "wechat_group_members",
                "description": "List members of a WeChat group.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chatroom_id": {"type": "string", "description": "The group chatroom ID"},
                    },
                    "required": ["chatroom_id"],
                },
                "category": "wechat",
            },
            {
                "name": "wechat_create_group",
                "description": "Create a new WeChat group chat with specified members.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Group chat name"},
                        "member_ids": {"type": "array", "items": {"type": "string"}, "description": "List of wxids to add"},
                    },
                    "required": ["member_ids"],
                },
                "category": "wechat",
            },
            {
                "name": "wechat_accept_friend",
                "description": "Accept a pending WeChat friend request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "encrypt_username": {"type": "string", "description": "v3/encryptUserName from friend request"},
                        "ticket": {"type": "string", "description": "v4/ticket from friend request"},
                    },
                    "required": ["encrypt_username", "ticket"],
                },
                "category": "wechat",
            },
            {
                "name": "wechat_profile",
                "description": "Get your own WeChat profile (wxid, nickname, avatar).",
                "parameters": {"type": "object", "properties": {}, "required": []},
                "category": "wechat",
            },
        ]

    # ═══════════════════════════════════════════════════════════════
    # Public API (WeChat-specific)
    # ═══════════════════════════════════════════════════════════════

    async def get_qrcode(self) -> dict:
        """获取登录二维码."""
        if not self._client:
            return {"error": "Client not initialized"}
        return await self._client.login_qrcode()

    async def wait_for_login(self, timeout: float = 120.0) -> dict:
        """轮询等待扫码登录."""
        if not self._client:
            return {"error": "Client not initialized"}

        qr = await self._client.login_qrcode()
        uuid = qr.get("uuid", "")
        if not uuid:
            return {"error": "Failed to get login UUID", **qr}

        start = time.time()
        while time.time() - start < timeout:
            await asyncio.sleep(2)
            status = await self._client.check_login(uuid)
            logger.info("WeChat login status: %s", status.get("status"))
            if status.get("status") == "logged_in":
                self._profile = {"wxid": status.get("wxid"), "nickname": status.get("nickname")}
                logger.info("WeChat logged in as %s (%s)", self._profile["nickname"], self._profile["wxid"])
                return status
            elif status.get("status") == "error":
                return {"error": "Login check failed", **status}

        return {"error": f"Login timeout after {timeout}s"}

    async def get_contacts(self) -> list[dict]:
        """获取联系人列表."""
        if not self._client:
            return []

        try:
            contacts = await self._client.get_contacts()
            self._contacts_cache = contacts
            return [
                {
                    "wxid": c.wxid,
                    "nickname": c.nickname,
                    "remark": c.remark,
                    "gender": c.gender,
                    "city": c.city,
                    "province": c.province,
                }
                for c in contacts
            ]
        except Exception as e:
            logger.error("Get contacts failed: %s", e)
            return []

    async def get_groups(self) -> list[dict]:
        """获取群聊列表."""
        if not self._client:
            return []

        try:
            groups = await self._client.get_groups()
            self._groups_cache = groups
            return [
                {
                    "chatroom_id": g.chatroom_id,
                    "name": g.name,
                    "owner_wxid": g.owner_wxid,
                    "member_count": g.member_count,
                }
                for g in groups
            ]
        except Exception as e:
            logger.error("Get groups failed: %s", e)
            return []

    async def get_group_members(self, chatroom_id: str) -> list[dict]:
        """获取群成员列表."""
        if not self._client:
            return []

        try:
            members = await self._client.get_group_members(chatroom_id)
            return [
                {"wxid": m.wxid, "nickname": m.nickname, "remark": m.remark}
                for m in members
            ]
        except Exception as e:
            logger.error("Get group members failed: %s", e)
            return []

    async def get_profile(self) -> dict:
        """获取自己的微信信息."""
        if not self._client:
            return self._profile
        try:
            profile = await self._client.get_profile()
            self._profile = profile
            return profile
        except Exception:
            return self._profile

    async def accept_friend(self, encrypt_username: str, ticket: str) -> bool:
        """接受好友请求."""
        if not self._client:
            return False
        return await self._client.accept_friend(encrypt_username, ticket)

    async def set_remark(self, wxid: str, remark: str) -> bool:
        """设置联系人备注."""
        if not self._client:
            return False
        return await self._client.set_remark(wxid, remark)

    # ═══════════════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════════════

    def _on_wx_message(self, wx_msg: WxMessage) -> None:
        """Handle incoming WeChat message → dispatch to callbacks/EventBus."""
        msg_type = MessageType.TEXT
        if wx_msg.msg_type == 3:
            msg_type = MessageType.IMAGE
        elif wx_msg.msg_type == 49:
            msg_type = MessageType.RICH
        elif wx_msg.msg_type == 34:
            msg_type = MessageType.UNKNOWN  # voice

        conversation_id = wx_msg.group_id if wx_msg.is_group else wx_msg.from_user

        msg = Message(
            platform="wechat",
            message_id=wx_msg.msg_id,
            conversation_id=conversation_id,
            sender_id=wx_msg.from_user,
            sender_name=wx_msg.sender_name or "",
            content=wx_msg.content,
            timestamp=wx_msg.timestamp / 1000.0 if wx_msg.timestamp > 1e10 else wx_msg.timestamp,
            message_type=msg_type,
            is_mention="@Sclerotium" in wx_msg.content or "@菌核" in wx_msg.content,
            raw=wx_msg.raw,
        )

        self._notify_message(msg)
