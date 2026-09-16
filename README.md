<div align="center">

# 🐲 Bá Khí Bot

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Discord.py](https://img.shields.io/badge/Discord.py-2.4%2B-blue?logo=discord&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLM-orange)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Download](https://img.shields.io/badge/Download-Zip-blue?style=for-the-badge&logo=github)

**Discord Bot Gen Z đọc mọi kênh, khịa cà khịa, và "mất kết nối 5 phút" khi bị chửi.**

[📥 **Tải code (.zip)**](https://github.com/vVnK-wh0i4m/ba-khi-bot-server-discord-by-vVnK-wh0i4m/archive/refs/heads/main.zip) • [📦 **Clone repo**](https://github.com/vVnK-wh0i4m/ba-khi-bot-server-discord-by-vVnK-wh0i4m.git)

</div>

---

## ⚠️ Cảnh báo quan trọng

> **Công cụ này được cung cấp cho mục đích giải trí, thử nghiệm và nghiên cứu.** Người dùng **chịu toàn bộ trách nhiệm** khi sử dụng.

---

## 📋 Mục lục

- [Giới thiệu](#-giới-thiệu)
- [Cách bot hoạt động](#-cách-bot-hoạt-động)
- [Tính năng](#-tính-năng)
- [Yêu cầu hệ thống](#-yêu-cầu-hệ-thống)
- [Cài đặt và chạy](#-cài-đặt-và-chạy)
- [Cấu hình](#-cấu-hình)
- [Danh sách lệnh](#-danh-sách-lệnh)
- [Cấu trúc dự án](#-cấu-trúc-dự-án)
- [Panel "mất kết nối"](#-panel-mất-kết-nối)
- [Chỉnh bot](#-chỉnh-bot)
- [FAQ](#-câu-hỏi-thường-gặp)
- [Bản quyền](#-bản-quyền)

---

## 🌟 Giới thiệu

**Bá Khí Bot** là Discord Bot Python được xây dựng bằng **Discord.py** và **Groq API**. Bot có tính cách Gen Z, đọc mọi kênh, chat teencode Việt trộn tiếng Anh, khịa cà khịa, và khi bị ai chửi thì giả vờ mất kết nối kèm đồng hồ đếm ngược realtime.

**Điểm nổi bật:**
- 🧠 AI-powered chat bằng Groq (openai/gpt-oss-120b)
- 🛡️ Prompt guard chống jailbreak (llama-prompt-guard-2-86m)
- 💬 Chat tự động theo xác suất + cooldown
- 😤 Panel "LỖI KẾT NỐI" khi bị chửi
- 🎯 Slash commands điều khiển realtime

---

## 🔄 Cách bot hoạt động

```
┌──────────────┐
│ tin nhắn tới │
└──────┬───────┘
       ▼
  lọc kênh / quyền        ─► không qua thì dừng
       ▼
  lưu vào lịch sử kênh
       ▼
  đang cooldown?          ─► im lặng, dừng
       ▼
  có bị nhắm tới không?   (tag / reply / gọi tên)
       ▼
  ① regex local           ─► dính chửi  ─► panel "LỖI KẾT NỐI" 05:00
       ▼
  ② prompt-guard (Groq)   ─► MALICIOUS  ─► panel "LỖI KẾT NỐI" 05:00
       ▼
  có trả lời không?       (bị tag = luôn luôn | không = random %)
       ▼
  xin slot rate limit     ─► hết slot thì bỏ qua, không spam 429
       ▼
  gọi model chat ─► gửi reply
```

---

## 🚀 Tính năng

### 🧠 AI Chat

| Tính năng | Mô tả |
|-----------|--------|
| Chat tự động | Bot tự nhảy vào chat theo xác suất (mặc định 8%) |
| Tag/Reply | Trả lời ngay khi bị tag hoặc reply |
| Context | Giữ lịch sử 6 tin nhắn gần nhất mỗi kênh |
| Teencode | Chat bằng teencode Việt trộn tiếng Anh |

### 🛡️ Anti-Jailbreak

| Tính năng | Mô tả |
|-----------|--------|
| Prompt Guard | llama-prompt-guard-2-86m phân loại BENIGN/MALICIOUS |
| Regex Scanner | Regex local miễn phí bắt chửi bậy |
| 2 lớp bảo vệ | Prompt guard + regex hoạt động song song |

### 😤 Cooldown System

| Tính năng | Mô tả |
|-----------|--------|
| Panel "LỖI KẾT NỐI" | Embed đỏ + đồng hồ đếm ngược realtime |
| 3 phạm vi | `user` / `channel` / `global` |
| Comeback roast | Bot thả câu khịa nhẹ sau khi "kết nối lại" |

### 🎯 Slash Commands

| Lệnh | Mô tả |
|-------|--------|
| `/bakhi status` | Xem quota Groq, cooldown, trạng thái kênh |
| `/bakhi chat bat:true` | Bật/tắt chat tự động |
| `/bakhi chance phan_tram:15` | Chỉnh % bot nhảy vào chat |
| `/bakhi trend tu:"..." nghia:"..."` | Dạy bot từ mới |
| `/bakhi unmute` | Gỡ cooldown ngay |

---

## 💻 Yêu cầu hệ thống

| Thành phần | Yêu cầu |
|------------|----------|
| Python | 3.10 trở lên |
| RAM | Tối thiểu 512MB |
| Mạng | Kết nối internet ổn định |
| API Key | Groq API Key (miễn phí) |

---

## 📥 Cài đặt và chạy

### Bước 1: Tải code

- [📥 **Tải file ZIP**](https://github.com/vVnK-wh0i4m/ba-khi-bot-server-discord-by-vVnK-wh0i4m/archive/refs/heads/main.zip)
- Hoặc clone: `git clone https://github.com/vVnK-wh0i4m/ba-khi-bot-server-discord-by-vVnK-wh0i4m.git`

### Bước 2: Vào thư mục

```bash
cd ba-khi-bot-server-discord-by-vVnK-wh0i4m
```

### Bước 3: Tạo virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### Bước 4: Cài đặt thư viện

```bash
pip install -r requirements.txt
```

### Bước 5: Cấu hình

Mở file `.env` và điền thông tin:

```env
DISCORD_TOKEN=ĐIỀN_DISCORD_TOKEN_VÀO_ĐÂY
GROQ_API_KEY=ĐIỀN_GROQ_API_KEY_VÀO_ĐÂY
```

> Xem thêm các trường cấu hình khác trong file `.env` bên dưới.

### Bước 6: Chạy bot

```bash
python bot.py
```

### Quan trọng

Vào [Discord Developer Portal](https://discord.com/developers/applications) → App của bạn → **Bot** → bật **MESSAGE CONTENT INTENT**.

Quyền mời bot: `View Channels`, `Send Messages`, `Read Message History`, `Embed Links`, `Add Reactions`, `Use Slash Commands`.

---

## ⚙️ Cấu hình

### File `.env`

Mở file `.env` và điền thông tin:

```env
# ============ BẮT BUỘC ============
DISCORD_TOKEN=ĐIỀN_DISCORD_TOKEN_VÀO_ĐÂY
GROQ_API_KEY=ĐIỀN_GROQ_API_KEY_VÀO_ĐÂY

# ============ MODEL ============
CHAT_MODEL=openai/gpt-oss-120b
GUARD_MODEL=meta-llama/llama-prompt-guard-2-86m
REASONING_EFFORT=low

# ============ RATE LIMIT ============
GUARD_RPM=30
GUARD_RPD=14400
GUARD_TPM=15000
GUARD_TPD=500000
CHAT_RPM=30
CHAT_RPD=1000
CHAT_TPM=8000
CHAT_TPD=200000
CHAT_MAX_WAIT=3.0
GUARD_MAX_WAIT=1.5

# ============ DANH TÍNH ============
BOT_NAME=bá khí bot
BOT_ALIASES=ba khi,bá khí,bakhibot,bó kí bot

# ============ CHAT TỰ ĐỘNG ============
AMBIENT_DEFAULT=true
REPLY_CHANCE=0.08
CHANNEL_COOLDOWN=25
MIN_LENGTH=4
MAX_HISTORY=6
REPLY_MAX_TOKENS=160
TEMPERATURE=0.95

# ============ LỌC KÊNH ============
ALLOW_CHANNELS=
DENY_CHANNELS=
ALLOW_DM=false

# ============ COOLDOWN ============
COOLDOWN_SECONDS=300
COUNTDOWN_INTERVAL=5
COOLDOWN_SCOPE=user
COMEBACK_ROAST=true
INSULT_REQUIRE_TARGET=true

# ============ PROMPT GUARD ============
GUARD_ENABLED=true
GUARD_ON_AMBIENT=false

# ============ DEV ============
DEV_GUILD_ID=
LOG_LEVEL=INFO
```

### Giải thích các trường chính

| Trường | Mô tả |
|--------|-------|
| `DISCORD_TOKEN` | Token bot Discord (Bot Token) |
| `GROQ_API_KEY` | API Key từ Groq (miễn phí) |
| `CHAT_MODEL` | Model AI chính để chat |
| `REASONING_EFFORT` | Mức độ suy luận: `low` / `medium` / `high` |
| `REPLY_CHANCE` | Xác suất bot tự nhảy vào chat (0.0 - 1.0) |
| `COOLDOWN_SCOPE` | Phạm vi cooldown: `user` / `channel` / `global` |

### Cách lấy API Key

**Discord Token:**
1. Vào https://discord.com/developers/applications
2. Tạo Application → Tab **Bot** → Copy **Token**

**Groq API Key:**
1. Vào https://console.groq.com
2. Đăng ký/đăng nhập → API Keys → Create API Key
3. Copy key

---

## 💬 Danh sách lệnh

| Lệnh | Quyền | Làm gì |
|-------|-------|--------|
| `/bakhi status` | Ai cũng được | Xem quota Groq, cooldown, trạng thái kênh |
| `/bakhi chat bat:true` | Manage Server | Bật/tắt chat tự động ở kênh hiện tại |
| `/bakhi chance phan_tram:15` | Manage Server | Chỉnh % bot tự nhảy vào chat |
| `/bakhi trend tu:"..." nghia:"..."` | Ai cũng được | Dạy bot từ mới, ghi vào `trends.json` |
| `/bakhi unmute` | Manage Server | Gỡ mọi cooldown ngay |

> Lần đầu chạy, slash command sync global có thể mất tới 1 tiếng. Điền `DEV_GUILD_ID` trong `.env` để sync tức thì.

---

## 📁 Cấu trúc dự án

```
ba-khi-bot/
├── bot.py              # Pipeline xử lý tin nhắn + slash commands
├── config.py           # Đọc .env, cấu hình
├── persona.py          # System prompt + từ điển trend
├── guard.py            # Regex bắt chửi + prompt-guard wrapper
├── cooldown.py         # Panel "lỗi kết nối" + đếm ngược
├── ratelimit.py        # RPM/RPD/TPM/TPD theo model
├── groq_api.py         # HTTP client async tới Groq
├── store.py            # Lưu toggle theo kênh
├── data/
│   ├── trigger_words.txt   # Từ khoá bắt chửi
│   ├── trends.json         # Từ điển trend
│   └── state/              # Runtime state
├── .env                # Secrets (gitignore)
├── .env.example        # Template cấu hình
├── requirements.txt    # Python dependencies
└── README.md
```

---

## 😤 Panel "mất kết nối"

Khi dính chửi, bot gửi embed đỏ rồi tự sửa mỗi 5 giây:

```
⚠️ MẤT KẾT NỐI TỚI MÁY CHỦ AI
[ERROR]  ERR_CONN_RESET_0x5F
[NODE ]  sea-gw-04
[STATE]  reconnecting…

⏳ Thử lại sau
01:33
▰▰▰▰▰▰▰▰▰▰▱▱▱▱ 69%

🔌 Dự kiến online
trong 1 phút nữa
```

**3 phạm vi cooldown:**

| Phạm vi | Hành vi |
|---------|---------|
| `user` | Chỉ im với riêng người chửi, trong kênh đó |
| `channel` | Im cả kênh |
| `global` | Im toàn server |

---

## 🔧 Chỉnh bot

| Muốn gì | Sửa ở đâu |
|---------|-----------|
| Giọng văn, mức độ khịa, ranh giới | `persona.py` |
| Từ điển trend, teencode | `data/trends.json` (hot-reload) |
| Từ khoá bắt chửi | `data/trigger_words.txt` |
| Tần suất, cooldown, rate limit | `.env` |

---

## ❓ Câu hỏi thường gặp

### Bot cần Python version nào?

Python 3.10 trở lên. Kiểm tra: `python --version`

### Lỗi `ModuleNotFoundError`?

Chạy: `pip install -r requirements.txt`

### Bot không hoạt động?

1. Token trong `.env` có hợp lệ không?
2. Groq API Key có đúng không?
3. Đã bật MESSAGE CONTENT INTENT chưa?

### Lỗi rate limit 429?

- Groq free tier: 30 RPM
- `ratelimit.py` tự phanh trước khi gửi
- Giảm `REPLY_CHANCE` hoặc tăng `CHANNEL_COOLDOWN`

---

## 📜 Bản quyền

**MIT License** - Xem file [LICENSE](LICENSE) để biết chi tiết.

| ✅ Được phép | ❌ Không được phép |
|-------------|-------------------|
| Giải trí cá nhân | Quấy rối người khác |
| Nghiên cứu, học tập | Spam, gây phiền |
| Quản lý server | Vi phạm pháp luật |

---

<div align="center">

**⭐ Star repo nếu thấy hữu ích! ⭐**

Made with ❤️ by vVnK

</div>
