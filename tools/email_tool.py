"""
RutinitasKu - Email Tool
IMAP/SMTP email integration.
"""

import asyncio
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime

from config import (
    IMAP_SERVER, IMAP_PORT,
    SMTP_SERVER, SMTP_PORT,
    EMAIL_ADDRESS, EMAIL_PASSWORD
)
from .registry import registry


def _decode_mime_header(header):
    """Decode MIME encoded header."""
    if not header:
        return ""

    decoded_parts = decode_header(header)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            charset = charset or "utf-8"
            try:
                result.append(part.decode(charset))
            except:
                result.append(part.decode("utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _get_email_body(msg):
    """Extract email body from message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    return part.get_payload(decode=True).decode("utf-8", errors="replace")
                except:
                    continue
            elif content_type == "text/html":
                try:
                    from bs4 import BeautifulSoup
                    html = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    soup = BeautifulSoup(html, "html.parser")
                    return soup.get_text(separator="\n", strip=True)
                except:
                    continue
    else:
        try:
            return msg.get_payload(decode=True).decode("utf-8", errors="replace")
        except:
            pass
    return "[Tidak dapat membaca isi email]"


def _parse_date(value: str, field: str) -> str:
    """Convert YYYY-MM-DD into the IMAP date format (e.g. 08-Oct-2026)."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d-%b-%Y")
    except ValueError:
        raise ValueError(f"Format tanggal '{field}' harus YYYY-MM-DD, bukan '{value}'")


def _build_search_criteria(
    unread_only: bool = False,
    search: str = None,
    since: str = None,
    before: str = None,
) -> str:
    """Build an IMAP SEARCH string from the tool arguments."""
    criteria = []
    if unread_only:
        criteria.append("UNSEEN")
    if since:
        criteria.append(f"SINCE {_parse_date(since, 'since')}")
    if before:
        criteria.append(f"BEFORE {_parse_date(before, 'before')}")
    if search:
        criteria.append(search)

    return " ".join(criteria) if criteria else "ALL"


MAX_EMAIL_LIMIT = 20


@registry.tool(
    name="email_read",
    description="Baca email terbaru dari inbox. Bisa filter berdasarkan sender, subject, atau jumlah.",
    input_schema={
        "type": "object",
        "properties": {
            "folder": {
                "type": "string",
                "description": "Folder email (INBOX, Sent, Drafts)",
                "default": "INBOX"
            },
            "limit": {
                "type": "integer",
                "description": "Jumlah email yang dibaca, 1-20 (default: 10)",
                "default": 10
            },
            "since": {
                "type": "string",
                "description": "Email pada atau sesudah tanggal ini, format YYYY-MM-DD (contoh: 2026-10-08)"
            },
            "before": {
                "type": "string",
                "description": "Email sebelum tanggal ini (tidak termasuk), format YYYY-MM-DD. Untuk satu hari penuh, isi since=tanggal dan before=tanggal berikutnya"
            },
            "search": {
                "type": "string",
                "description": "Filter pencarian (contoh: 'FROM:john' atau 'SUBJECT:meeting')"
            },
            "unread_only": {
                "type": "boolean",
                "description": "Hanya email yang belum dibaca (default: false)",
                "default": False
            }
        },
        "required": []
    }
)
async def email_read(
    folder: str = "INBOX",
    limit: int = 10,
    search: str = None,
    unread_only: bool = False,
    since: str = None,
    before: str = None,
) -> str:
    """
    Read emails from mailbox.

    Args:
        folder: Email folder
        limit: Number of emails to read (1-20)
        search: Search filter
        unread_only: Only unread emails
        since: Only emails on or after this date (YYYY-MM-DD)
        before: Only emails before this date (YYYY-MM-DD, exclusive)

    Returns:
        Formatted email list
    """
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return "Error: Konfigurasi email belum diatur. Set EMAIL_ADDRESS dan EMAIL_PASSWORD di .env"

    try:
        search_str = _build_search_criteria(unread_only, search, since, before)
    except ValueError as e:
        return f"Error: {e}"

    limit = max(1, min(int(limit or 10), MAX_EMAIL_LIMIT))

    try:
        def _read_emails():
            """Synchronous email reading (runs in thread)."""
            mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
            mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            mail.select(folder)

            # Search emails
            status, message_ids = mail.search(None, search_str)

            if status != "OK":
                return "Error: Gagal mencari email"

            ids = message_ids[0].split()

            if not ids:
                return f"Tidak ditemukan email di folder {folder}"

            # Get latest emails
            ids = ids[-limit:]
            ids.reverse()

            result = f"📧 Email dari folder '{folder}' ({len(ids)} email):\n\n"

            for msg_id in ids:
                status, msg_data = mail.fetch(msg_id, "(RFC822)")

                if status != "OK":
                    continue

                msg = email.message_from_bytes(msg_data[0][1])

                subject = _decode_mime_header(msg["Subject"])
                from_addr = _decode_mime_header(msg["From"])
                date_str = msg["Date"]

                # Get body preview
                body = _get_email_body(msg)
                body_preview = body[:200] + "..." if len(body) > 200 else body

                result += f"{'─' * 50}\n"
                result += f"📨 Dari: {from_addr}\n"
                result += f"📋 Subject: {subject}\n"
                result += f"📅 Tanggal: {date_str}\n"
                result += f"💬 Preview: {body_preview}\n\n"

            mail.logout()
            return result

        return await asyncio.to_thread(_read_emails)

    except imaplib.IMAP4.error as e:
        return f"Error IMAP: {str(e)}"
    except Exception as e:
        return f"Error saat baca email: {str(e)}"


@registry.tool(
    name="email_send",
    description="Kirim email baru.",
    input_schema={
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Alamat email penerima"
            },
            "subject": {
                "type": "string",
                "description": "Subject email"
            },
            "body": {
                "type": "string",
                "description": "Isi email"
            },
            "cc": {
                "type": "string",
                "description": "CC (opsional, pisahkan dengan koma)"
            }
        },
        "required": ["to", "subject", "body"]
    }
)
async def email_send(
    to: str,
    subject: str,
    body: str,
    cc: str = None
) -> str:
    """
    Send an email.

    Args:
        to: Recipient address
        subject: Email subject
        body: Email body
        cc: CC addresses (comma-separated)

    Returns:
        Send result
    """
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return "Error: Konfigurasi email belum diatur"

    try:
        def _send_email():
            """Synchronous email sending (runs in thread)."""
            msg = MIMEMultipart()
            msg["From"] = EMAIL_ADDRESS
            msg["To"] = to
            msg["Subject"] = subject

            if cc:
                msg["Cc"] = cc

            msg.attach(MIMEText(body, "plain", "utf-8"))

            # Build recipient list
            recipients = [to]
            if cc:
                recipients.extend([addr.strip() for addr in cc.split(",")])

            # Send email
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.send_message(msg, EMAIL_ADDRESS, recipients)

        await asyncio.to_thread(_send_email)
        return f"Email berhasil dikirim ke {to}" + (f" (CC: {cc})" if cc else "")

    except smtplib.SMTPException as e:
        return f"Error SMTP: {str(e)}"
    except Exception as e:
        return f"Error saat kirim email: {str(e)}"