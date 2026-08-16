#!/usr/bin/env python3
"""FRKN subscription bot: create temp mailbox -> register on frkn.org ->
parse Subscription ID from email -> publish link in sub.json + index.html."""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid

MAILTM_API = "https://api.mail.tm"
FRKN_API = "https://api.frkn.org"
SUB_BASE = "https://sub.frkn.org"

POLL_INTERVAL_SEC = 20
POLL_TIMEOUT_SEC = 300
REQUEST_RETRIES = 4
REQUEST_BACKOFF_SEC = 5

SUB_JSON = "sub.json"
INDEX_HTML = "index.html"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def http_request(
    url,
    method="GET",
    body=None,
    headers=None,
    retries=REQUEST_RETRIES,
):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    if data is not None:
        req_headers["Content-Type"] = "application/json"
    if headers:
        req_headers.update(headers)

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(
                url, data=data, headers=req_headers, method=method
            )
            with urllib.request.urlopen(request, timeout=30) as resp:
                raw = resp.read()
                try:
                    return resp.status, json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    return resp.status, raw.decode("utf-8")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_err = exc
            if attempt < retries:
                time.sleep(REQUEST_BACKOFF_SEC * attempt)
    raise RuntimeError(f"Request failed for {url}: {last_err}")


def mailtm_get_domain():
    status, data = http_request(f"{MAILTM_API}/domains")
    if status != 200:
        raise RuntimeError(f"mail.tm: failed to get domains (HTTP {status})")
    if isinstance(data, dict):
        if data.get("domain") and data.get("isActive"):
            return data["domain"]
        data = data.get("hydra:member", [])
    if isinstance(data, list):
        for d in data:
            if d.get("isActive"):
                domain = d.get("domain")
                if domain:
                    return domain
    raise RuntimeError("mail.tm: no active domain found")


def mailtm_create_account(address, password):
    status, data = http_request(
        f"{MAILTM_API}/accounts",
        method="POST",
        body={"address": address, "password": password},
    )
    if status not in (200, 201):
        raise RuntimeError(
            f"mail.tm: failed to create account (HTTP {status}): {data}"
        )
    return data


def mailtm_token(address, password):
    status, data = http_request(
        f"{MAILTM_API}/token",
        method="POST",
        body={"address": address, "password": password},
    )
    if status != 200:
        raise RuntimeError(f"mail.tm: auth failed (HTTP {status}): {data}")
    return data["token"]


