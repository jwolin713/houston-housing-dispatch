"""Approval workflow endpoints."""

from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.auth.tokens import TokenManager
from src.database import get_db
from src.models import Newsletter, NewsletterStatus
from src.workflows.approval import ApprovalWorkflow

logger = structlog.get_logger()
router = APIRouter()


class ApprovalResponse(BaseModel):
    """Response model for approval actions."""

    success: bool
    message: str
    newsletter_id: Optional[int] = None
    action: Optional[str] = None
    post_url: Optional[str] = None


@router.get("/newsletter/{token}")
async def approve_newsletter(
    token: str,
    action: str = Query(..., regex="^(approve|reject)$"),
    feedback: Optional[str] = Query(None),
):
    """
    Handle newsletter approval/rejection via magic link.

    Args:
        token: Signed approval token
        action: 'approve' or 'reject'
        feedback: Optional rejection feedback
    """
    logger.info("Approval request received", action=action)

    # Verify token
    token_manager = TokenManager()
    token_data = token_manager.verify_token(token)

    if not token_data:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired approval link. Please request a new one.",
        )

    newsletter_id = token_data.get("id")
    if not newsletter_id:
        raise HTTPException(status_code=400, detail="Invalid token data")

    # Process approval/rejection
    workflow = ApprovalWorkflow()

    with get_db() as db:
        newsletter = db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()

        if not newsletter:
            raise HTTPException(status_code=404, detail="Newsletter not found")

        # Check if already processed (optimistic locking)
        if newsletter.status not in [
            NewsletterStatus.DRAFT,
            NewsletterStatus.PENDING_APPROVAL,
        ]:
            return HTMLResponse(
                content=_render_already_processed_page(newsletter),
                status_code=200,
            )

        if action == "approve":
            result = workflow.approve(db, newsletter)
        else:
            result = workflow.reject(db, newsletter, feedback=feedback)

    if result["success"]:
        return HTMLResponse(
            content=_render_success_page(action, result),
            status_code=200,
        )
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


@router.get("/preview/{newsletter_id}")
async def preview_newsletter(newsletter_id: int):
    """Preview a newsletter before approval."""
    with get_db() as db:
        newsletter = db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()

        if not newsletter:
            raise HTTPException(status_code=404, detail="Newsletter not found")

        return HTMLResponse(
            content=_render_preview_page(newsletter),
            status_code=200,
        )


def _render_success_page(action: str, result: dict) -> str:
    """Render a success confirmation page."""
    if action == "approve":
        title = "Newsletter Published!"
        message = "Your newsletter has been published to Substack."
        if result.get("post_url"):
            message += f'<br><br><a href="{result["post_url"]}">View Published Post</a>'
    else:
        title = "Newsletter Rejected"
        message = "The newsletter draft has been archived. A new draft will be generated tomorrow."

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 100px auto;
            padding: 20px;
            text-align: center;
        }}
        .success {{ color: #28a745; }}
        .reject {{ color: #dc3545; }}
        h1 {{ font-size: 32px; }}
        p {{ font-size: 18px; color: #666; }}
        a {{ color: #007bff; }}
    </style>
</head>
<body>
    <h1 class="{'success' if action == 'approve' else 'reject'}">{title}</h1>
    <p>{message}</p>
</body>
</html>
"""


def _render_already_processed_page(newsletter: Newsletter) -> str:
    """Render a page for already processed newsletters."""
    status = newsletter.status.value.replace("_", " ").title()

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Already Processed</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 100px auto;
            padding: 20px;
            text-align: center;
        }}
        h1 {{ font-size: 28px; color: #666; }}
        p {{ font-size: 16px; color: #888; }}
    </style>
</head>
<body>
    <h1>Already Processed</h1>
    <p>This newsletter has already been {status.lower()}.</p>
    <p>Current status: <strong>{status}</strong></p>
</body>
</html>
"""


def _render_preview_page(newsletter: Newsletter) -> str:
    """Render a preview page for a newsletter."""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Preview: {newsletter.title}</title>
    <style>
        body {{
            font-family: Georgia, serif;
            max-width: 700px;
            margin: 0 auto;
            padding: 20px;
        }}
        .preview-banner {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }}
        .content {{ line-height: 1.6; }}
        hr {{ border: none; border-top: 1px solid #ddd; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="preview-banner">
        <strong>Preview Mode</strong> - This newsletter is pending approval.
    </div>
    <h1>{newsletter.title}</h1>
    <div class="content">
        {newsletter.content_html or newsletter.content_markdown or 'No content'}
    </div>
</body>
</html>
"""
