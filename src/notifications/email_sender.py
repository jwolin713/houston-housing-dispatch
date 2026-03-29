"""Email sender for approval notifications."""

from typing import Optional

import resend
import structlog

from src.config import get_settings

logger = structlog.get_logger()


class EmailSender:
    """Sends notification emails via Resend."""

    def __init__(self):
        self.settings = get_settings()
        resend.api_key = self.settings.resend_api_key

    def send_approval_email(
        self,
        newsletter_id: int,
        title: str,
        preview_html: str,
        approve_url: str,
        reject_url: str,
        preview_url: str,
    ) -> bool:
        """
        Send an approval email for a newsletter.

        Args:
            newsletter_id: ID of the newsletter
            title: Newsletter title
            preview_html: HTML preview of the newsletter
            approve_url: URL for approve action
            reject_url: URL for reject action
            preview_url: URL for full preview

        Returns:
            True if sent successfully
        """
        html_content = self._render_approval_email(
            title=title,
            preview_html=preview_html,
            approve_url=approve_url,
            reject_url=reject_url,
            preview_url=preview_url,
        )

        try:
            response = resend.Emails.send({
                "from": "Houston Housing Dispatch <noreply@resend.dev>",
                "to": [self.settings.notification_email],
                "subject": f"[Approve?] {title}",
                "html": html_content,
            })

            logger.info(
                "Approval email sent",
                newsletter_id=newsletter_id,
                to=self.settings.notification_email,
                email_id=response.get("id"),
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to send approval email",
                newsletter_id=newsletter_id,
                error=str(e),
            )
            return False

    def send_alert_email(
        self,
        subject: str,
        message: str,
        details: Optional[dict] = None,
    ) -> bool:
        """
        Send an alert email (errors, warnings, etc.).

        Args:
            subject: Email subject
            message: Main message
            details: Optional dict of details

        Returns:
            True if sent successfully
        """
        details_html = ""
        if details:
            details_html = "<ul>" + "".join(
                f"<li><strong>{k}:</strong> {v}</li>"
                for k, v in details.items()
            ) + "</ul>"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .alert {{
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .details {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <h1>Houston Housing Dispatch Alert</h1>
    <div class="alert">
        <p>{message}</p>
    </div>
    {f'<div class="details">{details_html}</div>' if details_html else ''}
</body>
</html>
"""

        try:
            response = resend.Emails.send({
                "from": "Houston Housing Dispatch <noreply@resend.dev>",
                "to": [self.settings.notification_email],
                "subject": f"[Alert] {subject}",
                "html": html_content,
            })

            logger.info(
                "Alert email sent",
                subject=subject,
                email_id=response.get("id"),
            )
            return True

        except Exception as e:
            logger.error("Failed to send alert email", subject=subject, error=str(e))
            return False

    def _render_approval_email(
        self,
        title: str,
        preview_html: str,
        approve_url: str,
        reject_url: str,
        preview_url: str,
    ) -> str:
        """Render the approval email HTML."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 700px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        .header {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .buttons {{
            margin: 30px 0;
            text-align: center;
        }}
        .btn {{
            display: inline-block;
            padding: 15px 30px;
            margin: 0 10px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
            font-size: 16px;
        }}
        .btn-approve {{
            background: #28a745;
            color: white !important;
        }}
        .btn-reject {{
            background: #dc3545;
            color: white !important;
        }}
        .btn-preview {{
            background: #6c757d;
            color: white !important;
        }}
        .preview {{
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            margin-top: 20px;
            max-height: 500px;
            overflow: auto;
        }}
        .preview-label {{
            background: #fff3cd;
            padding: 10px;
            margin: -20px -20px 20px -20px;
            border-radius: 5px 5px 0 0;
            font-size: 14px;
            color: #856404;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 style="margin: 0;">Newsletter Ready for Approval</h1>
        <p style="margin: 10px 0 0 0; color: #666;">{title}</p>
    </div>

    <p>A new newsletter draft is ready for your review. Click the buttons below to approve or reject.</p>

    <div class="buttons">
        <a href="{approve_url}" class="btn btn-approve">Approve & Publish</a>
        <a href="{reject_url}" class="btn btn-reject">Reject</a>
        <a href="{preview_url}" class="btn btn-preview">View Full Preview</a>
    </div>

    <div class="preview">
        <div class="preview-label">Preview (scroll for more)</div>
        {preview_html[:3000]}
        {'<p><em>... content truncated. Click "View Full Preview" for complete newsletter.</em></p>' if len(preview_html) > 3000 else ''}
    </div>

    <p style="color: #888; font-size: 12px; margin-top: 30px;">
        This link expires in 24 hours. If you don't respond, the draft will be archived.
    </p>
</body>
</html>
"""

    def send_instagram_approval_email(
        self,
        newsletter_id: int,
        caption: str,
        image_urls: list[str],
        approve_url: str,
        reject_url: str,
    ) -> bool:
        """Send an approval email for an Instagram post."""
        images_html = "".join(
            f'<img src="{url}" style="max-width: 200px; margin: 5px;" alt="Post image">'
            for url in image_urls[:4]
        )

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .instagram-preview {{
            background: #fafafa;
            border: 1px solid #dbdbdb;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        .caption {{
            white-space: pre-wrap;
            font-size: 14px;
            line-height: 1.5;
        }}
        .images {{
            margin: 15px 0;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .buttons {{
            text-align: center;
            margin: 30px 0;
        }}
        .btn {{
            display: inline-block;
            padding: 12px 24px;
            margin: 0 10px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
        }}
        .btn-approve {{ background: #28a745; color: white !important; }}
        .btn-reject {{ background: #dc3545; color: white !important; }}
    </style>
</head>
<body>
    <h1>Instagram Post Ready</h1>
    <p>An Instagram post has been generated for newsletter #{newsletter_id}.</p>

    <div class="instagram-preview">
        <div class="images">{images_html}</div>
        <div class="caption">{caption}</div>
    </div>

    <div class="buttons">
        <a href="{approve_url}" class="btn btn-approve">Approve & Post</a>
        <a href="{reject_url}" class="btn btn-reject">Skip</a>
    </div>
</body>
</html>
"""

        try:
            response = resend.Emails.send({
                "from": "Houston Housing Dispatch <noreply@resend.dev>",
                "to": [self.settings.notification_email],
                "subject": f"[Instagram] Post ready for Newsletter #{newsletter_id}",
                "html": html_content,
            })

            logger.info(
                "Instagram approval email sent",
                newsletter_id=newsletter_id,
                email_id=response.get("id"),
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to send Instagram approval email",
                newsletter_id=newsletter_id,
                error=str(e),
            )
            return False
