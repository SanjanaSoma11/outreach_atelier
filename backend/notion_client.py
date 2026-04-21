import os
from typing import Any

import httpx


def _rich_text(content: str) -> list[dict]:
    return [{"type": "text", "text": {"content": content[:2000]}}]


async def save_sent_email(
    person: str,
    company: str = "",
    role: str = "",
    contact_method: str = "",
    email_address: str = "",
    linkedin_url: str = "",
    job_link: str = "",
    tone: str = "",
    provider: str = "",
) -> bool:
    """Save minimal outreach metadata to Notion. Returns True on success."""
    notion_key = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_DATABASE_ID")
    if not notion_key or not database_id:
        raise ValueError("NOTION_API_KEY and NOTION_DATABASE_ID must be set")

    properties: dict[str, Any] = {
        "Name": {"title": _rich_text(person or "—")},
        "Company": {"rich_text": _rich_text(company)},
        "Role": {"rich_text": _rich_text(role)},
        "Email": {"email": email_address or None},
        "LinkedIn URL": {"url": linkedin_url or None},
        "Job Link": {"url": job_link or None},
    }
    if contact_method:
        properties["Contact Method"] = {"select": {"name": contact_method}}
    if tone:
        properties["Tone"] = {"select": {"name": tone}}
    if provider:
        properties["Provider"] = {"select": {"name": provider}}

    payload: dict[str, Any] = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {notion_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=payload, timeout=10)

    if r.status_code == 200:
        return True

    try:
        body = r.json()
        code = body.get("code", "")
        message = body.get("message", "")
        detail = f"{code}: {message}" if code and message else (message or code or r.text[:300])
    except Exception:
        detail = r.text[:300] or f"HTTP {r.status_code}"

    raise RuntimeError(f"Notion API error {r.status_code} — {detail}")
