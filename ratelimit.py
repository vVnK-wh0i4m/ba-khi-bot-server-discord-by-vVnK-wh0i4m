"""Rate limiter theo TỪNG model.

Groq tính limit riêng cho mỗi model, nên prompt-guard (30 RPM / 14.4K RPD /
15K TPM / 500K TPD) và model chat có hai cái "ví" khác nhau. Module này giữ:

  - cửa sổ trượt 60 giây cho RPM + TPM
  - bộ đếm theo ngày UTC cho RPD + TPD, ghi ra đĩa nên restart không mất

Cách dùng::

    res = await limiter.acquire(est_tokens=400, max_wait=3.0)
    if res is None:
        return  # hết quota -> im lặng bỏ qua
    ...gọi API...
    res.settle(usage["total_tokens"])  # chốt lại số token thật
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Optional


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "model"


@dataclass(frozen=True)
class Limits:
    rpm: int
    rpd: int
    tpm: int
    tpd: int


class Reservation:
    """Chỗ đã giữ trong cửa sổ rate limit; nhớ settle() sau khi có usage thật."""

    __slots__ = ("_limiter", "_entry", "_settled")

    def __init__(self, limiter: "ModelLimiter", entry: list) -> None:
        self._limiter = limiter
        self._entry = entry
        self._settled = False

    def settle(self, actual_tokens: int) -> None:
        if self._settled:
            return
        self._settled = True
        self._limiter._settle(self._entry, max(0, int(actual_tokens)))


class ModelLimiter:
    def __init__(self, model: str, limits: Limits, state_dir: Optional[Path] = None) -> None:
        self.model = model
        self.limits = limits
        self._window: Deque[list] = deque()  # [monotonic_ts, tokens]
        self._lock = asyncio.Lock()
        self._day = _utc_day()
        self._day_requests = 0
        self._day_tokens = 0
        self._path = (state_dir / f"{_slug(model)}.json") if state_dir else None
        self._last_save = 0.0
        self._load()

    # ---------- persistence ----------

    def _load(self) -> None:
        if not self._path or not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text("utf-8"))
        except Exception:
            return
        if raw.get("day") == self._day:
            self._day_requests = int(raw.get("requests", 0))
            self._day_tokens = int(raw.get("tokens", 0))

    def _maybe_save(self, force: bool = False) -> None:
        if not self._path:
            return
        now = time.monotonic()
        if not force and now - self._last_save < 15.0:
            return
        self._last_save = now
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(
                    {"day": self._day, "requests": self._day_requests, "tokens": self._day_tokens},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except OSError:
            pass

    # ---------- window helpers ----------

    def _prune(self, now: float) -> None:
        while self._window and now - self._window[0][0] >= 60.0:
            self._window.popleft()

    def _minute_tokens(self) -> int:
        return int(sum(entry[1] for entry in self._window))

    def _roll_day(self) -> None:
        today = _utc_day()
        if today != self._day:
            self._day = today
            self._day_requests = 0
            self._day_tokens = 0
            self._maybe_save(force=True)

    # ---------- api ----------

    async def acquire(self, est_tokens: int, max_wait: float = 0.0) -> Optional[Reservation]:
        """Giữ chỗ cho 1 request. Trả None nếu hết quota hoặc chờ quá lâu."""
        est = max(1, int(est_tokens))
        if est > self.limits.tpm or est > self.limits.tpd:
            return None

        deadline = time.monotonic() + max(0.0, max_wait)

        while True:
            async with self._lock:
                now = time.monotonic()
                self._prune(now)
                self._roll_day()

                if self._day_requests >= self.limits.rpd:
                    return None
                if self._day_tokens + est > self.limits.tpd:
                    return None

                room_req = len(self._window) < self.limits.rpm
                room_tok = self._minute_tokens() + est <= self.limits.tpm
                if room_req and room_tok:
                    entry = [now, float(est)]
                    self._window.append(entry)
                    self._day_requests += 1
                    self._day_tokens += est
                    self._maybe_save()
                    return Reservation(self, entry)

                # bao lâu nữa thì slot cũ nhất rơi khỏi cửa sổ 60s
                wait_for = 60.0 - (now - self._window[0][0]) + 0.05 if self._window else 0.25

            remaining = deadline - time.monotonic()
            if remaining <= 0 or wait_for > remaining:
                return None
            await asyncio.sleep(min(wait_for, remaining))

    def _settle(self, entry: list, actual_tokens: int) -> None:
        delta = actual_tokens - int(entry[1])
        entry[1] = float(actual_tokens)
        self._day_tokens = max(0, self._day_tokens + delta)
        self._maybe_save()

    def snapshot(self) -> dict:
        now = time.monotonic()
        self._prune(now)
        self._roll_day()
        return {
            "model": self.model,
            "rpm": (len(self._window), self.limits.rpm),
            "tpm": (self._minute_tokens(), self.limits.tpm),
            "rpd": (self._day_requests, self.limits.rpd),
            "tpd": (self._day_tokens, self.limits.tpd),
        }


class LimiterRegistry:
    def __init__(self, state_dir: Optional[Path] = None) -> None:
        self._state_dir = state_dir
        self._limiters: dict[str, ModelLimiter] = {}

    def register(self, model: str, limits: Limits) -> ModelLimiter:
        limiter = ModelLimiter(model, limits, self._state_dir)
        self._limiters[model] = limiter
        return limiter

    def get(self, model: str) -> ModelLimiter:
        if model not in self._limiters:
            # model lạ -> giả định limit thoáng, vẫn có phanh
            self.register(model, Limits(rpm=30, rpd=1_000, tpm=12_000, tpd=100_000))
        return self._limiters[model]

    def all(self) -> list[ModelLimiter]:
        return list(self._limiters.values())

    def flush(self) -> None:
        for limiter in self._limiters.values():
            limiter._maybe_save(force=True)
