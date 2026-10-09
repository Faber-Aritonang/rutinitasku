"""
RutinitasKu - Main Application
Gradio-based web interface for the task automation agent.

Layout note
-----------
The page follows a marketplace / product-detail layout:
  top bar (brand + search + primary action)  ->  nav tabs  ->  breadcrumb
  ->  wide "preview" panel (chat) + info & CTA sidebar.
Only the presentation lives here; the agent logic is untouched.
"""

import asyncio
import logging
import uuid
from datetime import datetime

import gradio as gr

from config import HOST, PORT, DEBUG, validate_config
from agent.orchestrator import AgentOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator = None


# =============================================================================
# Layout — static markup for the decorative parts of the shell
# =============================================================================

BRAND_HTML = """
<div class="rk-brand">
    <span class="rk-brand-mark">🤖</span>
    <span class="rk-brand-name">Rutinitas<span class="rk-brand-accent">Ku</span></span>
</div>
"""

AVATAR_HTML = '<div class="rk-avatar">👤</div>'

PANEL_HEAD_HTML = """
<div class="rk-panel-head">
    <div class="rk-panel-brand">🤖 RutinitasKu</div>
    <p class="rk-panel-sub">Personal Task Automation Assistant</p>
</div>
"""

SIDEBAR_HEAD_HTML = """
<div class="rk-side-head">
    <h1 class="rk-title">RutinitasKu — Personal Task Automation Assistant</h1>
    <p class="rk-by">Oleh <b>Jimmy</b></p>
</div>
"""

CARD_HTML = """
<div class="rk-card-body">
    <h3>Semua fitur inti, tersedia tanpa biaya langganan</h3>
    <ul class="rk-features">
        <li>Web research &amp; rangkuman otomatis dari banyak sumber</li>
        <li>Kelola file, PDF, dan analisis CSV langsung dari chat</li>
        <li>Baca &amp; kirim email serta atur Google Calendar</li>
        <li>Memory kontekstual dan reminder pintar</li>
    </ul>
</div>
"""

SIGNIN_HTML = '<p class="rk-signin">Sudah punya akun? <a href="#">Masuk</a></p>'