def mailtm_messages(token):
    status, data = http_request(
        f"{MAILTM_API}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    if status != 200:
        raise RuntimeError(f"mail.tm: list messages failed (HTTP {status})")
    if isinstance(data, list):
        return data
    return data.get("hydra:member", [])


def mailtm_message(token, message_id):
    status, data = http_request(
        f"{MAILTM_API}/messages/{message_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if status != 200:
        raise RuntimeError(
            f"mail.tm: get message failed (HTTP {status}): {data}"
        )
    return data


def frkn_register(email):
    status, data = http_request(
        f"{FRKN_API}/account",
        method="POST",
        body={"email": email, "language": "ru", "trial": True},
    )
    if status not in (200, 201):
        raise RuntimeError(f"frkn: registration failed (HTTP {status}): {data}")
    return data


def parse_subscription_id(email_text):
    if not email_text:
        return None
    patterns = [
        r"Subscription\s*ID\s*[:#]?\s*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
        r"Subscription\s*ID\s*[:#]?\s*([A-Za-z0-9-]{10,})",
        r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
    ]
    for pattern in patterns:
        match = re.search(pattern, email_text, re.IGNORECASE | re.DOTALL)
        if match:
            candidate = match.group(1).strip()
            if len(candidate) >= 10:
                return candidate
    return None


def wait_for_subscription_id(token, timeout=POLL_TIMEOUT_SEC):
    deadline = time.time() + timeout
    seen = set()
    fallback_id = None
    fallback_full = None
    while time.time() < deadline:
        messages = mailtm_messages(token)
        for msg in messages:
            mid = msg.get("id")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            sender = str(msg.get("from", {})).lower()
            full = mailtm_message(token, mid)
            body = (
                (full.get("text") or "")
                + "\n"
                + (full.get("html") or "")
                + "\n"
                + str(full.get("intro") or "")
            )
            sub_id = parse_subscription_id(body)
            if not sub_id:
                continue
            if "frkn" in sender:
                return sub_id, full
            if fallback_id is None:
                fallback_id, fallback_full = sub_id, full
        time.sleep(POLL_INTERVAL_SEC)
    return fallback_id, fallback_full


def load_existing():
    if not os.path.exists(SUB_JSON):
        return None
    try:
        with open(SUB_JSON, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def render_index_html(link, email, updated_at, sub_id):
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FRKN — ссылка подписки</title>
<style>
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f1115; color: #e8eaf0; margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
  .card {{ background: #1a1d24; border: 1px solid #2a2f3a; border-radius: 16px; padding: 40px; max-width: 560px; width: 90%; text-align: center; }}
  h1 {{ font-size: 22px; margin: 0 0 8px; }}
  .sub {{ color: #8b93a7; margin: 0 0 24px; }}
  .link {{ background: #0f1115; border: 1px solid #2a2f3a; border-radius: 10px; padding: 14px 16px; word-break: break-all; font-family: monospace; color: #7fb3ff; margin-bottom: 16px; }}
  .btn {{ background: #2f6feb; color: #fff; border: none; border-radius: 10px; padding: 12px 20px; font-size: 14px; cursor: pointer; }}
  .btn:hover {{ background: #245cd6; }}
  .meta {{ margin-top: 20px; font-size: 12px; color: #8b93a7; line-height: 1.6; }}
  .ok {{ color: #3ecf8e; }}
  .err {{ color: #ff6b6b; }}
</style>
</head>
<body>
<div class="card">
  <h1>🎛 FRKN подписка</h1>
  <p class="sub">Актуальная ссылка подписки (тест-драйв)</p>
  <div class="link" id="subLink">{link}</div>
  <button class="btn" onclick="copyLink()">Копировать</button>
  <div class="meta">
    ID: <span class="ok">{sub_id}</span><br>
    Почта: <span class="ok">{email}</span><br>
    Обновлено: <span class="ok">{updated_at}</span>
  </div>
</div>
<script>
  function copyLink() {{
    navigator.clipboard.writeText(document.getElementById('subLink').textContent)
      .then(() => {{ const b = document.querySelector('.btn'); b.textContent = 'Скопировано!'; setTimeout(() => b.textContent = 'Копировать', 1500); }});
  }}
</script>
</body>
</html>
"""


def main():
    existing = load_existing()
    current_id = (existing or {}).get("subscription_id")
    if current_id:
        print(f"Current subscription ID: {current_id}")

    domain = mailtm_get_domain()
    address = f"frkn.{uuid.uuid4().hex[:16]}@{domain}"
    password = uuid.uuid4().hex
    print(f"Temp mailbox: {address}")

    account = mailtm_create_account(address, password)
    address = account["address"]
    print(f"Temp mailbox (normalized): {address}")
    token = mailtm_token(address, password)

    print("Registering on frkn.org ...")
    api_resp = frkn_register(address)
    api_id = (api_resp or {}).get("subscription_id")
    if api_id:
        print(f"API returned subscription_id: {api_id}")

    print("Waiting for email with Subscription ID ...")
    sub_id, email_full = wait_for_subscription_id(token)
    if not sub_id and api_id:
        print("Email not found, falling back to API subscription_id")
        sub_id = api_id

    if not sub_id:
        print("ERROR: could not obtain subscription ID", file=sys.stderr)
        sys.exit(1)

    print(f"Subscription ID: {sub_id}")
    link = f"{SUB_BASE}/{sub_id}"

    if sub_id == current_id:
        print("Subscription ID unchanged, nothing to update")
        return

    email_addr = email_full.get("from", {}).get("address", address) if email_full else address
    updated_at = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    payload = {
        "subscription_id": sub_id,
        "link": link,
        "email": email_addr,
        "updated_at": updated_at,
    }
    with open(SUB_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    with open(INDEX_HTML, "w", encoding="utf-8") as fh:
        fh.write(
            render_index_html(
                link=link,
                email=email_addr,
                updated_at=updated_at,
                sub_id=sub_id,
            )
        )

    print(f"Saved: {link}")
    print(f"Saved: {SUB_JSON} and {INDEX_HTML}")


if __name__ == "__main__":
    main()
