"""bá khí bot — Discord gen Z — đọc mọi kênh, khịa, và "mất kết nối 5 phút" khi bị chửi.

Luồng xử lý 1 tin nhắn:

    tin nhắn tới
      -> lọc (bot khác / kênh cấm / không có quyền gửi)
      -> lưu vào lịch sử kênh
      -> đang trong cooldown? -> im lặng, hết
      -> có nhắm vào bot không? (tag / reply / gọi tên)
      -> quét chửi bậy bằng regex local (miễn phí)  -> dính thì bật "lỗi kết nối"
      -> prompt-guard trên Groq (chỉ khi bị nhắm)   -> MALICIOUS thì cũng bật
      -> quyết định có trả lời không (bị tag = luôn / không thì random %)
      -> xin slot rate limit -> gọi model chat -> gửi reply
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from collections import defaultdict, deque
from typing import Deque, Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import CONFIG, DATA_DIR, STATE_DIR
from cooldown import CooldownManager, _mmss
from groq_api import GroqClient, GroqError
from guard import InsultScanner, PromptGuard, normalize_loose
from persona import Persona
from ratelimit import Limits, LimiterRegistry
from store import RuntimeStore

logging.basicConfig(
    level=getattr(logging, CONFIG.log_level, logging.INFO),
    format="%(asctime)s %(levelname)-7s %(name)-9s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bot")

# ---------------------------------------------------------------- hạ tầng

registry = LimiterRegistry(STATE_DIR)
registry.register(CONFIG.chat_model, Limits(CONFIG.chat_rpm, CONFIG.chat_rpd, CONFIG.chat_tpm, CONFIG.chat_tpd))
registry.register(CONFIG.guard_model, Limits(CONFIG.guard_rpm, CONFIG.guard_rpd, CONFIG.guard_tpm, CONFIG.guard_tpd))

groq = GroqClient(CONFIG.groq_api_key, registry)
guard = PromptGuard(groq, CONFIG.guard_model, max_wait=CONFIG.guard_max_wait)
scanner = InsultScanner(DATA_DIR / "trigger_words.txt")
persona = Persona(CONFIG.bot_name, DATA_DIR / "trends.json")
store = RuntimeStore(STATE_DIR / "runtime.json")

HISTORY: dict[int, Deque[tuple[str, str, bool]]] = defaultdict(lambda: deque(maxlen=CONFIG.max_history))
LAST_REPLY: dict[int, float] = defaultdict(float)

intents = discord.Intents.default()
intents.message_content = True  # PRIVILEGED — nhớ bật trong Developer Portal
intents.guilds = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents, help_command=None)

# ---------------------------------------------------------------- tiện ích

_CLEAN_PREFIX = re.compile(rf"^\s*{re.escape(CONFIG.bot_name)}\s*[:：>-]\s*", re.IGNORECASE)
_MD_NOISE = re.compile(r"^\s*(#{1,6}\s+|[*\-•]\s+)", re.MULTILINE)


def polish(text: str) -> str:
    """Cắt mấy thói quen 'trợ lý' của model ra khỏi câu trả lời."""
    out = (text or "").strip()
    out = _CLEAN_PREFIX.sub("", out)
    out = _MD_NOISE.sub("", out)
    if len(out) >= 2 and out[0] in "\"'“”" and out[-1] in "\"'“”":
        out = out[1:-1].strip()
    out = re.sub(r"\n{2,}", "\n", out)
    return out[:400].strip()


def channel_allowed(channel_id: int) -> bool:
    if channel_id in CONFIG.deny_channels:
        return False
    if CONFIG.allow_channels:
        return channel_id in CONFIG.allow_channels
    return True


def can_speak(message: discord.Message) -> bool:
    if message.guild is None:
        return CONFIG.allow_dm
    me = message.guild.me
    if me is None:
        return False
    perms = message.channel.permissions_for(me)
    return bool(perms.send_messages and perms.view_channel)


def is_targeted(message: discord.Message) -> bool:
    if bot.user is not None and bot.user in message.mentions:
        return True

    ref = message.reference
    if ref is not None and isinstance(ref.resolved, discord.Message):
        if bot.user is not None and ref.resolved.author.id == bot.user.id:
            return True

    words = set(normalize_loose(message.clean_content).split())
    aliases = {normalize_loose(a) for a in ([CONFIG.bot_name] + CONFIG.bot_aliases)}
    return bool(words & {a for a in aliases if a})


def build_messages(message: discord.Message, mode: str) -> list[dict]:
    channel_name = getattr(message.channel, "name", "dm")
    payload: list[dict] = [{"role": "system", "content": persona.system_prompt(channel_name, mode)}]

    history = list(HISTORY[message.channel.id])
    for author, text, from_bot in history[:-1]:
        if from_bot:
            payload.append({"role": "assistant", "content": text})
        else:
            payload.append({"role": "user", "content": f"{author}: {text}"})

    payload.append({"role": "user", "content": f"{message.author.display_name}: {message.clean_content}"})
    return payload


async def generate(message: discord.Message, mode: str) -> Optional[str]:
    try:
        raw = await groq.complete(
            CONFIG.chat_model,
            build_messages(message, mode),
            max_tokens=CONFIG.reply_max_tokens,
            temperature=CONFIG.temperature,
            max_wait=CONFIG.chat_max_wait,
            reasoning_effort=CONFIG.reasoning_effort or None,
        )
    except GroqError as exc:
        log.warning("gọi chat model lỗi: %s", exc)
        return None
    except Exception:
        log.exception("lỗi không lường trước khi gọi model")
        return None

    if raw is None:
        return None
    return polish(raw) or None


async def on_reconnect(channel: discord.abc.Messageable, author: Optional[discord.abc.User]) -> None:
    """Sau khi 'kết nối lại' thì thả 1 câu khịa nhẹ."""
    if not CONFIG.comeback_roast:
        return

    who = getattr(author, "display_name", "ai đó")
    channel_name = getattr(channel, "name", "dm")
    payload = [
        {"role": "system", "content": persona.system_prompt(channel_name, "comeback")},
        {"role": "user", "content": f"{who}: (vừa chửi bot xong, bot lag 5 phút, giờ vừa online lại)"},
    ]
    try:
        raw = await groq.complete(
            CONFIG.chat_model,
            payload,
            max_tokens=80,
            temperature=1.0,
            max_wait=CONFIG.chat_max_wait,
            reasoning_effort=CONFIG.reasoning_effort or None,
        )
    except Exception:
        return

    line = polish(raw or "")
    if line:
        try:
            await channel.send(line[:300])
        except discord.HTTPException:
            pass


cooldowns = CooldownManager(
    duration=CONFIG.cooldown_seconds,
    interval=CONFIG.countdown_interval,
    scope=CONFIG.cooldown_scope,
    resume_hook=on_reconnect,
)

# ---------------------------------------------------------------- sự kiện


@bot.event
async def on_ready() -> None:
    log.info("đăng nhập: %s (%s)", bot.user, bot.user.id if bot.user else "?")
    log.info("chat=%s | guard=%s | %d từ khoá chửi", CONFIG.chat_model, CONFIG.guard_model, scanner.size)
    try:
        await bot.change_presence(activity=discord.CustomActivity(name="đang hóng drama 👀"))
    except discord.HTTPException:
        pass


@bot.event
async def on_message(message: discord.Message) -> None:
    if bot.user is None or message.author.id == bot.user.id:
        return
    if message.author.bot:
        return
    if message.guild is None and not CONFIG.allow_dm:
        return
    if not channel_allowed(message.channel.id):
        return

    content = (message.clean_content or "").strip()
    if not content:
        return
    if not can_speak(message):
        return

    HISTORY[message.channel.id].append((message.author.display_name, content, False))

    key = cooldowns.key_for(message)
    if cooldowns.is_active(key):
        return  # đang "mất kết nối", im re

    targeted = is_targeted(message)

    # --- lớp 1: regex local, 0 đồng ---
    hit = scanner.scan(content)
    if hit and (targeted or not CONFIG.insult_require_target):
        await cooldowns.trigger(message, reason=f"insult:{hit}")
        return

    # --- lớp 2: prompt-guard trên Groq ---
    if CONFIG.guard_enabled and (targeted or CONFIG.guard_on_ambient):
        verdict = await guard.is_malicious(content)
        if verdict:
            await cooldowns.trigger(message, reason="prompt-guard:MALICIOUS")
            return

    # --- có trả lời không? ---
    if targeted:
        mode = "direct"
    else:
        if not store.ambient(message.channel.id, CONFIG.ambient_default):
            return
        if len(content) < CONFIG.min_length:
            return
        if time.monotonic() - LAST_REPLY[message.channel.id] < CONFIG.channel_cooldown:
            return
        guild_id = message.guild.id if message.guild else 0
        if random.random() > store.chance(guild_id, CONFIG.reply_chance):
            return
        mode = "ambient"

    LAST_REPLY[message.channel.id] = time.monotonic()

    async with message.channel.typing():
        reply = await generate(message, mode)

    if not reply:
        try:
            await message.add_reaction("⏳")  # hết slot rate limit / tin nhắn quá dài
        except discord.HTTPException:
            pass
        return

    try:
        if targeted:
            await message.reply(reply[:1900], mention_author=False)
        else:
            await message.channel.send(reply[:1900])
    except discord.HTTPException as exc:
        log.warning("gửi reply lỗi: %s", exc)
        return

    HISTORY[message.channel.id].append((CONFIG.bot_name, reply, True))


# ---------------------------------------------------------------- lệnh

bakhi = app_commands.Group(name="bakhi", description=f"Điều khiển {CONFIG.bot_name}")


@bakhi.command(name="status", description="Xem quota Groq, cooldown và trạng thái kênh")
async def cmd_status(interaction: discord.Interaction) -> None:
    embed = discord.Embed(title=f"📊 {CONFIG.bot_name} — trạng thái", colour=0x5865F2)

    for limiter in registry.all():
        s = limiter.snapshot()
        embed.add_field(
            name=f"`{s['model']}`",
            value=(
                f"phút: **{s['rpm'][0]}/{s['rpm'][1]}** req · **{s['tpm'][0]:,}/{s['tpm'][1]:,}** tok\n"
                f"ngày: **{s['rpd'][0]:,}/{s['rpd'][1]:,}** req · **{s['tpd'][0]:,}/{s['tpd'][1]:,}** tok"
            ),
            inline=False,
        )

    ambient = store.ambient(interaction.channel_id or 0, CONFIG.ambient_default)
    guild_id = interaction.guild_id or 0
    chance = store.chance(guild_id, CONFIG.reply_chance)
    embed.add_field(
        name="Kênh này",
        value=f"chat tự động: **{'bật' if ambient else 'tắt'}** · xác suất nhảy vào: **{chance * 100:.0f}%**",
        inline=False,
    )

    active = cooldowns.active_items()
    if active:
        lines = [f"`{k}` còn **{_mmss(rem)}**" for k, rem in active[:8]]
        embed.add_field(name=f"Đang 'mất kết nối' ({len(active)})", value="\n".join(lines), inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bakhi.command(name="chat", description="Bật/tắt chat tự động ở kênh này")
@app_commands.describe(bat="true = bot tự nhảy vào chat, false = chỉ trả lời khi bị tag")
@app_commands.checks.has_permissions(manage_guild=True)
async def cmd_chat(interaction: discord.Interaction, bat: bool) -> None:
    store.set_ambient(interaction.channel_id or 0, bat)
    await interaction.response.send_message(
        f"chat tự động ở kênh này: **{'bật' if bat else 'tắt'}**", ephemeral=True
    )


@bakhi.command(name="chance", description="Chỉnh % bot tự nhảy vào chat (0-100)")
@app_commands.checks.has_permissions(manage_guild=True)
async def cmd_chance(interaction: discord.Interaction, phan_tram: app_commands.Range[int, 0, 100]) -> None:
    store.set_chance(interaction.guild_id or 0, phan_tram / 100)
    await interaction.response.send_message(f"ok, giờ là **{phan_tram}%**", ephemeral=True)


@bakhi.command(name="trend", description="Dạy bot một từ/trend mới")
@app_commands.describe(tu="từ hoặc cụm từ", nghia="nghĩa / dùng khi nào")
async def cmd_trend(interaction: discord.Interaction, tu: str, nghia: str) -> None:
    ok = persona.add_trend(tu, nghia)
    msg = f"đã nhét **{tu}** vào từ điển 🔥" if ok else "ghi file hỏng rồi, check log"
    await interaction.response.send_message(msg, ephemeral=True)


@bakhi.command(name="unmute", description="Gỡ trạng thái 'mất kết nối' ngay lập tức")
@app_commands.checks.has_permissions(manage_guild=True)
async def cmd_unmute(interaction: discord.Interaction) -> None:
    count = cooldowns.clear()
    await interaction.response.send_message(f"đã gỡ **{count}** cooldown", ephemeral=True)


@bakhi.error
async def bakhi_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        text = "lệnh này cần quyền **Manage Server** nha 🙂‍↔️"
    else:
        log.exception("lỗi slash command", exc_info=error)
        text = "có gì đó sai sai, check log giùm"
    if interaction.response.is_done():
        await interaction.followup.send(text, ephemeral=True)
    else:
        await interaction.response.send_message(text, ephemeral=True)


bot.tree.add_command(bakhi)


@bot.event
async def setup_hook() -> None:
    if CONFIG.dev_guild_id:
        guild = discord.Object(id=CONFIG.dev_guild_id)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        log.info("sync slash command vào guild %s", CONFIG.dev_guild_id)
    else:
        await bot.tree.sync()
        log.info("sync slash command global (có thể mất tới 1 tiếng)")


async def shutdown() -> None:
    registry.flush()
    await groq.aclose()


def main() -> None:
    missing = [k for k, v in (("DISCORD_TOKEN", CONFIG.discord_token), ("GROQ_API_KEY", CONFIG.groq_api_key)) if not v]
    if missing:
        raise SystemExit(f"Thiếu {', '.join(missing)} trong .env — copy .env.example thành .env rồi điền vào.")

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        bot.run(CONFIG.discord_token, log_handler=None)
    finally:
        try:
            asyncio.run(shutdown())
        except Exception:
            pass


if __name__ == "__main__":
    main()
