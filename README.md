# 🤖 NaraTask AI

**Personal Task Automation Agent**

NaraTask AI adalah asisten personal berbasis AI yang membantu mengotomasi tugas sehari-hari seperti web research, email, calendar, dan file management — semuanya melalui satu interface chat.

## ✨ Fitur

| Fitur | Deskripsi |
|-------|-----------|
| 🌐 **Web Research** | Cari informasi di internet, rangkum artikel |
| 📧 **Email** | Baca dan kirim email via IMAP/SMTP |
| 📅 **Calendar** | Kelola Google Calendar (lihat, buat, hapus event) |
| 📁 **File Management** | Kelola file dalam workspace (baca, tulis, analisis) |
| 📊 **Data Analysis** | Analisis CSV/Excel dengan statistik deskriptif |
| ⏰ **Reminder** | Atur pengingat berbasis waktu |
| 💾 **Memory** | Ingat percakapan dan preferensi user |

## 🛠️ Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| **Language** | Python 3.11+ |
| **Web UI** | Gradio 4.x |
| **LLM Primary** | Anthropic Claude API |
| **LLM Fallback** | NaraRouter (Bynara) |
| **Database** | SQLite + aiosqlite |
| **Email** | smtplib + imaplib (stdlib) |
| **Calendar** | Google Calendar API |
| **Web Search** | DuckDuckGo Search |
| **Web Scraping** | httpx + BeautifulSoup4 |

## 🚀 Quick Start

### 1. Clone Repository

```bash
cd task-automation-agent
```

### 2. Setup Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# atau
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` dan isi API keys:

```env
# Minimal: salah satu harus diisi
ANTHROPIC_API_KEY=sk-ant-xxx-your-key
NARAROUTER_API_KEY=sk-nry-xxx-your-key
```

### 5. Run Application

```bash
python app.py
```

Buka browser di `http://localhost:7860`

## 📁 Struktur Project

```
task-automation-agent/
├── PRD.md                    # Product Requirements Document
├── README.md                 # Dokumen ini
├── requirements.txt          # Python dependencies
├── .env.example              # Template environment variables
├── app.py                    # Entry point — Gradio UI
├── config.py                 # Konfigurasi & env vars
│
├── agent/
│   ├── __init__.py
│   ├── orchestrator.py       # Agent loop utama
│   ├── llm.py                # LLM abstraction (Claude + NaraRouter)
│   ├── memory.py             # Conversation & long-term memory
│   └── prompt.py             # System prompts
│
├── tools/
│   ├── __init__.py
│   ├── registry.py           # Tool registry & dispatcher
│   ├── email_tool.py         # Email (IMAP/SMTP)
│   ├── calendar_tool.py      # Google Calendar
│   ├── web_search.py         # DuckDuckGo search
│   ├── web_scrape.py         # Web scraping
│   ├── file_manager.py       # File operations
│   ├── csv_analyzer.py       # CSV/Excel analysis
│   └── reminder.py           # Reminder system
│
├── data/
│   ├── memory.db             # SQLite database (auto-created)
│   ├── uploads/              # User uploaded files
│   └── workspace/            # Agent workspace
│
└── tests/
    ├── test_llm.py
    ├── test_memory.py
    └── test_tools.py
```

## ⚙️ Konfigurasi Detail

### Anthropic Claude API

1. Daftar di [Anthropic Console](https://console.anthropic.com)
2. Buat API Key
3. Set di `.env`: `ANTHROPIC_API_KEY=sk-ant-xxx`

### NaraRouter (Fallback)

1. Daftar di [router.bynara.id](https://router.bynara.id)
2. Buat API Key (prefix: `sk-nry-`)
3. Set di `.env`: `NARAROUTER_API_KEY=sk-nry-xxx`

### Email (Gmail)

1. Aktifkan 2FA di Google Account
2. Buat App Password: [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Set di `.env`:
   ```
   EMAIL_ADDRESS=your-email@gmail.com
   EMAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx
   ```

### Google Calendar

1. Buka [Google Cloud Console](https://console.cloud.google.com)
2. Buat project baru
3. Enable Google Calendar API
4. Buat OAuth 2.0 credentials
5. Download sebagai `credentials.json`
6. Letakkan di folder project

## 🧪 Testing

```bash
# Jalankan semua test
pytest

# Jalankan test spesifik
pytest tests/test_memory.py

# Jalankan dengan verbose
pytest -v
```

## 📝 Contoh Penggunaan

### Web Research
```
User: Cari informasi tentang tren AI 2026
Agent: [mencari di web dan merangkum hasilnya]
```

### Email
```
User: Baca email terbaru dari Pak Budi
Agent: [mengakses inbox dan menampilkan email]
```

### Calendar
```
User: Jadwalkan meeting besok jam 2 siang
Agent: [membuat event di Google Calendar]
```

### File Analysis
```
User: Analisis data penjualan di file sales.csv
Agent: [membaca CSV dan menampilkan statistik]
```

### Reminder
```
User: Ingatkan saya jam 3 sore untuk follow up klien
Agent: Reminder diatur untuk jam 15:00
```

## 🔧 Troubleshooting

### "No LLM provider available"
- Pastikan minimal satu API key diisi di `.env`
- Cek apakah API key valid

### "Email configuration missing"
- Pastikan `EMAIL_ADDRESS` dan `EMAIL_PASSWORD` di `.env`
- Untuk Gmail, gunakan App Password, bukan password biasa

### "Google Calendar credentials not found"
- Pastikan file `credentials.json` ada di folder project
- Ikuti panduan Google Calendar di atas

## 📄 License

MIT License

## 🙏 Credits

- **Anthropic** - Claude API
- **NaraRouter (Bynara)** - LLM Router
- **Gradio** - Web UI Framework
- **DuckDuckGo** - Web Search

---

**Made with ❤️ for productivity**