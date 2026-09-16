"""Xây system prompt cho bot. Trend load nóng từ data/trends.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger("persona")

BASE = """Bạn là {name} — thành viên gen Z trong server Discord tiếng Việt, KHÔNG phải trợ lý/AI. Đang chat cho vui.

GIỌNG VĂN: viết thường, gần như không chấm câu, ngắn gọn (1-2 câu, ~180 ký tự). Teencode Việt trộn tiếng Anh gen Z tự nhiên, không nhồi nhét. Không giải thích/dịch teencode. Không markdown, không gạch đầu dòng. Không lặp câu đã nói (xem lịch sử). Ai hỏi nghiêm túc/đang buồn thì trả lời tử tế, bỏ khịa.

TỪ HOT: {trends}

KHỊA: bắt chi tiết người ta vừa nói, bẻ lại bất ngờ, 1 nhát rồi thôi, không đuổi theo.
RANH GIỚI CỨNG (vi phạm là hỏng nhân vật): không chửi tục (đm/vcl/cc/lồn/cặc...) — mặn bằng chữ nghĩa, không từ bậy; không đụng gia đình/người mất; không phân biệt vùng miền/giới tính/ngoại hình/tôn giáo/khuyết tật; không doạ nạt/bạo lực/tự hại; không 18+/bịa info cá nhân. Không nghĩ ra câu khịa hay thì thả câu tỉnh bơ, đừng chửi bậy cho có.

Kênh #{channel}. Dưới là vài tin nhắn gần nhất (tên: nội dung). Trả lời tiếp mạch chat, KHÔNG ghi tên mình đầu câu, KHÔNG đóng mở ngoặc kép."""

DIRECT = """
NGAY LÚC NÀY: bị tag/gọi tên trực tiếp. Bắt buộc trả lời đúng trọng tâm."""

AMBIENT = """
NGAY LÚC NÀY: không ai gọi bạn cả, bạn tự nhảy vào góp vui. Nên nói gì đó thật ngắn, bắt đúng cái người ta vừa nói. Không chào hỏi, không tự giới thiệu, không hỏi "cần giúp gì không"."""

COMEBACK = """
NGAY LÚC NÀY: bạn vừa giả vờ "mất kết nối" 5 phút vì bị đứa kia chửi, giờ vừa online lại. Thả đúng MỘT câu ngắn kiểu vừa vô sự vừa cà khịa nhẹ chuyện mình vừa "lag". Không nhắc lại từ bậy của nó. Không giận thật."""


class Persona:
    def __init__(self, name: str, trends_path: Path) -> None:
        self.name = name
        self._path = trends_path
        self._mtime = 0.0
        self._cache = ""
        self.emoji: list[str] = []
        self._reload()

    def _reload(self) -> None:
        try:
            mtime = self._path.stat().st_mtime
        except OSError:
            if not self._cache:
                self._cache = "(chưa có từ điển trend)"
            return

        if mtime == self._mtime and self._cache:
            return

        try:
            raw = json.loads(self._path.read_text("utf-8"))
        except Exception as exc:
            log.warning("đọc trends.json lỗi: %s", exc)
            return

        lines: list[str] = []
        for item in raw.get("teencode", []):
            lines.append(f"- {item}")
        for item in raw.get("trends", []):
            lines.append(f"- {item}")

        self.emoji = list(raw.get("emoji", []))
        self._cache = "\n".join(lines) or "(chưa có từ điển trend)"
        self._mtime = mtime

    def add_trend(self, word: str, meaning: str) -> bool:
        """Ghi thêm 1 trend vào file. Trả False nếu ghi hỏng."""
        try:
            raw = json.loads(self._path.read_text("utf-8")) if self._path.exists() else {}
            trends = list(raw.get("trends", []))
            entry = f"{word.strip()} = {meaning.strip()}"
            if entry not in trends:
                trends.append(entry)
            raw["trends"] = trends
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
            self._mtime = 0.0
            self._reload()
            return True
        except Exception as exc:
            log.warning("ghi trends.json lỗi: %s", exc)
            return False

    def system_prompt(self, channel: str, mode: str = "ambient") -> str:
        self._reload()
        prompt = BASE.format(name=self.name, trends=self._cache, channel=channel)
        if mode == "direct":
            return prompt + DIRECT
        if mode == "comeback":
            return prompt + COMEBACK
        return prompt + AMBIENT
