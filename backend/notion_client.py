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
    """Save a sent email record to Notion. Returns True on success."""
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
            "LinkedIn": {"url": linkedin_url or None},
            "Job Link": {"url": job_link or None},
        },
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=payload, timeout=10)

    return r.status_code == 200
