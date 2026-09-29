import asyncio
import smtplib
import ssl
from datetime import UTC, datetime
from email.message import EmailMessage
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.qa_reports.models import DailyReport
from app.modules.qa_reports.schemas import DeliveryOptions, Preview, SendInput
from app.modules.qa_reports.service import check_version, generate_preview, get_report


def delivery_options() -> DeliveryOptions:
    settings = get_settings()
    return DeliveryOptions(
        slack=bool(settings.slack_webhook_url.get_secret_value()),
        email=bool(settings.smtp_host and settings.smtp_from),
    )


def send_email(preview: Preview, recipient: str) -> None:
    settings = get_settings()
    message = EmailMessage()
    message["Subject"] = preview.title
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message.set_content(preview.slack)
    message.add_alternative(preview.html, subtype="html")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password.get_secret_value())
        smtp.send_message(message)


async def send_report(db: AsyncSession, report_id: UUID, body: SendInput) -> DailyReport:
    report = await get_report(db, report_id, lock=True)
    check_version(report, body.version, draft=False)
    if report.status == "draft":
        raise AppError(409, "Finalisasi laporan sebelum mengirim.")
    preview = generate_preview(report)
    options = delivery_options()
    already_sent = report.slack_sent_at if body.channel == "slack" else report.email_sent_at
    if already_sent:
        raise AppError(409, "Laporan ini sudah dikirim melalui kanal tersebut.")
    if body.channel == "slack":
        webhook = get_settings().slack_webhook_url.get_secret_value()
        parsed = urlsplit(webhook)
        if (
            not options.slack
            or parsed.scheme != "https"
            or parsed.hostname != "hooks.slack.com"
            or not parsed.path.startswith("/services/")
            or parsed.port not in (None, 443)
            or parsed.username
            or parsed.password
        ):
            raise AppError(422, "Webhook Slack belum dikonfigurasi dengan benar di server.")
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
                result = await client.post(webhook, json={"text": preview.slack, "mrkdwn": False})
                result.raise_for_status()
                if result.text.strip() != "ok":
                    raise AppError(502, "Slack tidak mengonfirmasi pengiriman.")
        except httpx.HTTPError:
            raise AppError(
                502,
                "Pengiriman Slack belum terkonfirmasi. Periksa kanal sebelum "
                "mencoba lagi untuk menghindari pesan ganda.",
            ) from None
        report.slack_sent_at = datetime.now(UTC)
    else:
        if not options.email or not body.recipient:
            raise AppError(422, "SMTP belum tersedia atau alamat penerima belum diisi.")
        try:
            await asyncio.to_thread(send_email, preview, str(body.recipient))
        except (OSError, smtplib.SMTPException, ValueError):
            raise AppError(
                502,
                "Pengiriman email belum terkonfirmasi. Periksa kotak terkirim "
                "sebelum mencoba lagi.",
            ) from None
        report.email_sent_at = datetime.now(UTC)
    report.status = "sent"
    report.version += 1
    await db.commit()
    await db.refresh(report, ["updated_at"])
    return report
