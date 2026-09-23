from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

BEGIN = "# === CORPORATION_REQUIRED_CHANNEL_V32_BEGIN ==="
END = "# === CORPORATION_REQUIRED_CHANNEL_V32_END ==="


def strip_old_block(text: str) -> str:
    if BEGIN not in text:
        return text
    start = text.index(BEGIN)
    end = text.find(END, start)
    if end < 0:
        raise RuntimeError("Found v32 begin marker without end marker in app.py")
    end += len(END)
    return (text[:start].rstrip() + "\n\n" + text[end:].lstrip()).rstrip() + "\n"


def detect_fastapi_name(text: str) -> str:
    match = re.search(r"(?m)^\s*([A-Za-z_]\w*)\s*=\s*FastAPI\s*\(", text)
    if not match:
        raise RuntimeError("FastAPI application variable was not found in app.py")
    return match.group(1)


def build_block(app_name: str) -> str:
    return f'''{BEGIN}
# Required Telegram channel membership for Corporation.
# Uses the existing verified Telegram identity from user_from_request and then
# checks membership through Bot API getChatMember. Positive results are cached
# briefly to avoid one Telegram API request per in-game action.
import json as _v32_json
import os as _v32_os
import time as _v32_time
from urllib.parse import urlencode as _v32_urlencode
from urllib.request import Request as _V32UrlRequest, urlopen as _v32_urlopen
from fastapi import Header as _V32Header, HTTPException as _V32HTTPException

_V32_REQUIRED_CHANNEL = (_v32_os.getenv("REQUIRED_CHANNEL") or "").strip()
try:
    _V32_CACHE_SECONDS = max(30, int(_v32_os.getenv("SUBSCRIPTION_CACHE_SECONDS", "300")))
except ValueError:
    _V32_CACHE_SECONDS = 300
_V32_POSITIVE_CACHE = {{}}


def _v32_channel_url():
    channel = _V32_REQUIRED_CHANNEL
    if channel.startswith("@") and len(channel) > 1:
        return "https://t.me/" + channel[1:]
    return ""


def _v32_get_chat_member(user_id: int):
    if not _V32_REQUIRED_CHANNEL:
        raise _V32HTTPException(
            status_code=503,
            detail="REQUIRED_CHANNEL is not configured on the server.",
        )
    token = str(globals().get("BOT_TOKEN") or _v32_os.getenv("BOT_TOKEN") or "").strip()
    if not token or "PASTE_YOUR_BOT_TOKEN" in token:
        raise _V32HTTPException(
            status_code=503,
            detail="BOT_TOKEN is not configured on the server.",
        )
    query = _v32_urlencode({{"chat_id": _V32_REQUIRED_CHANNEL, "user_id": int(user_id)}})
    url = f"https://api.telegram.org/bot{{token}}/getChatMember?{{query}}"
    request = _V32UrlRequest(url, headers={{"User-Agent": "Corporation-v32"}})
    try:
        with _v32_urlopen(request, timeout=5) as response:
            payload = _v32_json.loads(response.read().decode("utf-8"))
    except Exception:
        raise _V32HTTPException(
            status_code=503,
            detail="Не удалось проверить подписку через Telegram. Попробуйте ещё раз.",
        )
    if not payload.get("ok") or not isinstance(payload.get("result"), dict):
        raise _V32HTTPException(
            status_code=503,
            detail="Telegram не подтвердил проверку подписки. Проверьте, что бот — администратор канала.",
        )
    return payload["result"]


def _v32_is_subscribed(user_id: int, force: bool = False) -> bool:
    user_id = int(user_id)
    now = _v32_time.time()
    cached_until = _V32_POSITIVE_CACHE.get(user_id, 0)
    if not force and cached_until > now:
        return True

    member = _v32_get_chat_member(user_id)
    status = str(member.get("status") or "")
    subscribed = status in {{"creator", "administrator", "member"}} or (
        status == "restricted" and bool(member.get("is_member"))
    )

    if subscribed:
        _V32_POSITIVE_CACHE[user_id] = now + _V32_CACHE_SECONDS
    else:
        _V32_POSITIVE_CACHE.pop(user_id, None)
    return subscribed


# Keep the project's existing Telegram initData validation as the source of
# identity. We only add the channel-membership requirement on top of it.
_v32_base_user_from_request = user_from_request


def user_from_request(x_telegram_init_data, x_user_id):
    # Never trust X-User-Id for the subscription gate in production.
    # It is allowed only for an explicitly enabled local-development bypass.
    is_dev_request = not x_telegram_init_data and bool(x_user_id)
    dev_bypass = (
        is_dev_request
        and _v32_os.getenv("ALLOW_DEV_AUTH") == "1"
        and _v32_os.getenv("ALLOW_SUBSCRIPTION_DEV_BYPASS") == "1"
    )
    if not x_telegram_init_data and not dev_bypass:
        raise _V32HTTPException(
            status_code=401,
            detail="Откройте Corporation через Telegram-бота.",
        )

    identity = _v32_base_user_from_request(x_telegram_init_data, x_user_id)
    user_id = int(identity[0])
    if dev_bypass:
        return identity

    if not _v32_is_subscribed(user_id):
        raise _V32HTTPException(
            status_code=403,
            detail="Для входа в Corporation подпишитесь на официальный Telegram-канал.",
        )
    return identity


@{app_name}.get("/api/subscription/check")
def subscription_check_v32(
    x_telegram_init_data: str | None = _V32Header(None),
    x_user_id: str | None = _V32Header(None),
):
    is_dev_request = not x_telegram_init_data and bool(x_user_id)
    dev_bypass = (
        is_dev_request
        and _v32_os.getenv("ALLOW_DEV_AUTH") == "1"
        and _v32_os.getenv("ALLOW_SUBSCRIPTION_DEV_BYPASS") == "1"
    )
    if not x_telegram_init_data and not dev_bypass:
        raise _V32HTTPException(
            status_code=401,
            detail="Откройте Corporation через Telegram-бота.",
        )

    identity = _v32_base_user_from_request(x_telegram_init_data, x_user_id)
    user_id = int(identity[0])
    subscribed = True if dev_bypass else _v32_is_subscribed(user_id, force=True)
    return {{
        "ok": True,
        "subscribed": subscribed,
        "channel": _V32_REQUIRED_CHANNEL,
        "channel_url": _v32_channel_url(),
        "cache_seconds": _V32_CACHE_SECONDS,
    }}
{END}
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    app_path = project / "app.py"
    if not app_path.is_file():
        raise SystemExit(f"app.py not found: {app_path}")

    text = app_path.read_text(encoding="utf-8-sig")
    text = strip_old_block(text)

    if not re.search(r"(?m)^\s*def\s+user_from_request\s*\(", text):
        raise SystemExit("user_from_request() was not found in app.py; update aborted safely")

    app_name = detect_fastapi_name(text)
    patched = text.rstrip() + "\n\n" + build_block(app_name)

    try:
        ast.parse(patched, filename=str(app_path))
    except SyntaxError as exc:
        raise SystemExit(f"Patched app.py is invalid Python: {exc}") from exc

    app_path.write_text(patched, encoding="utf-8", newline="\n")
    print(f"Patched {app_path.name}; FastAPI variable: {app_name}")


if __name__ == "__main__":
    main()
