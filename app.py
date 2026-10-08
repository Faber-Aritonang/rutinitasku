"""
RutinitasKu - Main Application
Gradio-based web interface for the task automation agent.
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
    Stream chat response.

    Args:
        message: User message
        history: Chat history
        session_id: Current session ID

    Yields:
        Updated history
    """
    if not message.strip():
        yield history
        return

    # Create session if needed
    if not session_id:
        session_id = orchestrator.create_session()

    # Add user message
    history = history + [{"role": "user", "content": message}]
    yield history

    # Stream response
    full_response = ""
    async for chunk in orchestrator.chat_stream(message, session_id):
        full_response += chunk
        history[-1] = {"role": "assistant", "content": full_response + "▌"}
        yield history

    # Final response without cursor
    history[-1] = {"role": "assistant", "content": full_response}
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

    with gr.Blocks(
        title="RutinitasKu"
    ) as app:

        # State
        session_id = gr.State(value="")

        # Header
        gr.Markdown(
            """
            # 🤖 RutinitasKu
            **Personal Task Automation Assistant**

            Saya bisa membantu Anda dengan web research, email, calendar, file management, dan lainnya.
            """,
            elem_classes="main-header"
        )

        with gr.Tabs():
            # ===== Chat Tab =====
            with gr.Tab("💬 Chat", id="chat"):
                chatbot = gr.Chatbot(
                    label="Percakapan",
                    height=500
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        label="Pesan",
                        placeholder="Ketik pesan Anda di sini...",
                        lines=2,
                        scale=9
                    )
                    send_btn = gr.Button("Kirim", variant="primary", scale=1)

                with gr.Row():
                    clear_btn = gr.Button("🗑️ Hapus Chat")
                    new_session_btn = gr.Button("🆕 Session Baru")

                # Chat examples
                gr.Examples(
                    examples=[
                        "Cari informasi tentang tren AI terbaru",
                        "Baca email terbaru saya",
                        "Analisis file CSV yang saya upload",
                        "Jadwalkan meeting besok jam 2 siang",
                        "Ingatkan saya dalam 2 jam untuk follow up"
                    ],
                    inputs=msg_input
                )

            # ===== Files Tab =====
            with gr.Tab("📁 Files", id="files"):
                with gr.Row():
                    with gr.Column():
                        file_upload = gr.File(
                            label="Upload File",
                            file_types=[".csv", ".xlsx", ".pdf", ".txt", ".json"],
                            type="filepath"
                        )
                        upload_status = gr.Textbox(label="Status Upload", interactive=False)

                    with gr.Column():
                        file_list_display = gr.Textbox(
                            label="Daftar File di Workspace",
                            lines=10,
                            interactive=False
                        )
                        refresh_files_btn = gr.Button("🔄 Refresh")

            # ===== Reminders Tab =====
            with gr.Tab("⏰ Reminders", id="reminders"):
                reminders_display = gr.Markdown(
                    value="Memuat reminder...",
                    label="Reminder Aktif"
                )
                refresh_reminders_btn = gr.Button("🔄 Refresh Reminder")

            # ===== Stats Tab =====
            with gr.Tab("📊 Statistics", id="stats"):
                stats_display = gr.Markdown(
                    value="Memuat statistik...",
                    label="Statistik Penggunaan"
                )
                refresh_stats_btn = gr.Button("🔄 Refresh Statistik")

            # ===== Settings Tab =====
            with gr.Tab("⚙️ Settings", id="settings"):
                gr.Markdown("### Konfigurasi")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("**LLM Provider Status**")
                        llm_status = gr.Textbox(
                            label="Status",
                            value="Memuat...",
                            interactive=False
                        )
                        check_llm_btn = gr.Button("🔍 Cek Status LLM")

                    with gr.Column():
                        gr.Markdown("**Session Info**")
                        session_info = gr.Textbox(
                            label="Session ID",
                            value="",
                            interactive=False
                        )

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
        theme=gr.themes.Soft(),
        css="""
        .main-header {
            text-align: center;
            margin-bottom: 20px;
        }
        """
    )


if __name__ == "__main__":
    asyncio.run(main())