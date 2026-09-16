"""Lưu trạng thái chỉnh lúc chạy (bật/tắt chat theo kênh, % trả lời) ra JSON."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger("store")


class RuntimeStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: dict[str, Any] = {"channels": {}, "chance": {}}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text("utf-8"))
            if isinstance(raw, dict):
                self._data["channels"] = dict(raw.get("channels", {}))
                self._data["chance"] = dict(raw.get("chance", {}))
        except Exception as exc:
            log.warning("đọc state lỗi: %s", exc)

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            log.warning("ghi state lỗi: %s", exc)

    # ---- chat tự động theo kênh ----

    def ambient(self, channel_id: int, default: bool) -> bool:
        return bool(self._data["channels"].get(str(channel_id), default))

    def set_ambient(self, channel_id: int, value: bool) -> None:
        self._data["channels"][str(channel_id)] = bool(value)
        self._save()

    # ---- % trả lời theo guild ----

    def chance(self, guild_id: int, default: float) -> float:
        try:
            return float(self._data["chance"].get(str(guild_id), default))
        except (TypeError, ValueError):
            return default

    def set_chance(self, guild_id: int, value: float) -> None:
        self._data["chance"][str(guild_id)] = max(0.0, min(1.0, value))
        self._save()
