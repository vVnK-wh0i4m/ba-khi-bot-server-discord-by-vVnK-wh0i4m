"""Đọc cấu hình từ .env, ép kiểu an toàn, không crash vì typo."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
STATE_DIR = DATA_DIR / "state"

load_dotenv(ROOT / ".env")


def _s(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


def _i(key: str, default: int) -> int:
    try:
        return int(_s(key) or default)
    except ValueError:
        return default


def _f(key: str, default: float) -> float:
    try:
        return float(_s(key) or default)
    except ValueError:
        return default


def _b(key: str, default: bool) -> bool:
    raw = _s(key).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on", "bat", "bật"}


def _ids(key: str) -> set[int]:
    out: set[int] = set()
    for part in _s(key).replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def _words(key: str, default: str = "") -> list[str]:
    return [p.strip().lower() for p in _s(key, default).split(",") if p.strip()]


@dataclass(frozen=True)
class Config:
    discord_token: str
    groq_api_key: str

    chat_model: str
    guard_model: str

    guard_rpm: int
    guard_rpd: int
    guard_tpm: int
    guard_tpd: int
    chat_rpm: int
    chat_rpd: int
    chat_tpm: int
    chat_tpd: int
    chat_max_wait: float
    guard_max_wait: float

    bot_name: str
    bot_aliases: list[str] = field(default_factory=list)

    ambient_default: bool = True
    reply_chance: float = 0.08
    channel_cooldown: float = 25.0
    min_length: int = 4
    max_history: int = 12
    reply_max_tokens: int = 160
    temperature: float = 0.95
    reasoning_effort: str = ""

    allow_channels: set[int] = field(default_factory=set)
    deny_channels: set[int] = field(default_factory=set)
    allow_dm: bool = False

    cooldown_seconds: int = 300
    countdown_interval: float = 5.0
    cooldown_scope: str = "user"
    comeback_roast: bool = True
    insult_require_target: bool = True

    guard_enabled: bool = True
    guard_on_ambient: bool = False

    dev_guild_id: int = 0
    log_level: str = "INFO"

    @classmethod
    def load(cls) -> "Config":
        scope = _s("COOLDOWN_SCOPE", "user").lower()
        if scope not in {"user", "channel", "global"}:
            scope = "user"

        return cls(
            discord_token=_s("DISCORD_TOKEN"),
            groq_api_key=_s("GROQ_API_KEY"),
            chat_model=_s("CHAT_MODEL", "llama-3.3-70b-versatile"),
            guard_model=_s("GUARD_MODEL", "meta-llama/llama-prompt-guard-2-86m"),
            guard_rpm=_i("GUARD_RPM", 30),
            guard_rpd=_i("GUARD_RPD", 14_400),
            guard_tpm=_i("GUARD_TPM", 15_000),
            guard_tpd=_i("GUARD_TPD", 500_000),
            chat_rpm=_i("CHAT_RPM", 30),
            chat_rpd=_i("CHAT_RPD", 1_000),
            chat_tpm=_i("CHAT_TPM", 12_000),
            chat_tpd=_i("CHAT_TPD", 100_000),
            chat_max_wait=_f("CHAT_MAX_WAIT", 3.0),
            guard_max_wait=_f("GUARD_MAX_WAIT", 1.5),
            bot_name=_s("BOT_NAME", "Khịa"),
            bot_aliases=_words("BOT_ALIASES", "bot"),
            ambient_default=_b("AMBIENT_DEFAULT", True),
            reply_chance=min(1.0, max(0.0, _f("REPLY_CHANCE", 0.08))),
            channel_cooldown=_f("CHANNEL_COOLDOWN", 25.0),
            min_length=_i("MIN_LENGTH", 4),
            max_history=max(2, _i("MAX_HISTORY", 12)),
            reply_max_tokens=_i("REPLY_MAX_TOKENS", 160),
            temperature=_f("TEMPERATURE", 0.95),
            reasoning_effort=_s("REASONING_EFFORT", "low").lower(),
            allow_channels=_ids("ALLOW_CHANNELS"),
            deny_channels=_ids("DENY_CHANNELS"),
            allow_dm=_b("ALLOW_DM", False),
            cooldown_seconds=max(10, _i("COOLDOWN_SECONDS", 300)),
            countdown_interval=max(3.0, _f("COUNTDOWN_INTERVAL", 5.0)),
            cooldown_scope=scope,
            comeback_roast=_b("COMEBACK_ROAST", True),
            insult_require_target=_b("INSULT_REQUIRE_TARGET", True),
            guard_enabled=_b("GUARD_ENABLED", True),
            guard_on_ambient=_b("GUARD_ON_AMBIENT", False),
            dev_guild_id=_i("DEV_GUILD_ID", 0),
            log_level=_s("LOG_LEVEL", "INFO").upper(),
        )


CONFIG = Config.load()
