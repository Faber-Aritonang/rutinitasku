"""
RutinitasKu - Reminder Tool
Time-based reminder management.
"""

from datetime import datetime, timedelta
from typing import Optional

from .registry import registry


@registry.tool(
    name="save_fact",
    description="Simpan fakta atau preferensi user untuk personalisasi. Contoh: nama, bahasa, topik favorit.",
    input_schema={
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "Nama fakta (contoh: 'nama', 'bahasa', 'kota')"
            },
            "value": {
                "type": "string",
                "description": "Nilai fakta (contoh: 'Jimmy', 'Indonesia', 'Jakarta')"
            }
        },
        "required": ["key", "value"]
    }
)
async def save_fact(key: str, value: str) -> str:
    """
    Save a user fact or preference.

    Args:
        key: Fact key
        value: Fact value

    Returns:
        Confirmation message
    """
    # This is handled by the orchestrator directly
    return f"SAVE_FACT|{key}|{value}"


@registry.tool(
    name="set_reminder",
    description="Atur pengingat baru. Bisa berdasarkan waktu spesifik atau durasi.",
    input_schema={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Pesan reminder"
            },
            "time": {
                "type": "string",
                "description": "Waktu spesifik (format: YYYY-MM-DD HH:MM atau 'HH:MM')"
            },
            "duration": {
                "type": "string",
                "description": "Durasi dari sekarang (contoh: '30m', '2h', '1d')"
            }
        },
        "required": ["message"]
    }
)
async def set_reminder(
    message: str,
    time: str = None,
    duration: str = None
) -> str:
    """
    Set a new reminder.

    Args:
        message: Reminder message
        time: Specific time
        duration: Duration from now

    Returns:
        Confirmation message
    """
    # Note: This is a placeholder that returns the reminder details
    # Actual reminder storage will be handled by the orchestrator using MemoryManager

    if time:
        try:
            # Parse time
            if ":" in time and len(time) <= 5:
                # Time only (HH:MM), assume today
                now = datetime.now()
                hour, minute = map(int, time.split(":"))
                trigger_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if trigger_at < now:
                    trigger_at += timedelta(days=1)
            else:
                # Full datetime
                trigger_at = datetime.strptime(time, "%Y-%m-%d %H:%M")

            return (
                f"REMINDER_SET|{trigger_at.isoformat()}|{message}\n\n"
                f"⏰ Reminder diatur!\n"
                f"📌 Pesan: {message}\n"
                f"📅 Waktu: {trigger_at.strftime('%d %B %Y, %H:%M')}"
            )
        except ValueError:
            return f"Error: Format waktu tidak valid. Gunakan 'YYYY-MM-DD HH:MM' atau 'HH:MM'"

    elif duration:
        try:
            # Parse duration
            now = datetime.now()

            if duration.endswith("m"):
                minutes = int(duration[:-1])
                trigger_at = now + timedelta(minutes=minutes)
            elif duration.endswith("h"):
                hours = int(duration[:-1])
                trigger_at = now + timedelta(hours=hours)
            elif duration.endswith("d"):
                days = int(duration[:-1])
                trigger_at = now + timedelta(days=days)
            else:
                return "Error: Format durasi tidak valid. Gunakan '30m', '2h', atau '1d'"

            return (
                f"REMINDER_SET|{trigger_at.isoformat()}|{message}\n\n"
                f"⏰ Reminder diatur!\n"
                f"📌 Pesan: {message}\n"
                f"⏱️ Akan muncul dalam: {duration}"
            )
        except ValueError:
            return f"Error: Format durasi tidak valid"

    else:
        return "Error: Harap tentukan 'time' atau 'duration'"


@registry.tool(
    name="list_reminders",
    description="Lihat daftar reminder yang aktif.",
    input_schema={
        "type": "object",
        "properties": {},
        "required": []
    }
)
async def list_reminders() -> str:
    """
    List all active reminders.

    Returns:
        Formatted reminder list
    """
    # This will be populated by the orchestrator
    return "LIST_REMINDERS"


@registry.tool(
    name="delete_reminder",
    description="Hapus reminder berdasarkan ID.",
    input_schema={
        "type": "object",
        "properties": {
            "reminder_id": {
                "type": "integer",
                "description": "ID reminder yang akan dihapus"
            }
        },
        "required": ["reminder_id"]
    }
)
async def delete_reminder(reminder_id: int) -> str:
    """
    Delete a reminder.

    Args:
        reminder_id: Reminder ID to delete

    Returns:
        Deletion result
    """
    return f"DELETE_REMINDER|{reminder_id}"