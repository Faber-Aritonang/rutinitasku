# Product Requirements Document (PRD)

## RutinitasKu — Personal Task Automation Agent

| Field | Detail |
|-------|--------|
| **Nama Produk** | RutinitasKu |
| **Versi Dokumen** | 1.0 |
| **Tanggal** | 7 Oktober 2026 |
| **Author** | Jimmy (Product Owner) |
| **Status** | Draft |
| **Target Launch** | 8 minggu dari kickoff |

---

## 1. Executive Summary

**RutinitasKu** adalah sebuah personal assistant berbasis AI yang dapat mengotomasi berbagai tugas sehari-hari seperti mengelola email, menjadwalkan meeting, mencari informasi di web, dan mengelola file — semuanya melalui satu interface chat berbasis web.

Produk ini menggunakan **Anthropic Claude** sebagai LLM utama dengan **NaraRouter (Bynara)** sebagai fallback, memastikan ketersediaan layanan yang tinggi tanpa vendor lock-in ke satu provider AI.

---

## 2. Problem Statement

### 2.1 Masalah yang Dipecahkan

| No | Masalah | Dampak Saat Ini |
|----|---------|-----------------|
| 1 | **Context switching berlebihan** — pengguna harus bolak-balik antara email, calendar, browser, dan file manager | Waktu terbuang 30-60 menit/hari untuk tugas administratif |
| 2 | **Tidak ada satu titik kontrol** — setiap aplikasi punya UI dan logika berbeda | Cognitive load tinggi, rentan lupa/miss task |
| 3 | **Tidak ada memori kontekstual** — tools saat ini tidak ingat preferensi atau konteks percakapan sebelumnya | Pengguna harus mengulang instruksi berulang kali |
| 4 | **Barrier untuk otomasi** — tools otomasi existing (Zapier, Make) memerlukan setup kompleks dan berbayar | Pengguna individual/UMKM tidak terjangkau |

### 2.2 Target Users

| Persona | Deskripsi | Pain Point Utama |
|---------|-----------|------------------|
| **Profesional Individual** | Karyawan/konsultan yang handle banyak task harian | Ingin fokus pada pekerjaan strategis, bukan administratif |
| **Freelancer** | Butuh kelola klien, invoice, jadwal mandiri | Tidak punya asisten, budget terbatas |
| **Mahasiswa/Peneliti** | Riset intensif, kelola referensi, jadwal akademik | Butuh rangkuman cepat dari banyak sumber |
| **UMKM Owner** | Kelola operasional bisnis kecil | Tidak ada tim admin, butuh efisiensi |

---

## 3. Product Vision & Goals

### 3.1 Vision Statement

> *"Menjadi AI personal assistant yang paling terjangkau dan mudah diakses untuk pengguna berbahasa Indonesia, yang bisa di-hosting sendiri (self-hosted) dan tidak tergantung pada satu provider AI."*

### 3.2 Business Goals

| Goal | Metrik | Target |
|------|--------|--------|
| Mengurangi waktu tugas administratif | Waktu yang dihemat per hari | ≥ 30 menit/hari |
| Adoption | Active users dalam 3 bulan pertama | 50 users |
| User satisfaction | Rating kepuasan | ≥ 4.0/5.0 |
| Reliability | Uptime agent | ≥ 95% |
| Cost efficiency | Biaya LLM per user per bulan | ≤ $5/user |

### 3.3 Product Principles

1. **Sederhana dulu** — Mulai dari fitur yang paling sering dipakai, iterasi berdasarkan feedback
2. **Self-hosted & Private** — Data user tetap di infrastruktur sendiri, tidak dikirim ke pihak ketiga (kecuali LLM API)
3. **Multi-provider** — Tidak tergantung satu LLM; bisa switch antara Claude, NaraRouter, atau provider lain
4. **Bahasa Indonesia first** — UI dan interaksi utama dalam Bahasa Indonesia
5. **Free-tier friendly** — Semua dependency gratis atau punya free tier yang cukup

---

## 4. Scope

### 4.1 In Scope (v1.0)

