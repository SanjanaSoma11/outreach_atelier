import os

import httpx


async def save_sent_email(
    person: str,
    company: str,
    role: str,
    email_address: str,
    linkedin_url: str,
    job_link: str,
) -> bool:
    """Save a sent email record to Notion. Returns True on success, raises RuntimeError on Notion API failure."""
    notion_key = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_DATABASE_ID")
    if not notion_key or not database_id:
        raise ValueError("NOTION_API_KEY and NOTION_DATABASE_ID must be set")

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {notion_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": person}}]},
            "Company": {"rich_text": [{"text": {"content": company}}]},
            "Role": {"rich_text": [{"text": {"content": role}}]},
            "Email": {"email": email_address or None},
            "LinkedIn URL": {"url": linkedin_url or None},
            "Job Link": {"url": job_link or None},
        },
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=payload, timeout=10)

    if r.status_code == 200:
        return True

    # Extract the most useful detail from Notion's error body
    try:
        body = r.json()
        code = body.get("code", "")
        message = body.get("message", "")
        detail = f"{code}: {message}" if code and message else (message or code or r.text[:300])
    except Exception:
        detail = r.text[:300] or f"HTTP {r.status_code}"

    raise RuntimeError(f"Notion API error {r.status_code} — {detail}")
