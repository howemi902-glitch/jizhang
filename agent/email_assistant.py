import base64
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from openai import OpenAI


@dataclass
class EmailItem:
    message_id: str
    thread_id: str
    subject: str
    sender: str
    received_at: str
    snippet: str
    body_text: str


@dataclass
class ClassifiedEmail:
    email: EmailItem
    needs_reply: bool
    importance: str
    reason: str
    suggested_reply: Optional[str]


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_emails (
            message_id TEXT PRIMARY KEY,
            processed_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def was_processed(conn: sqlite3.Connection, message_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM processed_emails WHERE message_id = ?", (message_id,)
    ).fetchone()
    return row is not None


def mark_processed(conn: sqlite3.Connection, message_id: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO processed_emails(message_id, processed_at) VALUES (?, ?)",
        (message_id, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def gmail_service() -> object:
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    return build("gmail", "v1", credentials=creds)


def _decode_payload(payload: dict) -> str:
    body_data = payload.get("body", {}).get("data")
    if body_data:
        return base64.urlsafe_b64decode(body_data.encode("utf-8")).decode(
            "utf-8", errors="ignore"
        )

    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data.encode("utf-8")).decode(
                    "utf-8", errors="ignore"
                )
    return ""


def _header(headers: list, name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def fetch_recent_emails(service, user_id: str, lookback_hours: int, max_emails: int) -> List[EmailItem]:
    after_ts = int((datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).timestamp())
    q = f"after:{after_ts}"

    response = (
        service.users()
        .messages()
        .list(userId=user_id, q=q, maxResults=max_emails)
        .execute()
    )
    messages = response.get("messages", [])

    results: List[EmailItem] = []
    for m in messages:
        msg = (
            service.users()
            .messages()
            .get(userId=user_id, id=m["id"], format="full")
            .execute()
        )
        payload = msg.get("payload", {})
        headers = payload.get("headers", [])

        date_raw = _header(headers, "Date")
        try:
            dt = parsedate_to_datetime(date_raw).astimezone(timezone.utc).isoformat()
        except Exception:
            dt = datetime.now(timezone.utc).isoformat()

        results.append(
            EmailItem(
                message_id=msg["id"],
                thread_id=msg.get("threadId", ""),
                subject=_header(headers, "Subject"),
                sender=_header(headers, "From"),
                received_at=dt,
                snippet=msg.get("snippet", ""),
                body_text=_decode_payload(payload)[:4000],
            )
        )

    return results


def classify_email(client: OpenAI, model: str, email: EmailItem) -> ClassifiedEmail:
    prompt = {
        "subject": email.subject,
        "sender": email.sender,
        "received_at": email.received_at,
        "snippet": email.snippet,
        "body_text": email.body_text,
    }

    completion = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "你是邮件助理。请判断邮件是否需要回复、重要程度(high/medium/low)，"
                    "并给出简短原因。如果需要回复，请给出中文回复草稿。"
                    "输出严格 JSON："
                    '{"needs_reply": bool, "importance": "high|medium|low", '
                    '"reason": string, "suggested_reply": string|null}'
                ),
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
    )

    text = completion.output_text.strip()
    data = json.loads(text)

    return ClassifiedEmail(
        email=email,
        needs_reply=bool(data.get("needs_reply", False)),
        importance=str(data.get("importance", "low")),
        reason=str(data.get("reason", "")),
        suggested_reply=data.get("suggested_reply"),
    )


def print_daily_report(items: List[ClassifiedEmail]) -> None:
    items_sorted = sorted(
        items,
        key=lambda x: (x.importance == "high", x.needs_reply),
        reverse=True,
    )

    print("\n=== 今日邮件摘要 ===")
    print(f"总计处理：{len(items_sorted)}\n")

    print("=== 重要且需要回复 ===")
    key_items = [i for i in items_sorted if i.needs_reply and i.importance in {"high", "medium"}]
    if not key_items:
        print("无")
    for idx, item in enumerate(key_items, start=1):
        print(f"\n[{idx}] {item.email.subject}")
        print(f"发件人: {item.email.sender}")
        print(f"时间: {item.email.received_at}")
        print(f"原因: {item.reason}")
        if item.suggested_reply:
            print(f"建议回复: {item.suggested_reply}")

    print("\n=== 其他邮件简报 ===")
    for item in items_sorted:
        print(f"- ({item.importance}) {item.email.subject} | {item.email.sender}")


def main() -> None:
    load_dotenv()
    required = [
        "OPENAI_API_KEY",
        "GMAIL_CLIENT_ID",
        "GMAIL_CLIENT_SECRET",
        "GMAIL_REFRESH_TOKEN",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing env vars: {', '.join(missing)}")

    db_path = os.getenv("SQLITE_PATH", "agent_state.db")
    lookback_hours = int(os.getenv("LOOKBACK_HOURS", "24"))
    max_emails = int(os.getenv("MAX_EMAILS", "50"))
    user = os.getenv("GMAIL_USER", "me")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    conn = init_db(db_path)
    service = gmail_service()
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    emails = fetch_recent_emails(service, user, lookback_hours, max_emails)
    fresh = [e for e in emails if not was_processed(conn, e.message_id)]

    results: List[ClassifiedEmail] = []
    for email in fresh:
        classified = classify_email(client, model, email)
        results.append(classified)
        mark_processed(conn, email.message_id)

    print_daily_report(results)


if __name__ == "__main__":
    main()