CUSTOM_CSS = """
/* =========================================================================
   RutinitasKu — design tokens
   ========================================================================= */
:root {
    --rk-green: #00cf7f;
    --rk-green-dark: #00ba71;
    --rk-ink: #14151b;
    --rk-muted: #6b6f7b;
    --rk-border: #e4e6ec;
    --rk-page: #f6f7f9;
    --rk-dark: #0f1116;
}

html, body, .gradio-container {
    background: var(--rk-page) !important;
    color: var(--rk-ink) !important;
    font-family: "Inter", "Segoe UI", ui-sans-serif, system-ui, -apple-system, sans-serif;
}
/* full-bleed bars must never create a horizontal scrollbar */
body { overflow-x: hidden !important; }
.gradio-container .main { padding-top: 0 !important; padding-bottom: 0 !important; }
.gradio-container {
    --font: "Inter", "Segoe UI", ui-sans-serif, system-ui, -apple-system, sans-serif;
    font-family: var(--font) !important;
    max-width: 1340px !important;
    margin: 0 auto !important;
    padding: 0 24px 64px !important;
}
/* Gradio clips the container, which would cut off the full-bleed bars */
.gradio-container { overflow: visible !important; }
.gradio-container .main,
.gradio-container .wrap,
.gradio-container .contain { background: transparent !important; }
footer { display: none !important; }

/* Decorative HTML blocks lose their default card chrome */
.rk-plain, .rk-plain.block, .rk-plain .block, .rk-plain .html-container,
.rk-plain .prose {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* =========================================================================
   Top bar — brand | search | primary action
   ========================================================================= */
.rk-topbar {
    align-items: center !important;
    gap: 14px !important;
    flex-wrap: nowrap !important;
    background: #fff !important;
    border-bottom: 1px solid var(--rk-border) !important;
    /* bleed the bar to the viewport edges while keeping content aligned */
    width: calc(100% + 2 * (50vw - 50%)) !important;
    margin-left: calc(50% - 50vw) !important;
    margin-right: calc(50% - 50vw) !important;
    padding: 0 calc(50vw - 50%) !important;
    height: 69px !important;
    /* close the 16px layout gap so the bar meets the nav below it */
    margin-bottom: -16px !important;
    position: sticky;
    top: 0;
    z-index: 60;
}
.rk-topbar .block, .rk-topbar .form, .rk-topbar .html-container {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}

.rk-brand-cell { min-width: 200px !important; flex-shrink: 0 !important; }
.rk-avatar-cell { min-width: 52px !important; flex-shrink: 0 !important; }
.rk-search-cell { min-width: 240px !important; }
.rk-brand { display: flex; align-items: center; gap: 11px; }
.rk-brand-mark {
    flex-shrink: 0 !important;
    width: 38px; height: 38px; border-radius: 10px;
    background: var(--rk-green); color: #06281c;
    display: flex; align-items: center; justify-content: center;
    font-size: 19px;
}
.rk-brand-name {
    font-size: 21px; font-weight: 800; letter-spacing: -0.02em;
    color: var(--rk-ink); line-height: 1; white-space: nowrap;
}
.rk-brand-accent { color: var(--rk-green-dark); }
.rk-avatar {
    width: 38px; height: 38px; border-radius: 50%;
    background: #eef0f4; border: 1px solid var(--rk-border); color: var(--rk-muted);
    display: flex; align-items: center; justify-content: center; font-size: 17px;
}

/* Search pill (mirrors the reference search field) */
.rk-search, .rk-search label {
    display: flex !important;
    align-items: center !important;
}
.rk-search label { width: 100% !important; }
.rk-search .input-container { flex: 1 1 auto !important; width: 100% !important; }
.rk-search input, .rk-search textarea {
    width: 100% !important;
    height: 44px !important;
    min-height: 44px !important;
    border-radius: 999px !important;
    border: 1px solid var(--rk-border) !important;
    background-color: #fff !important;
    color: var(--rk-ink) !important;
    font-size: 14.5px !important;
    padding: 0 18px 0 44px !important;
    background-image: url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%236b6f7b' stroke-width='2' stroke-linecap='round'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='M20.5 20.5L16.7 16.7'/%3E%3C/svg%3E") !important;
    background-repeat: no-repeat !important;
    background-position: 16px center !important;
    background-size: 17px 17px !important;
    box-shadow: 0 1px 2px rgba(16, 18, 24, 0.04) !important;
}
.rk-search input::placeholder, .rk-search textarea::placeholder { color: #9aa0ad !important; }

.rk-pill, .rk-pill .wrap, .rk-pill .wrap-inner, .rk-pill input,
.rk-pill .secondary-wrap, .rk-pill .token {
    border-radius: 999px !important;
    background: #fff !important;
    border-color: var(--rk-border) !important;
    color: var(--rk-ink) !important;
    opacity: 1 !important;
}
.rk-pill input { height: 44px !important; font-size: 14.5px !important; padding: 0 16px !important; }

/* =========================================================================
   Nav tabs — the marketplace menu row
   ========================================================================= */
.rk-tabs {
    background: #fff !important;
    width: calc(100% + 2 * (50vw - 50%)) !important;
    margin-left: calc(50% - 50vw) !important;
    margin-right: calc(50% - 50vw) !important;
    padding: 0 calc(50vw - 50%) !important;
    --border-color-primary: var(--rk-border);
    position: sticky;
    top: 69px;
    z-index: 55;
}
/* Gradio fixes the nav wrapper height below the buttons, which would make the
   nav overlap the page content — give it the real height instead. */
.rk-tabs .tab-wrapper {
    height: 54px !important;
    padding-bottom: 0 !important;
    margin-bottom: 0 !important;
}
.rk-tabs .tab-container, .rk-tabs .tab-nav {
    gap: 30px !important;
    height: 54px !important;
    background: transparent !important;
}
.rk-tabs .tab-container > button, .rk-tabs .tab-nav > button {
    background: transparent !important;
    border: 0 !important;
    border-bottom: 2px solid transparent !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    color: var(--rk-muted) !important;
    font-size: 14.5px !important;
    font-weight: 600 !important;
    height: 100% !important;
    padding: 0 2px !important;
}
.rk-tabs .tab-container > button:hover, .rk-tabs .tab-nav > button:hover {
    color: var(--rk-ink) !important;
    background: transparent !important;
}
.rk-tabs .tab-container > button.selected, .rk-tabs .tab-nav > button.selected,
.rk-tabs .tab-container > button[aria-selected="true"],
.rk-tabs .tab-nav > button[aria-selected="true"] {
    color: var(--rk-ink) !important;
    border-bottom-color: var(--rk-green) !important;
}
.rk-tabs .tabitem, .rk-tabs > .tabitem { padding: 0 !important; }

/* =========================================================================
   Breadcrumb
   ========================================================================= */
.rk-breadcrumb {
    color: var(--rk-muted) !important;
    font-size: 13.5px !important;
    padding: 22px 0 16px !important;
}
.rk-breadcrumb .sep { margin: 0 8px; color: #b7bac3; }
.rk-breadcrumb .last { color: var(--rk-ink); font-weight: 600; }

/* =========================================================================
   Content — wide preview panel + sidebar
   ========================================================================= */
.rk-hero { gap: 40px !important; align-items: flex-start !important; }

.rk-panel {
    background: var(--rk-dark) !important;
    border: 1px solid #23262f !important;
    border-radius: 18px !important;
    padding: 0 !important;
    gap: 0 !important;
    overflow: hidden !important;
    box-shadow: 0 22px 48px rgba(15, 17, 22, 0.16) !important;
    --background-fill-primary: #1b1e27;
    --background-fill-secondary: #0f1116;
    --block-background-fill: transparent;
    --border-color-primary: #2a2e3a;
    --body-text-color: #e9ebf2;
    --body-text-color-subdued: #99a0b0;
    --color-accent-soft: #17372b;
    --chatbot-text-size: 15px;
}
.rk-panel .block, .rk-panel .form, .rk-panel .html-container {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
}
.rk-panel-head { padding: 26px 26px 12px !important; }
.rk-panel-brand {
    color: #fff !important;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.2;
}
.rk-panel-sub { margin: 6px 0 0 !important; color: #99a0b0 !important; font-size: 13.5px; }
.rk-chat { background: transparent !important; }

.rk-composer {
    align-items: stretch !important;
    gap: 10px !important;
    padding: 14px 16px 18px !important;
    background: #0f1116 !important;
    border-top: 1px solid #22252f !important;
}
.rk-input textarea, .rk-input input {
    background: #fff !important;
    color: var(--rk-ink) !important;
    border: 0 !important;
    border-radius: 12px !important;
    min-height: 54px !important;
    font-size: 14.5px !important;
    padding: 15px 16px !important;
}
.rk-input input::placeholder, .rk-input textarea::placeholder { color: #9aa0ad !important; }
.rk-send, .rk-send button {
    background: var(--rk-green) !important;
    border: 0 !important;
    color: #06281c !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    height: 54px !important;
    font-size: 15px !important;
    box-shadow: none !important;
}
.rk-send:hover, .rk-send button:hover { background: var(--rk-green-dark) !important; }

/* Sidebar: title, author, CTA card */
.rk-sidebar { gap: 16px !important; position: sticky; top: 140px; }
.rk-title {
    margin: 0 0 8px !important;
    color: var(--rk-ink) !important;
    font-size: 27px !important;
    font-weight: 800 !important;
    line-height: 1.2 !important;
    letter-spacing: -0.02em !important;
}
.rk-by { margin: 0 0 18px !important; color: var(--rk-muted) !important; font-size: 14px !important; }
.rk-by b { color: var(--rk-ink) !important; }
.rk-card {
    background: #fff !important;
    border: 1px solid var(--rk-border) !important;
    border-radius: 14px !important;
    padding: 22px !important;
    gap: 18px !important;
    box-shadow: 0 1px 2px rgba(16, 18, 24, 0.04) !important;
}
.rk-card h3 {
    margin: 0 !important;
    color: var(--rk-ink) !important;
    font-size: 20px !important;
    font-weight: 700 !important;
    line-height: 1.32 !important;
    letter-spacing: -0.01em !important;
}
.rk-features {
    list-style: none !important;
    margin: 18px 0 4px !important;
    padding: 0 !important;
    display: grid;
    gap: 13px;
}
.rk-features li {
    position: relative;
    padding-left: 30px;
    color: #2b2e39;
    font-size: 14.5px;
    line-height: 1.45;
}
.rk-features li::before {
    content: "✓";
    position: absolute;
    left: 0;
    top: 0;
    width: 19px;
    height: 19px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1.5px solid #14151b;
    border-radius: 50%;
    color: #14151b;
    font-size: 11px;
    font-weight: 700;
}
.rk-signin {
    margin: 18px 0 0 !important;
    color: var(--rk-muted) !important;
    font-size: 14px !important;
    text-align: center;
}
.rk-signin a { color: var(--rk-ink) !important; font-weight: 600; text-decoration: underline; }

/* Buttons */
.rk-cta, .rk-cta button {
    background: var(--rk-green) !important;
    border: 1px solid var(--rk-green) !important;
    color: #06281c !important;
    font-weight: 700 !important;
    border-radius: 9px !important;
    height: 48px !important;
    font-size: 15px !important;
    box-shadow: none !important;
}
.rk-cta:hover, .rk-cta button:hover {
    background: var(--rk-green-dark) !important;
    border-color: var(--rk-green-dark) !important;
}
.rk-cta-top, .rk-cta-top button { height: 44px !important; white-space: nowrap; }
.rk-outline, .rk-outline button {
    background: #fff !important;
    border: 1.5px solid var(--rk-ink) !important;
    color: var(--rk-ink) !important;
    font-weight: 700 !important;
    border-radius: 9px !important;
    height: 48px !important;
    font-size: 15px !important;
}
.rk-outline:hover, .rk-outline button:hover { background: #f4f5f8 !important; }

/* =========================================================================
   Secondary tabs (Files / Reminders / Statistics / Settings)
   ========================================================================= */
.rk-section {
    background: #fff !important;
    border: 1px solid var(--rk-border) !important;
    border-radius: 14px !important;
    padding: 22px !important;
    gap: 16px !important;
    box-shadow: 0 1px 2px rgba(16, 18, 24, 0.04) !important;
}
.rk-section .block { background: transparent !important; }
.rk-examples, .rk-examples .block, .rk-examples .html-container {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}
.rk-examples table { background: transparent !important; }

/* =========================================================================
   Small screens
   ========================================================================= */
@media (max-width: 900px) {
    .rk-topbar {
        height: auto !important;
        flex-wrap: wrap !important;
        padding: 10px 16px !important;
        width: calc(100% + 2 * (50vw - 50%)) !important;
    }
    .rk-pill { display: none !important; }
    .rk-brand-cell, .rk-avatar-cell { min-width: 0 !important; }
    .rk-search-cell { min-width: 160px !important; }
    .rk-tabs { padding: 0 16px !important; }
    .rk-tabs .tab-wrapper { height: auto !important; overflow-x: auto !important; }
    .rk-tabs .tab-container { height: 48px !important; }
    .rk-hero { gap: 22px !important; }
    .rk-title { font-size: 22px !important; }
    .rk-sidebar { position: static !important; }
}
"""


