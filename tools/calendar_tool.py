"""
NaraTask AI - Calendar Tool
Google Calendar API integration.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_TOKEN_FILE
from .registry import registry


# Scopes required for Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    """
    Get Google Calendar API service.
    Handles OAuth2 authentication flow.

    Returns:
        Google Calendar service object
    """
    creds = None

    # Check if token file exists
    if os.path.exists(GOOGLE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, SCOPES)

    # If no valid credentials, refresh or create new
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"File credentials Google tidak ditemukan: {GOOGLE_CREDENTIALS_FILE}\n"
                    f"Download dari Google Cloud Console dan simpan di folder project."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token for future use
        with open(GOOGLE_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


@registry.tool(
    name="calendar_list_events",
    description="Lihat event di Google Calendar. Bisa filter berdasarkan tanggal.",
    input_schema={
        "type": "object",
        "properties": {
            "time_min": {
                "type": "string",
                "description": "Tanggal mulai (format: YYYY-MM-DD atau 'today', 'tomorrow', 'week')"
            },
            "time_max": {
                "type": "string",
                "description": "Tanggal akhir (format: YYYY-MM-DD)"
            },
            "max_results": {
                "type": "integer",
                "description": "Jumlah event maksimal (default: 10)",
                "default": 10
            },
            "calendar_id": {
                "type": "string",
                "description": "Calendar ID (default: 'primary')",
                "default": "primary"
            }
        },
        "required": []
    }
)
async def calendar_list_events(
    time_min: str = None,
    time_max: str = None,
    max_results: int = 10,
    calendar_id: str = "primary"
) -> str:
    """
    List events from Google Calendar.

    Args:
        time_min: Start date filter
        time_max: End date filter
        max_results: Maximum events to return
        calendar_id: Calendar ID

    Returns:
        Formatted event list
    """
    try:
        service = get_calendar_service()

        # Parse time filters
        now = datetime.utcnow()

        if time_min:
            if time_min.lower() == "today":
                time_min = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
            elif time_min.lower() == "tomorrow":
                tomorrow = now + timedelta(days=1)
                time_min = tomorrow.replace(hour=0, minute=0, second=0).isoformat() + "Z"
            elif time_min.lower() == "week":
                time_min = now.isoformat() + "Z"
                time_max = (now + timedelta(days=7)).isoformat() + "Z"
            else:
                time_min = datetime.strptime(time_min, "%Y-%m-%d").isoformat() + "Z"
        else:
            time_min = now.isoformat() + "Z"

        if time_max and "Z" not in time_max:
            time_max = datetime.strptime(time_max, "%Y-%m-%d").isoformat() + "Z"

        # Call Google Calendar API
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])

        if not events:
            return "Tidak ada event ditemukan"

        result = f"📅 Event Calendar ({len(events)} event):\n\n"

        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))

            # Parse datetime
            try:
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))

                if "T" in start:
                    time_str = f"{start_dt.strftime('%d %b %Y, %H:%M')} - {end_dt.strftime('%H:%M')}"
                else:
                    time_str = f"{start_dt.strftime('%d %b %Y')} (All day)"
            except:
                time_str = start

            summary = event.get("summary", "(Tanpa judul)")
            location = event.get("location", "")
            description = event.get("description", "")

            result += f"📌 {summary}\n"
            result += f"   ⏰ {time_str}\n"
            if location:
                result += f"   📍 {location}\n"
            if description:
                desc_preview = description[:100] + "..." if len(description) > 100 else description
                result += f"   📝 {desc_preview}\n"
            result += "\n"

        return result

    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error saat ambil event: {str(e)}"


@registry.tool(
    name="calendar_create_event",
    description="Buat event baru di Google Calendar.",
    input_schema={
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Judul event"
            },
            "start_time": {
                "type": "string",
                "description": "Waktu mulai (format: YYYY-MM-DD HH:MM)"
            },
            "end_time": {
                "type": "string",
                "description": "Waktu selesai (format: YYYY-MM-DD HH:MM)"
            },
            "description": {
                "type": "string",
                "description": "Deskripsi event (opsional)"
            },
            "location": {
                "type": "string",
                "description": "Lokasi event (opsional)"
            },
            "all_day": {
                "type": "boolean",
                "description": "Event seharian (default: false)",
                "default": False
            },
            "calendar_id": {
                "type": "string",
                "description": "Calendar ID (default: 'primary')",
                "default": "primary"
            }
        },
        "required": ["summary", "start_time", "end_time"]
    }
)
async def calendar_create_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = None,
    location: str = None,
    all_day: bool = False,
    calendar_id: str = "primary"
) -> str:
    """
    Create a new calendar event.

    Args:
        summary: Event title
        start_time: Start time
        end_time: End time
        description: Event description
        location: Event location
        all_day: Whether it's an all-day event
        calendar_id: Calendar ID

    Returns:
        Creation result
    """
    try:
        service = get_calendar_service()

        # Parse times
        if all_day:
            start_dt = datetime.strptime(start_time, "%Y-%m-%d")
            end_dt = datetime.strptime(end_time, "%Y-%m-%d")
            start = {"date": start_dt.strftime("%Y-%m-%d")}
            end = {"date": end_dt.strftime("%Y-%m-%d")}
        else:
            start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
            start = {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Jakarta"}
            end = {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Jakarta"}

        # Build event body
        event_body = {
            "summary": summary,
            "start": start,
            "end": end
        }

        if description:
            event_body["description"] = description
        if location:
            event_body["location"] = location

        # Create event
        event = service.events().insert(
            calendarId=calendar_id,
            body=event_body
        ).execute()

        return (
            f"Event berhasil dibuat!\n\n"
            f"📌 {summary}\n"
            f"⏰ {start_time} - {end_time}\n"
            f"🔗 {event.get('htmlLink', '')}"
        )

    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except ValueError as e:
        return f"Error format tanggal: {str(e)}"
    except Exception as e:
        return f"Error saat buat event: {str(e)}"


@registry.tool(
    name="calendar_delete_event",
    description="Hapus event dari Google Calendar.",
    input_schema={
        "type": "object",
        "properties": {
            "event_id": {
                "type": "string",
                "description": "ID event yang akan dihapus"
            },
            "calendar_id": {
                "type": "string",
                "description": "Calendar ID (default: 'primary')",
                "default": "primary"
            }
        },
        "required": ["event_id"]
    }
)
async def calendar_delete_event(
    event_id: str,
    calendar_id: str = "primary"
) -> str:
    """
    Delete a calendar event.

    Args:
        event_id: Event ID to delete
        calendar_id: Calendar ID

    Returns:
        Deletion result
    """
    try:
        service = get_calendar_service()

        service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()

        return f"Event berhasil dihapus (ID: {event_id})"

    except Exception as e:
        return f"Error saat hapus event: {str(e)}"