| Module | Fitur | Priority |
|--------|-------|----------|
| **Chat Interface** | Chat UI dengan streaming response | P0 (Must) |
| **Chat Interface** | Riwayat percakapan per session | P0 |
| **Chat Interface** | Upload file (CSV, PDF, Excel, TXT) | P0 |
| **Web Research** | Search informasi via DuckDuckGo | P0 |
| **Web Research** | Scrape & rangkum halaman web | P0 |
| **File Management** | List, baca, tulis, hapus file (sandboxed) | P0 |
| **File Management** | Analisis CSV/Excel (statistik, filter) | P1 (Should) |
| **Email** | Baca email via IMAP | P1 |
| **Email** | Kirim email via SMTP | P1 |
| **Calendar** | Lihat jadwal Google Calendar | P1 |
| **Calendar** | Buat/hapus event di Google Calendar | P1 |
| **Memory** | Simpan & recall percakapan | P0 |
| **Memory** | Ingat fakta/preferensi user | P1 |
| **Reminder** | Set pengingat berbasis waktu | P1 |
| **LLM Layer** | Claude API sebagai primary | P0 |
| **LLM Layer** | NaraRouter sebagai fallback | P0 |
| **LLM Layer** | Auto-fallback jika primary gagal | P1 |
| **Dashboard** | Ringkasan aktivitas hari ini | P2 (Nice to have) |
| **Settings** | Konfigurasi API keys via UI | P1 |

### 4.2 Out of Scope (v1.0)

| Fitur | Alasan | Rencana |
|-------|--------|---------|
| Multi-user / team collaboration | Kompleksitas auth & permission | v2.0 |
| Mobile app native | Fokus web dulu | v2.0 |
| Voice input/output | Butuh STT/TTS integration | v2.0 |
| Plugin marketplace | Butuh infrastruktur tambahan | v3.0 |
| WhatsApp/Telegram integration | Butuh approval & infra messaging | v2.0 |
| Image generation | Bukan core task automation | v2.0 (via NaraRouter) |
| Auto-invoice / accounting | Domain spesifik, butuh validasi | v3.0 |

---

## 5. Functional Requirements

### 5.1 FR-CHAT: Chat Interface

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| FR-CHAT-01 | User dapat mengirim pesan teks ke agent | Pesan terkirim, response muncul dalam ≤ 10 detik |
| FR-CHAT-02 | Response ditampilkan secara streaming (token by token) | User melihat response bertahap, bukan sekaligus |
| FR-CHAT-03 | User dapat mengupload file melalui chat | File tersimpan di server, agent bisa akses isinya |
| FR-CHAT-04 | Riwayat percakapan tersimpan per session | User bisa melanjutkan percakapan setelah refresh |
| FR-CHAT-05 | User dapat membuat session baru | Session baru dimulai dengan konteks kosong |
| FR-CHAT-06 | Support multi-line input | User bisa shift+enter untuk baris baru |

### 5.2 FR-LLM: LLM Layer

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| FR-LLM-01 | Menggunakan Anthropic Claude Messages API | Response berhasil dengan model claude-sonnet-4-20250514 |
| FR-LLM-02 | Fallback ke NaraRouter jika Claude gagal | Ketika Claude error, otomatis retry via NaraRouter |
| FR-LLM-03 | Support function calling / tool use | Agent bisa memanggil tools yang terdaftar |
| FR-LLM-04 | Support streaming response | Token dikirim ke UI secara real-time |
| FR-LLM-05 | Konfigurasi model bisa diubah via .env | User bisa ganti model tanpa ubah kode |

### 5.3 FR-WEB: Web Research

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| FR-WEB-01 | Search informasi via DuckDuckGo | Mengembalikan top 5-10 hasil dengan title, URL, snippet |
| FR-WEB-02 | Scrape konten halaman web | Ekstraksi teks bersih dari URL yang diberikan |
| FR-WEB-03 | Rangkuman otomatis dari hasil search | Agent merangkum informasi relevan dari beberapa sumber |
| FR-WEB-04 | Support search dalam Bahasa Indonesia dan Inggris | Query dalam bahasa apapun menghasilkan hasil relevan |