def breadcrumb(current: str) -> gr.HTML:
    """Render the marketplace-style breadcrumb trail for the active tab."""
    return gr.HTML(
        f'<div class="rk-breadcrumb">Rumah <span class="sep">»</span> '
        f'Modul <span class="sep">»</span> <span class="last">{current}</span></div>',
        elem_classes=["rk-plain"],
    )


async def init_orchestrator():
    """Initialize the global orchestrator."""
    global orchestrator
    orchestrator = AgentOrchestrator()
    await orchestrator.initialize()
    return orchestrator


def get_or_create_session(request: gr.Request) -> str:
    """Get or create a session for the user."""
    # Use a simple session ID based on timestamp
    # In production, you'd use proper session management
    if not hasattr(get_or_create_session, "_sessions"):
        get_or_create_session._sessions = {}

    # Use cookie or create new session
    session_id = str(uuid.uuid4())
    return session_id


async def chat_response(
    message: str,
    history: list,
    session_id: str
) -> tuple:
    """
    Process chat message and return response.

    Args:
        message: User message
        history: Chat history
        session_id: Current session ID

    Returns:
        Updated history and session ID
    """
    if not message.strip():
        return history, session_id

    # Create session if needed
    if not session_id:
        session_id = orchestrator.create_session()

    # Add user message to history
    history = history + [{"role": "user", "content": message}]

    try:
        # Get response from agent
        response = await orchestrator.chat(message, session_id)

        # Add assistant response to history
        history = history + [{"role": "assistant", "content": response}]

    except Exception as e:
        logger.error(f"Chat error: {e}")
        history = history + [
            {"role": "assistant", "content": f"Maaf, terjadi error: {str(e)}"}
        ]

    return history, session_id


