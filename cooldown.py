"""Bị chửi -> giả vờ 'mất kết nối', đếm ngược realtime, rồi online lại.

Đồng hồ chạy bằng hai cách chồng lên nhau:
  1. Sửa embed mỗi COUNTDOWN_INTERVAL giây (mặc định 5s -> 60 lần cho 5 phút).
     Discord giới hạn sửa tin nhắn khá chặt, đừng hạ xuống dưới 3 giây.
  2. Timestamp tương đối <t:epoch:R> — Discord client tự đếm, không tốn
     request nào. Kể cả khi bot bị rate limit thì chỗ này vẫn nhảy.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Awaitable, Callable, Optional

import discord

log = logging.getLogger("cooldown")

ERROR_CODES = [
    "ERR_CONN_RESET_0x5F",
    "WS_GATEWAY_TIMEOUT_4006",
    "INFER_NODE_UNREACHABLE",
    "ECONNRESET (upstream)",
    "TLS_HANDSHAKE_ABORTED",
    "MODEL_SOCKET_HANGUP",
]

NODES = ["sea-gw-04", "sgp-infer-02", "hnd-edge-11", "fra-relay-07", "iad-lb-03"]

BAR_FULL = "▰"
BAR_EMPTY = "▱"


def _mmss(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    return f"{total // 60:02d}:{total % 60:02d}"


def _bar(ratio: float, width: int = 14) -> str:
    filled = max(0, min(width, int(round(ratio * width))))
    return BAR_FULL * filled + BAR_EMPTY * (width - filled)


class CooldownManager:
    def __init__(
        self,
        *,
        duration: int,
        interval: float,
        scope: str,
        resume_hook: Optional[Callable[[discord.abc.Messageable, Optional[discord.abc.User]], Awaitable[None]]] = None,
    ) -> None:
        self.duration = duration
        self.interval = interval
        self.scope = scope
        self._resume_hook = resume_hook
        self._until: dict[str, float] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    # ---------- key ----------

    def key_for(self, message: discord.Message) -> str:
        if self.scope == "global":
            return f"g:{message.guild.id if message.guild else 0}"
        if self.scope == "channel":
            return f"c:{message.channel.id}"
        return f"u:{message.author.id}:{message.channel.id}"

    def is_active(self, key: str) -> bool:
        until = self._until.get(key)
        if until is None:
            return False
        if time.monotonic() >= until:
            self._until.pop(key, None)
            return False
        return True

    def remaining(self, key: str) -> float:
        until = self._until.get(key)
        return max(0.0, until - time.monotonic()) if until else 0.0

    def active_items(self) -> list[tuple[str, float]]:
        now = time.monotonic()
        return [(k, v - now) for k, v in self._until.items() if v > now]

    def clear(self, key: Optional[str] = None) -> int:
        keys = [key] if key else list(self._until)
        count = 0
        for k in keys:
            if self._until.pop(k, None) is not None:
                count += 1
            task = self._tasks.pop(k, None)
            if task and not task.done():
                task.cancel()
        return count

    # ---------- trigger ----------

    async def trigger(self, message: discord.Message, reason: str = "") -> bool:
        key = self.key_for(message)
        if self.is_active(key):
            return False

        self._until[key] = time.monotonic() + self.duration
        log.info("cooldown %s (%ds) — lý do: %s", key, self.duration, reason or "n/a")

        task = asyncio.create_task(self._countdown(message, key))
        self._tasks[key] = task
        return True

    # ---------- embed ----------

    def _embed(self, remaining: float, code: str, node: str, resume_at: int) -> discord.Embed:
        done = 1.0 - (remaining / self.duration)
        embed = discord.Embed(
            title="⚠️ MẤT KẾT NỐI TỚI MÁY CHỦ AI",
            description=(
                "```ansi\n"
                f"\u001b[0;31m[ERROR]\u001b[0m  {code}\n"
                f"\u001b[0;34m[NODE ]\u001b[0m  {node}\n"
                f"\u001b[0;33m[STATE]\u001b[0m  reconnecting…\n"
                "```"
            ),
            colour=0xED4245,
        )
        embed.add_field(
            name="⏳ Thử lại sau",
            value=f"# `{_mmss(remaining)}`\n`{_bar(done)}` **{int(done * 100)}%**",
            inline=False,
        )
        embed.add_field(name="🔌 Dự kiến online", value=f"<t:{resume_at}:R>", inline=False)
        embed.set_footer(text="Vui lòng đợi 5 phút • hệ thống sẽ tự kết nối lại")
        return embed

    def _done_embed(self, code: str, node: str, waited: int) -> discord.Embed:
        embed = discord.Embed(
            title="✅ ĐÃ KẾT NỐI LẠI",
            description=(
                "```ansi\n"
                f"\u001b[0;32m[ OK  ]\u001b[0m  {node} online\n"
                f"\u001b[0;30m[INFO ]\u001b[0m  recovered from {code}\n"
                f"\u001b[0;30m[INFO ]\u001b[0m  downtime {_mmss(waited)}\n"
                "```"
            ),
            colour=0x57F287,
        )
        embed.add_field(name="⏳ Thử lại sau", value=f"# `00:00`\n`{_bar(1.0)}` **100%**", inline=False)
        embed.set_footer(text="Kết nối ổn định • bạn có thể tiếp tục")
        return embed

    # ---------- loop ----------

    async def _countdown(self, message: discord.Message, key: str) -> None:
        channel = message.channel
        code = random.choice(ERROR_CODES)
        node = random.choice(NODES)
        resume_at = int(time.time()) + self.duration
        started = time.monotonic()
        panel: Optional[discord.Message] = None

        try:
            panel = await channel.send(embed=self._embed(self.duration, code, node, resume_at))
        except discord.HTTPException as exc:
            log.warning("không gửi được panel lỗi: %s", exc)

        try:
            while True:
                await asyncio.sleep(self.interval)
                remaining = self.remaining(key)
                if remaining <= 0.5:
                    break
                if panel is None:
                    continue
                try:
                    await panel.edit(embed=self._embed(remaining, code, node, resume_at))
                except discord.NotFound:
                    panel = None
                except discord.HTTPException as exc:
                    log.debug("edit đếm ngược lỗi (bỏ qua): %s", exc)

            waited = int(time.monotonic() - started)
            if panel is not None:
                try:
                    await panel.edit(embed=self._done_embed(code, node, waited))
                except discord.HTTPException:
                    pass

            if self._resume_hook is not None:
                author = message.author if self.scope == "user" else None
                try:
                    await self._resume_hook(channel, author)
                except Exception as exc:
                    log.warning("resume hook lỗi: %s", exc)

        except asyncio.CancelledError:
            if panel is not None:
                try:
                    await panel.edit(embed=self._done_embed(code, node, int(time.monotonic() - started)))
                except discord.HTTPException:
                    pass
            raise
        finally:
            self._until.pop(key, None)
            self._tasks.pop(key, None)