### 5.4 FR-FILE: File Management

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| FR-FILE-01 | List file dalam direktori yang diizinkan | Menampilkan nama, ukuran, tanggal modifikasi |
| FR-FILE-02 | Baca isi file teks (TXT, MD, JSON, CSV) | Konten file ditampilkan/diproses |
| FR-FILE-03 | Baca PDF dan ekstrak teks | Teks dari PDF bisa dibaca agent |
| FR-FILE-04 | Baca Excel (XLSX) dan konversi ke tabel | Data Excel bisa dianalisis |
| FR-FILE-05 | Analisis CSV — statistik deskriptif, filter, sorting | Agent bisa jawab pertanyaan tentang data CSV |
| FR-FILE-06 | Operasi file dasar (copy, move, rename, delete) | Operasi berhasil dengan konfirmasi sebelum delete |
| FR-FILE-07 | Semua operasi file di-sandbox ke folder tertentu | Tidak bisa akses di luar sandbox |

### 5.5 FR-EMAIL: Email Management

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| FR-EMAIL-01 | Koneksi ke mailbox via IMAP | Berhasil koneksi dengan credential yang valid |
| FR-EMAIL-02 | Baca email terbaru (filter by sender, date, subject) | Menampilkan daftar email sesuai filter |
| FR-EMAIL-03 | Baca isi email lengkap | Teks email ditampilkan utuh |
| FR-EMAIL-04 | Kirim email via SMTP | Email terkirim dengan subject, body, attachment |
| FR-EMAIL-05 | Credential disimpan aman di .env | Tidak hardcode di source code |

### 5.6 FR-CAL: Calendar Management

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| FR-CAL-01 | Autentikasi Google Calendar via OAuth2 | Flow OAuth2 berhasil, token tersimpan |
| FR-CAL-02 | Lihat event hari ini / minggu ini / tanggal tertentu | Daftar event ditampilkan dengan waktu & deskripsi |
| FR-CAL-03 | Buat event baru | Event muncul di Google Calendar |
| FR-CAL-04 | Update event existing | Perubahan tersimpan di Google Calendar |
| FR-CAL-05 | Hapus event | Event dihapus dengan konfirmasi |

### 5.7 FR-MEM: Memory System

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| FR-MEM-01 | Simpan semua percakapan ke SQLite | Percakapan bisa di-retrieve berdasarkan session |
| FR-MEM-02 | Recall percakapan sebelumnya | Agent bisa merujuk percakapan lama saat ditanya |
| FR-MEM-03 | Simpan fakta/preferensi user | "Ingat: saya lebih suka format bullet point" → tersimpan |
| FR-MEM-04 | Gunakan fakta tersimpan dalam response | Agent otomatis pakai preferensi yang pernah disebut |
| FR-MEM-05 | Hapus history session | User bisa bersihkan riwayat percakapan |

### 5.8 FR-REM: Reminder System

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| FR-REM-01 | Set reminder dengan waktu spesifik | Notifikasi muncul pada waktu yang ditentukan |
| FR-REM-02 | Set reminder berbasis durasi | "Ingatkan saya dalam 2 jam" → trigger setelah 2 jam |
| FR-REM-03 | Reminder persist setelah restart | Reminder tersimpan di DB, aktif setelah app restart |
| FR-REM-04 | List semua reminder aktif | User bisa lihat semua reminder yang belum trigger |

---

## 6. Non-Functional Requirements

### 6.1 NFR-PERF: Performance

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-PERF-01 | Response time (first token) | ≤ 3 detik |
| NFR-PERF-02 | Tool execution time (rata-rata) | ≤ 5 detik |
| NFR-PERF-03 | File upload max size | 50 MB |
| NFR-PERF-04 | Concurrent sessions | ≥ 5 sessions bersamaan |
| NFR-PERF-05 | Memory usage server | ≤ 512 MB RAM |

### 6.2 NFR-SEC: Security