async def stream_chat_response(
    message: str,
    history: list,
    session_id: str
):
    """
    Stream chat response in the Chatbot's role/content message format.

    Args:
        message: User message
        history: Chat history
        session_id: Current session ID

    Yields:
        Updated message history
    """
    if not message.strip():
        yield history
        return

    # Create session if needed
    if not session_id:
        session_id = orchestrator.create_session()

    # Gradio shares yielded values with this generator, so copy before updating.
    history = list(history or [])

    # Gradio's Chatbot accepts role/content messages.
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": ""}
    ]
    yield history

    # Stream response into the assistant placeholder.
    full_response = ""
    try:
        async for chunk in orchestrator.chat_stream(message, session_id):
            full_response += chunk
            history = history[:-1] + [
                {"role": "assistant", "content": full_response + "▌"}
            ]
            yield history
    except Exception as e:
        logger.exception("Stream chat error")
        full_response = f"Maaf, terjadi error: {str(e)}"

    # Final response without cursor
    history = history[:-1] + [{"role": "assistant", "content": full_response}]
    yield history


async def get_sessions_list() -> list:
    """Get list of all sessions."""
    sessions = await orchestrator.get_sessions()
    if not sessions:
        return [["(Belum ada session)", "", "", ""]]

    return [
        [
            s["session_id"][:8] + "...",
            s["started"],
            s["last_active"],
            str(s["message_count"])
        ]
        for s in sessions
    ]


