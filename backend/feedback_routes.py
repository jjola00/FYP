import hmac
import json
import os
import uuid
from pathlib import Path
from typing import List

import httpx
import fastapi
from fastapi import File, Form, Request, UploadFile

from . import db, models
from .rate_limit import feedback_limiter

router = fastapi.APIRouter()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
FEEDBACK_SECRET = os.getenv("FEEDBACK_SECRET", "change-me")
FEEDBACK_IMAGES_DIR = Path("data/feedback_images")
MAX_IMAGES = 3
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB per image


@router.post("/feedback")
async def submit_feedback(
    request: Request,
    message: str = Form(...),
    category: str = Form(...),
    device: str = Form(...),
    name: str = Form(""),
    images: List[UploadFile] = File(default=[]),
):
    client_ip = request.client.host if request.client else "unknown"
    feedback_limiter.check(client_ip)

    category = category.strip()
    device = device.strip()
    if category not in ("line", "image", "both"):
        raise fastapi.HTTPException(status_code=400, detail="Invalid category")
    if device not in ("phone", "laptop", "tablet"):
        raise fastapi.HTTPException(status_code=400, detail="Invalid device type")
    if not message.strip():
        raise fastapi.HTTPException(status_code=400, detail="Message is required")
    if len(message) > 2000:
        raise fastapi.HTTPException(status_code=400, detail="Message too long (max 2000 chars)")
    if len(images) > MAX_IMAGES:
        raise fastapi.HTTPException(status_code=400, detail=f"Max {MAX_IMAGES} images allowed")

    feedback_id = uuid.uuid4().hex
    saved_filenames: List[str] = []

    # Save uploaded images
    if images:
        FEEDBACK_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        for img in images:
            if not img.filename:
                continue
            # Read in chunks to reject oversized uploads early
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = await img.read(1024 * 64)  # 64KB chunks
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_IMAGE_SIZE_BYTES:
                    raise fastapi.HTTPException(status_code=400, detail="Image too large (max 10 MB)")
                chunks.append(chunk)
            content = b"".join(chunks)
            if not content:
                continue
            if not img.content_type or not img.content_type.startswith("image/"):
                raise fastapi.HTTPException(status_code=400, detail="Only image files are allowed")
            ext = Path(img.filename).suffix or ".png"
            filename = f"{feedback_id}_{len(saved_filenames)}{ext}"
            filepath = FEEDBACK_IMAGES_DIR / filename
            filepath.write_bytes(content)
            saved_filenames.append(filename)

    clean_name = name.strip() or None

    db.save_feedback(
        feedback_id=feedback_id,
        name=clean_name,
        category=category,
        device=device,
        message=message.strip(),
        image_filenames=saved_filenames,
    )

    # Send Discord webhook notification
    discord_sent = False
    discord_error = None
    if DISCORD_WEBHOOK_URL:
        discord_sent, discord_error = await _send_discord_notification(
            feedback_id=feedback_id,
            name=clean_name,
            category=category,
            device=device,
            message=message.strip(),
            image_filenames=saved_filenames,
        )
    else:
        discord_error = "DISCORD_WEBHOOK_URL not set"

    return {"ok": True, "feedbackId": feedback_id, "discordSent": discord_sent, "discordError": discord_error}


@router.get("/feedback")
def list_feedback(secret: str = ""):
    if not hmac.compare_digest(secret, FEEDBACK_SECRET):
        raise fastapi.HTTPException(status_code=403, detail="Forbidden")
    rows = db.get_all_feedback()
    items = []
    for row in rows:
        items.append(
            models.FeedbackItem(
                id=row["id"],
                name=row["name"],
                category=row["category"],
                device=row.get("device", "unknown") if isinstance(row, dict) else (row["device"] if "device" in row.keys() else "unknown"),
                message=row["message"],
                imageFilenames=json.loads(row["image_filenames_json"]),
                createdAt=row["created_at"],
            )
        )
    return items


@router.get("/feedback/images/{filename}")
def get_feedback_image(filename: str, secret: str = ""):
    if not hmac.compare_digest(secret, FEEDBACK_SECRET):
        raise fastapi.HTTPException(status_code=403, detail="Forbidden")
    filepath = FEEDBACK_IMAGES_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise fastapi.HTTPException(status_code=404, detail="Image not found")
    # Prevent path traversal
    if filepath.resolve().parent != FEEDBACK_IMAGES_DIR.resolve():
        raise fastapi.HTTPException(status_code=400, detail="Invalid filename")
    return fastapi.responses.FileResponse(filepath)


async def _send_discord_notification(
    feedback_id: str,
    name: str | None,
    category: str,
    device: str,
    message: str,
    image_filenames: List[str],
) -> tuple[bool, str | None]:
    embed = {
        "title": "New Feedback",
        "color": 0x5865F2,  # Discord blurple
        "fields": [
            {"name": "From", "value": name or "Anonymous", "inline": True},
            {"name": "Category", "value": category.title(), "inline": True},
            {"name": "Device", "value": device.title(), "inline": True},
            {"name": "Message", "value": message[:1024]},
        ],
        "footer": {"text": f"ID: {feedback_id}"},
    }
    if image_filenames:
        embed["fields"].append(
            {"name": "Attachments", "value": f"{len(image_filenames)} image(s)", "inline": True}
        )

    payload = {"embeds": [embed]}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # If there are images, send them as attachments
            if image_filenames:
                files = []
                for fname in image_filenames:
                    fpath = FEEDBACK_IMAGES_DIR / fname
                    if fpath.exists():
                        files.append(
                            ("files", (fname, fpath.read_bytes(), "image/png"))
                        )
                resp = await client.post(
                    DISCORD_WEBHOOK_URL,
                    data={"payload_json": json.dumps(payload)},
                    files=files,
                )
            else:
                resp = await client.post(
                    DISCORD_WEBHOOK_URL,
                    json=payload,
                )
            if resp.status_code in (200, 204):
                return True, None
            return False, f"Discord returned {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, str(e)