| ID | Requirement | Detail |
|----|-------------|--------|
| NFR-SEC-01 | API key tidak diekspos ke client | Key di server-side .env, tidak dikirim ke browser |
| NFR-SEC-02 | File access di-sandbox | Operasi file hanya di `data/uploads/` dan `data/workspace/` |
| NFR-SEC-03 | Email credential terenkripsi | App password di .env, tidak di log |
| NFR-SEC-04 | Input sanitization | Semua input user di-validate sebelum diproses |
| NFR-SEC-05 | Rate limiting | Maks 30 request/menit per session |

### 6.3 NFR-REL: Reliability

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-REL-01 | Uptime (self-hosted) | ≥ 95% (bergantung infra user) |
| NFR-REL-02 | Graceful degradation saat LLM down | Tampilkan pesan error yang jelas, bukan crash |
| NFR-REL-03 | Auto-retry dengan fallback | Jika Claude gagal → NaraRouter → error message |
| NFR-REL-04 | Data persistence | Percakapan & reminder survive restart |

### 6.4 NFR-USA: Usability

| ID | Requirement | Detail |
|----|-------------|--------|
| NFR-USA-01 | Setup time | ≤ 15 menit dari clone ke running |
| NFR-USA-02 | Responsive UI | Berfungsi di desktop dan mobile browser |
| NFR-USA-03 | Bahasa Indonesia default | UI dan system prompt dalam Bahasa Indonesia |
| NFR-USA-04 | Error messages informatif | User tahu apa yang salah dan bagaimana memperbaiki |
| NFR-USA-05 | Documentation lengkap | README dengan setup guide, contoh penggunaan |

### 6.5 NFR-MAINT: Maintainability

| ID | Requirement | Detail |
|----|-------------|--------|
| NFR-MAINT-01 | Modular architecture | Setiap tool adalah module terpisah, mudah ditambah/hapus |
| NFR-MAINT-02 | Type hints | Semua fungsi menggunakan Python type hints |
| NFR-MAINT-03 | Logging | Structured logging untuk debugging |
| NFR-MAINT-04 | Tests | Coverage minimal 60% untuk core modules |

---

## 7. Technical Architecture

### 7.1 System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    USER (Browser)                         │
└─────────────────────────┬────────────────────────────────┘
                          │ HTTP/WebSocket
