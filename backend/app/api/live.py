"""WebSocket for live feedback. Audio in, stats out. Nothing is saved."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.services.live import LiveTranscriber, whisper_transcribe_fn

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/live", tags=["live"])

LIVE_MODEL = "tiny"
MAX_MESSAGE_BYTES = 64 * 1024  # about 2 s of 16 kHz int16 audio


@router.websocket("/ws")
async def live_ws(ws: WebSocket, lang: str = "en") -> None:
    from app.db.session import get_sessionmaker
    from app.services import auth

    db = get_sessionmaker()()
    try:
        signed_in = auth.user_for_token(db, ws.cookies.get(auth.COOKIE_NAME)) is not None
    finally:
        db.close()
    if not signed_in:
        await ws.close(code=4401, reason="not signed in")
        return
    await ws.accept()
    settings = get_settings()
    loop = asyncio.get_running_loop()
    try:
        fn = await loop.run_in_executor(
            None, whisper_transcribe_fn, LIVE_MODEL, str(settings.models_dir), lang
        )
    except Exception:
        log.exception("could not load live model")
        await ws.send_json({"type": "error", "message": "The live speech model could not load."})
        await ws.close()
        return

    live = LiveTranscriber(transcribe=fn, language=lang)
    await ws.send_json({"type": "ready"})
    busy = False

    async def process(final: bool = False) -> None:
        nonlocal busy
        busy = True
        try:
            while await loop.run_in_executor(None, live.step, final) and final:
                pass
        finally:
            busy = False
        await ws.send_json(live.stats().as_dict())

    task: asyncio.Task[None] | None = None
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if (data := msg.get("bytes")) is not None:
                if len(data) > MAX_MESSAGE_BYTES or len(data) % 2:
                    continue
                live.feed(data)
                if not busy and live.ready():
                    task = asyncio.create_task(process())
                elif not busy:
                    await ws.send_json(live.stats().as_dict())
            elif msg.get("text") == "stop":
                if task:
                    await task
                await process(final=True)
                await ws.send_json({"type": "done"})
                break
    except WebSocketDisconnect:
        pass
    finally:
        if task and not task.done():
            task.cancel()
        with contextlib.suppress(Exception):
            await ws.close()