async def get_reminders_list() -> str:
    """Get formatted list of active reminders."""
    reminders = await orchestrator.memory.get_active_reminders()
    if not reminders:
        return "Tidak ada reminder aktif"

    result = "📋 **Reminder Aktif:**\n\n"
    for r in reminders:
        result += f"**ID: {r['id']}** | {r['message']}\n"
        result += f"⏰ Jadwal: {r['trigger_at']}\n\n"

    return result


async def get_task_stats() -> str:
    """Get task execution statistics."""
    stats = await orchestrator.get_task_stats()

    if not stats:
        return "Belum ada aktivitas"

    result = "📊 **Statistik Task:**\n\n"
    result += "| Tool | Total | Success | Avg Duration |\n"
    result += "|------|-------|---------|---------------|\n"

    for tool_name, stat in stats.items():
        success_rate = (stat["success"] / stat["total"] * 100) if stat["total"] > 0 else 0
        result += f"| {tool_name} | {stat['total']} | {success_rate:.0f}% | {stat['avg_duration_ms']:.0f}ms |\n"

    return result


async def upload_file(file) -> str:
    """Handle file upload."""
    if file is None:
        return "Tidak ada file yang diupload"

    try:
        # Gradio already saves to temp, we just need to note the path
        return f"File berhasil diupload: {file.name}"
    except Exception as e:
        return f"Error upload: {str(e)}"