┌─────────────────────────▼────────────────────────────────┐
│                    GRADIO WEB UI                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │   Chat   │ │  Tasks   │ │  Files   │ │ Settings │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
└─────────────────────────┬────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────┐
│                  AGENT ORCHESTRATOR                        │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  LLM Layer   │  │  Tool Router │  │    Memory    │    │
│  │              │  │              │  │              │    │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │    │
│  │ │  Claude  │ │  │ │ Registry │ │  │ │ SQLite   │ │    │
│  │ │  API     │ │  │ │          │ │  │ │ DB       │ │    │
│  │ ├──────────┤ │  │ │ dispatch │ │  │ │          │ │    │
│  │ │ NaraRtr  │ │  │ │ validate │ │  │ │ sessions │ │    │
│  │ │ (fallback)│ │  │ └──────────┘ │  │ │ facts    │ │    │
│  │ └──────────┘ │  └──────────────┘  │ │ reminders│ │    │
│  └──────────────┘                    │ └──────────┘ │    │
│                                      └──────────────┘    │
└─────────────────────────┬────────────────────────────────┘
                          │
        ┌─────────┬───────┼────────┬─────────┬──────────┐
        ▼         ▼       ▼        ▼         ▼          ▼
   ┌────────┐┌────────┐┌──────┐┌────────┐┌────────┐┌────────┐
   │ Email  ││Calendar││ Web  ││  File  ││  CSV   ││Reminder│
   │ (IMAP/ ││(Google ││Search││Manager ││Analyzer││        │
   │  SMTP) ││Calendar││(DDG) ││        ││        ││        │
   └────────┘└────────┘└──────┘└────────┘└────────┘└────────┘
        │         │       │        │         │          │
        ▼         ▼       ▼        ▼         ▼          ▼
   ┌────────┐┌────────┐┌──────┐┌────────┐┌────────┐┌────────┐
   │ Email  ││Google  ││Inter-││ Local  ││ Local  ││ SQLite │
   │ Server ││API     ││net   ││ Filesys││ Files  ││   DB   │
   └────────┘└────────┘└──────┘└────────┘└────────┘└────────┘
```

### 7.2 Data Model (SQLite)

```sql
-- Tabel percakapan
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,          -- 'user' | 'assistant' | 'system'
    content TEXT NOT NULL,
    tool_calls TEXT,             -- JSON: tool calls made
    tool_results TEXT,           -- JSON: tool results received
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel fakta/preferensi user
CREATE TABLE facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,    -- e.g., 'preferred_format'
    value TEXT NOT NULL,         -- e.g., 'bullet points'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel reminder
CREATE TABLE reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT NOT NULL,
    trigger_at TIMESTAMP NOT NULL,
    is_triggered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel task log
CREATE TABLE task_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    input_params TEXT,           -- JSON
    output_result TEXT,          -- JSON
    status TEXT NOT NULL,        -- 'success' | 'error'
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 7.3 LLM Integration

```python
# Dual-provider pattern
class LLMLayer:
    async def chat(self, messages, tools=None):
        try:
            # Primary: Anthropic Claude
            return await self._call_claude(messages, tools)
        except (APIError, TimeoutError) as e:
            logger.warning(f"Claude failed: {e}, falling back to NaraRouter")
            try:
                # Fallback: NaraRouter (OpenAI-compatible)
                return await self._call_nararouter(messages, tools)
            except Exception as e2:
                logger.error(f"NaraRouter also failed: {e2}")
                raise LLMUnavailableError("Semua LLM provider gagal")
```

### 7.4 Tool Definition Format

```python
# Tools didefinisikan sebagai JSON Schema untuk function calling
TOOLS = [
    {
        "name": "web_search",
        "description": "Cari informasi di internet menggunakan DuckDuckGo",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Kata kunci pencarian"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Jumlah hasil maksimal (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    # ... tools lainnya
]
```

---

## 8. Project Timeline & Milestones

### 8.1 Milestone Overview

```
Week 1-2     Week 3-4     Week 5-6     Week 7       Week 8
┌───────────┬───────────┬───────────┬───────────┬───────────┐
│  Phase 1  │  Phase 2  │  Phase 3  │  Phase 4  │  Phase 5  │
│Foundation │Core Tools │  Agent    │  Web UI   │  Testing  │
│           │           │  Engine   │  (Gradio) │  & Polish │
└───────────┴───────────┴───────────┴───────────┴───────────┘
    M1           M2          M3          M4          M5
```

### 8.2 Detailed Milestones

| Milestone | Week | Deliverables | Definition of Done |
|-----------|------|-------------|-------------------|
| **M1: Foundation** | 1-2 | Project setup, LLM layer, Memory system, Config | Bisa kirim chat ke Claude & NaraRouter, percakapan tersimpan di SQLite |
| **M2: Core Tools** | 3-4 | Web search, File manager, CSV analyzer | Agent bisa search web, baca file, analisis CSV via tool calling |
| **M3: Agent Engine** | 5-6 | Orchestrator, Planner, Email tool, Calendar tool | Agent bisa execute multi-step task, baca email, kelola calendar |
| **M4: Web UI** | 7 | Gradio interface dengan semua tab | Bisa diakses via browser, semua fitur terintegrasi |
| **M5: Launch** | 8 | Testing, bug fixes, documentation | Semua test pass, README lengkap, demo video |

### 8.3 Sprint Breakdown

#### Sprint 1 (Week 1): Project Setup & LLM Layer
- [ ] Initialize project structure
- [ ] Setup `.env` configuration
- [ ] Implement `config.py`
- [ ] Implement `agent/llm.py` — Claude API integration
- [ ] Implement `agent/llm.py` — NaraRouter integration
- [ ] Implement `agent/llm.py` — Auto-fallback logic
- [ ] Unit tests untuk LLM layer

#### Sprint 2 (Week 2): Memory & System Prompt
- [ ] Implement `agent/memory.py` — SQLite schema & CRUD
- [ ] Implement `agent/prompt.py` — System prompts Bahasa Indonesia
- [ ] Implement conversation history management
- [ ] Implement facts/preferences storage
- [ ] Unit tests untuk memory system

#### Sprint 3 (Week 3): Web & File Tools
- [ ] Implement `tools/registry.py` — Tool registration pattern
- [ ] Implement `tools/web_search.py` — DuckDuckGo integration
- [ ] Implement `tools/web_scrape.py` — httpx + BeautifulSoup
- [ ] Implement `tools/file_manager.py` — Sandboxed file ops
- [ ] Implement `tools/csv_analyzer.py` — Pandas-based analysis
- [ ] Unit tests untuk semua tools

#### Sprint 4 (Week 4): Email & Calendar Tools
- [ ] Implement `tools/email_tool.py` — IMAP read
- [ ] Implement `tools/email_tool.py` — SMTP send
- [ ] Implement `tools/calendar_tool.py` — Google OAuth2 flow
- [ ] Implement `tools/calendar_tool.py` — Calendar CRUD
- [ ] Implement `tools/reminder.py` — Time-based reminders
- [ ] Integration tests

#### Sprint 5 (Week 5): Agent Orchestrator
- [ ] Implement `agent/planner.py` — Task decomposition
- [ ] Implement `agent/orchestrator.py` — Main agent loop
- [ ] Implement tool execution pipeline
- [ ] Implement error handling & retry logic
- [ ] End-to-end test: chat → tool call → response

#### Sprint 6 (Week 6): Agent Refinement
- [ ] Implement multi-step task handling
- [ ] Implement context window management
- [ ] Implement conversation summarization (untuk long sessions)
- [ ] Implement graceful degradation
- [ ] Performance testing & optimization

#### Sprint 7 (Week 7): Gradio Web UI
- [ ] Implement `app.py` — Chat tab
- [ ] Implement `app.py` — Tasks tab
- [ ] Implement `app.py` — Files tab
- [ ] Implement `app.py` — Settings tab
- [ ] Implement `app.py` — Dashboard tab
- [ ] Responsive design testing
- [ ] Stream integration dengan agent

#### Sprint 8 (Week 8): Testing, Polish & Launch
- [ ] End-to-end testing semua fitur
- [ ] Bug fixes dari testing
- [ ] Write `README.md` — setup guide
- [ ] Write `README.md` — usage examples
- [ ] Create demo video / screenshots
- [ ] Tag release v1.0.0

---

## 9. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Claude API rate limit / downtime** | Medium | High | NaraRouter sebagai fallback; implement retry with exponential backoff |
| **NaraRouter compatibility issues** | Low | Medium | Abstract LLM layer; unit test kedua provider |
| **Google Calendar OAuth2 complexity** | Medium | Medium | Gunakan service account sebagai alternativ; buat guide step-by-step |
| **Email provider blocks IMAP** | Low | Medium | Support multiple provider settings; dokumentasikan app password setup |
| **SQLite corruption** | Low | High | Regular backup ke file terpisah; WAL mode untuk concurrent access |
| **Memory leak / high resource usage** | Medium | Medium | Implement session cleanup; limit conversation history window |
| **Scope creep** | High | High | Strict prioritization (P0/P1/P2); defer fitur non-essential ke v2.0 |
| **Security vulnerability (file access)** | Medium | High | Strict sandboxing; path traversal prevention; input validation |

---

## 10. Success Metrics

### 10.1 Key Performance Indicators (KPIs)

| KPI | Metode Pengukuran | Target v1.0 |
|-----|------------------|-------------|
| **Task completion rate** | % task yang berhasil diselesaikan agent | ≥ 80% |
| **Response latency (P95)** | Waktu dari user input ke first token | ≤ 3 detik |
| **Tool execution success rate** | % tool call yang berhasil | ≥ 90% |
| **User satisfaction** | Survey rating | ≥ 4.0/5.0 |
| **Daily active sessions** | Jumlah session unik per hari | ≥ 10 (bulan pertama) |
| **LLM fallback rate** | % request yang pakai NaraRouter | ≤ 20% |
| **Setup time** | Waktu dari clone ke first chat | ≤ 15 menit |

### 10.2 Monitoring & Observability

| Signal | Tool | Alert Threshold |
|--------|------|-----------------|
| API error rate | `task_log` table | > 10% error dalam 5 menit |
| Response latency | `task_log.duration_ms` | P95 > 10 detik |
| LLM fallback rate | Log analysis | > 30% dalam 1 jam |
| Disk usage | `data/` directory size | > 1 GB |
| Memory usage | Process monitoring | > 512 MB |

---

## 11. Dependencies & Constraints

### 11.1 External Dependencies

| Dependency | Type | Risk Level | Fallback |
|------------|------|-----------|----------|
| Anthropic Claude API | LLM | Medium | NaraRouter |
| NaraRouter (Bynara) | LLM Router | Low | Direct Claude API |
| DuckDuckGo | Web Search | Low | Manual URL scrape |
| Google Calendar API | Calendar | Medium | Local SQLite calendar |
| Email Server (IMAP/SMTP) | Email | Low | N/A — user provides credentials |

### 11.2 Constraints

| Constraint | Detail |
|------------|--------|
| **Budget** | $0 infrastructure cost (self-hosted, free tools only) |
| **Team** | 1 developer (solo project) |
| **Timeline** | 8 minggu untuk v1.0 |
| **Hosting** | Lokal (user's machine) atau VPS gratis tier |
| **Language** | Python 3.11+ |
| **UI Framework** | Gradio (free, open source) |

---

## 12. Open Questions

| No | Question | Owner | Status |
|----|----------|-------|--------|
| 1 | Apakah NaraRouter mendukung Anthropic Messages API format? (docs bilang ya) | Dev | Perlu verifikasi saat implementasi |
| 2 | Google Calendar: personal account atau workspace? | PO | Pending decision |
| 3 | Apakah perlu support multiple email accounts? | PO | Defer ke v2.0 |
| 4 | Berapa max context window yang akan dipakai? | Dev | Tergantung model yang dipilih |
| 5 | Apakah perlu Docker containerization untuk v1.0? | PO | Nice to have, defer ke v1.1 |

---

## 13. Appendix

### A. API Reference

| API | Documentation URL |
|-----|------------------|
| Anthropic Messages API | https://docs.anthropic.com/en/api/messages |
| NaraRouter API | https://router.bynara.id/docs |
| Google Calendar API | https://developers.google.com/calendar/api |
| DuckDuckGo Search | https://github.com/deedy5/duckduckgo_search |

### B. Glossary

| Term | Definition |
|------|-----------|
| **Agent** | Sistem AI yang bisa menggunakan tools untuk menyelesaikan task |
| **LLM** | Large Language Model — model bahasa besar (Claude, GPT, dll.) |
| **Tool Calling** | Kemampuan LLM untuk memanggil fungsi eksternal |
| **RAG** | Retrieval-Augmented Generation — mengambil konteks dari database sebelum generate |
| **ReAct** | Reasoning + Acting — pattern agent: pikir → act → observasi → ulangi |
| **Sandbox** | Lingkungan terisolasi yang membatasi akses agent |
| **Streaming** | Mengirim response token-by-token, bukan sekaligus |
| **Fallback** | Mekanisme cadangan jika provider utama gagal |
| **OAuth2** | Protokol autentikasi standar untuk akses API pihak ketiga |

### C. File Structure

```
task-automation-agent/
├── PRD.md                    # Dokumen ini
├── README.md                 # Setup & usage guide
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
│   ├── planner.py            # Task decomposition
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
│   ├── memory.db             # SQLite database
│   ├── uploads/              # User uploaded files
│   └── workspace/            # Agent workspace
│
└── tests/
    ├── test_llm.py
    ├── test_memory.py
    ├── test_tools.py
    ├── test_agent.py
    └── conftest.py
```

---

*Document generated on 2026-10-07. Review and update after each milestone.*