def create_ui():
    """Create the Gradio UI."""

    with gr.Blocks(title="RutinitasKu") as app:

        # State
        session_id = gr.State(value="")

        # ===== Top bar: brand + search + primary action =====
        with gr.Row(elem_classes=["rk-topbar"]):
            gr.HTML(
                BRAND_HTML,
                elem_classes=["rk-plain", "rk-brand-cell"],
                scale=0,
            )
            gr.Dropdown(
                choices=["Semua modul", "Chat", "Files", "Reminders", "Email", "Calendar"],
                value="Semua modul",
                show_label=False,
                interactive=False,
                scale=0,
                min_width=170,
                elem_classes=["rk-pill"],
            )
            gr.Textbox(
                placeholder="Cari di RutinitasKu...",
                show_label=False,
                interactive=False,
                scale=8,
                elem_classes=["rk-search", "rk-search-cell"],
            )
            top_new_session_btn = gr.Button(
                "+ Sesi Baru",
                scale=0,
                min_width=150,
                elem_classes=["rk-cta", "rk-cta-top"],
            )
            gr.HTML(
                AVATAR_HTML,
                elem_classes=["rk-plain", "rk-avatar-cell"],
                scale=0,
            )

        # ===== Nav tabs (marketplace menu) =====
        with gr.Tabs(elem_classes=["rk-tabs"]):

            # ===== Chat Tab (hero: preview panel + sidebar) =====
            with gr.Tab("Chat", id="chat"):
                breadcrumb("Chat")

                with gr.Row(elem_classes=["rk-hero"]):
                    # ---- Left: dark preview panel holding the conversation ----
                    with gr.Column(scale=5, elem_classes=["rk-panel"]):
                        gr.HTML(PANEL_HEAD_HTML, elem_classes=["rk-plain"])

                        chatbot = gr.Chatbot(
                            label="Percakapan",
                            show_label=False,
                            height=500,
                            elem_classes=["rk-chat"],
                        )

                        with gr.Row(elem_classes=["rk-composer"]):
                            msg_input = gr.Textbox(
                                label="Pesan",
                                show_label=False,
                                placeholder="Ketik pesan Anda di sini...",
                                lines=2,
                                scale=9,
                                elem_classes=["rk-input"],
                            )
                            send_btn = gr.Button(
                                "Kirim",
                                variant="primary",
                                scale=1,
                                elem_classes=["rk-send"],
                            )

                    # ---- Right: info + CTA sidebar ----
                    with gr.Column(scale=3, elem_classes=["rk-sidebar"]):
                        gr.HTML(SIDEBAR_HEAD_HTML, elem_classes=["rk-plain"])

                        with gr.Column(elem_classes=["rk-card"]):
                            gr.HTML(CARD_HTML, elem_classes=["rk-plain"])
                            new_session_btn = gr.Button(
                                "Mulai sesi baru",
                                elem_classes=["rk-cta"],
                            )

                        clear_btn = gr.Button(
                            "Hapus percakapan",
                            elem_classes=["rk-outline"],
                        )

                        gr.HTML(SIGNIN_HTML, elem_classes=["rk-plain"])

                # Chat examples
                with gr.Column(elem_classes=["rk-examples"]):
                    gr.Examples(
                        examples=[
                            "Cari informasi tentang tren AI terbaru",
                            "Baca email terbaru saya",
                            "Analisis file CSV yang saya upload",
                            "Jadwalkan meeting besok jam 2 siang",
                            "Ingatkan saya dalam 2 jam untuk follow up"
                        ],
                        inputs=msg_input,
                    )

            # ===== Files Tab =====
            with gr.Tab("Files", id="files"):
                breadcrumb("Files")

                with gr.Row(elem_classes=["rk-hero"]):
                    with gr.Column(scale=1, elem_classes=["rk-section"]):
                        file_upload = gr.File(
                            label="Upload File",
                            file_types=[".csv", ".xlsx", ".pdf", ".txt", ".json"],
                            type="filepath"
                        )
                        upload_status = gr.Textbox(label="Status Upload", interactive=False)

                    with gr.Column(scale=1, elem_classes=["rk-section"]):
                        file_list_display = gr.Textbox(
                            label="Daftar File di Workspace",
                            lines=10,
                            interactive=False
                        )
                        refresh_files_btn = gr.Button("🔄 Refresh", elem_classes=["rk-outline"])

            # ===== Reminders Tab =====
            with gr.Tab("Reminders", id="reminders"):
                breadcrumb("Reminders")

                with gr.Column(elem_classes=["rk-section"]):
                    reminders_display = gr.Markdown(
                        value="Memuat reminder...",
                        label="Reminder Aktif"
                    )
                    refresh_reminders_btn = gr.Button(
                        "🔄 Refresh Reminder",
                        elem_classes=["rk-outline"],
                    )

            # ===== Stats Tab =====
            with gr.Tab("Statistics", id="stats"):
                breadcrumb("Statistics")

                with gr.Column(elem_classes=["rk-section"]):
                    stats_display = gr.Markdown(
                        value="Memuat statistik...",
                        label="Statistik Penggunaan"
                    )
                    refresh_stats_btn = gr.Button(
                        "🔄 Refresh Statistik",
                        elem_classes=["rk-outline"],
                    )

            # ===== Settings Tab =====
            with gr.Tab("Settings", id="settings"):
                breadcrumb("Settings")

                with gr.Row(elem_classes=["rk-hero"]):
                    with gr.Column(scale=1, elem_classes=["rk-section"]):
                        gr.Markdown("**LLM Provider Status**")
                        llm_status = gr.Textbox(
                            label="Status",
                            value="Memuat...",
                            interactive=False
                        )
                        check_llm_btn = gr.Button(
                            "🔍 Cek Status LLM",
                            elem_classes=["rk-cta"],
                        )

                    with gr.Column(scale=1, elem_classes=["rk-section"]):
                        gr.Markdown("**Session Info**")
                        session_info = gr.Textbox(
                            label="Session ID",
                            value="",
                            interactive=False
                        )

                with gr.Column(elem_classes=["rk-section"]):
                    gr.Markdown(
                        """
                        ### 📝 Panduan

                        **Email Setup:**
                        1. Buat App Password di Google Account
                        2. Set `EMAIL_ADDRESS` dan `EMAIL_PASSWORD` di `.env`

                        **Google Calendar:**
                        1. Buat project di Google Cloud Console
                        2. Enable Calendar API
                        3. Download credentials.json
                        4. Letakkan di folder project

                        **NaraRouter:**
                        1. Daftar di https://router.bynara.id
                        2. Buat API Key
                        3. Set `NARAROUTER_API_KEY` di `.env`
                        """
                    )

        # ===== Event Handlers =====

        # Chat submission
        async def handle_submit(message, history, sid):
            async for updated_history in stream_chat_response(message, history, sid):
                yield updated_history, sid

        msg_input.submit(
            fn=handle_submit,
            inputs=[msg_input, chatbot, session_id],
            outputs=[chatbot, session_id]
        ).then(
            fn=lambda: "",
            outputs=msg_input
        )

        send_btn.click(
            fn=handle_submit,
            inputs=[msg_input, chatbot, session_id],
            outputs=[chatbot, session_id]
        ).then(
            fn=lambda: "",
            outputs=msg_input
        )

        # Clear chat
        async def clear_chat(sid):
            if sid:
                await orchestrator.clear_session(sid)
            return [], ""

        clear_btn.click(
            fn=clear_chat,
            inputs=[session_id],
            outputs=[chatbot, session_id]
        )

        # New session
        def new_session():
            return orchestrator.create_session()

        new_session_btn.click(
            fn=new_session,
            outputs=[session_id]
        )

        top_new_session_btn.click(
            fn=new_session,
            outputs=[session_id]
        )

        # File upload
        file_upload.change(
            fn=upload_file,
            inputs=[file_upload],
            outputs=[upload_status]
        )

        # Refresh files
        async def refresh_files():
            return await orchestrator.chat("list files in workspace", session_id.value or orchestrator.create_session())

        refresh_files_btn.click(
            fn=refresh_files,
            outputs=[file_list_display]
        )

        # Refresh reminders
        refresh_reminders_btn.click(
            fn=get_reminders_list,
            outputs=[reminders_display]
        )

        # Refresh stats
        refresh_stats_btn.click(
            fn=get_task_stats,
            outputs=[stats_display]
        )

        # Check LLM status
        def check_llm():
            status = orchestrator.llm.is_available()
            result = []
            if status["claude"]:
                result.append("✅ Claude API: Connected")
            else:
                result.append("❌ Claude API: Not configured")
            if status["nararouter"]:
                result.append("✅ NaraRouter: Connected")
            else:
                result.append("❌ NaraRouter: Not configured")
            return "\n".join(result)

        check_llm_btn.click(
            fn=check_llm,
            outputs=[llm_status]
        )

        # Initialize session on load
        app.load(
            fn=lambda: orchestrator.create_session(),
            outputs=[session_id]
        )

    return app


async def main():
    """Main entry point."""
    # Validate configuration
    errors = validate_config()
    if errors:
        logger.warning("Configuration warnings:")
        for error in errors:
            logger.warning(f"  - {error}")

    # Initialize orchestrator
    await init_orchestrator()
    logger.info("Orchestrator initialized")

    # Create and launch UI
    app = create_ui()

    logger.info(f"Starting RutinitasKu on {HOST}:{PORT}")
    app.launch(
        server_name=HOST,
        server_port=PORT,
        share=False,
        theme=gr.themes.Soft(
            primary_hue="green",
            radius_size="sm",
        ),
        css=CUSTOM_CSS,
    )


if __name__ == "__main__":
    asyncio.run(main())
