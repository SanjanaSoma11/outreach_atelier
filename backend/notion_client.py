import os
import re
from typing import Any

import httpx

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"


def _rich_text(content: str) -> list[dict]:
    return [{"type": "text", "text": {"content": content[:2000]}}]


def _notion_id(value: str) -> str:
    """Accept a bare Notion ID or URL and return the first page/database ID."""
    value = (value or "").strip()
    if not value:
        return ""
    hyphenated = re.search(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        value,
    )
    if hyphenated:
        return hyphenated.group(0)
    compact = re.search(r"[0-9a-fA-F]{32}", value)
    return compact.group(0) if compact else value


def _notion_api_error(response: httpx.Response) -> RuntimeError:
    try:
        body = response.json()
        code = body.get("code", "")
        message = body.get("message", "")
        detail = f"{code}: {message}" if code and message else (message or code or response.text[:300])
    except Exception:
        detail = response.text[:300] or f"HTTP {response.status_code}"
    return RuntimeError(f"Notion API error {response.status_code} — {detail}")


async def _retrieve_data_source(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    data_source_id: str,
) -> dict[str, Any]:
    response = await client.get(
        f"{NOTION_API_BASE}/data_sources/{data_source_id}",
        headers=headers,
        timeout=10,
    )
    if response.status_code != 200:
        raise _notion_api_error(response)
    return response.json()


async def _resolve_data_source(
    client: httpx.AsyncClient,
    headers: dict[str, str],
) -> dict[str, Any]:
    data_source_id = _notion_id(os.getenv("NOTION_DATA_SOURCE_ID", ""))
    if data_source_id:
        return await _retrieve_data_source(client, headers, data_source_id)

    database_id = _notion_id(os.getenv("NOTION_DATABASE_ID", ""))
    if not database_id:
        raise ValueError("NOTION_DATABASE_ID or NOTION_DATA_SOURCE_ID must be set")

    response = await client.get(
        f"{NOTION_API_BASE}/databases/{database_id}",
        headers=headers,
        timeout=10,
    )
    if response.status_code != 200:
        raise _notion_api_error(response)

    data_sources = response.json().get("data_sources", [])
    if not data_sources:
        raise RuntimeError("No Notion data sources found for NOTION_DATABASE_ID")

    preferred_name = os.getenv("NOTION_DATA_SOURCE_NAME", "Cold email log").strip().casefold()
    selected = next(
        (source for source in data_sources if source.get("name", "").casefold() == preferred_name),
        None,
    )
    if selected is None:
        selected = next(
            (source for source in data_sources if "cold email" in source.get("name", "").casefold()),
            data_sources[0] if len(data_sources) == 1 else None,
        )
    if selected is None:
        names = ", ".join(source.get("name", source.get("id", "")) for source in data_sources)
        raise RuntimeError(f"Multiple Notion data sources found ({names}); set NOTION_DATA_SOURCE_ID")

    return await _retrieve_data_source(client, headers, selected["id"])


def _property_name(
    schema: dict[str, Any],
    candidates: list[str],
    property_type: str | None = None,
) -> str | None:
    for candidate in candidates:
        if candidate in schema:
            return candidate

    by_case = {name.casefold(): name for name in schema}
    for candidate in candidates:
        name = by_case.get(candidate.casefold())
        if name:
            return name

    if property_type:
        for name, meta in schema.items():
            if meta.get("type") == property_type and name.casefold() in {c.casefold() for c in candidates}:
                return name
        if property_type == "title":
            for name, meta in schema.items():
                if meta.get("type") == "title":
                    return name

    return None


def _select_name(value: str, mapping: dict[str, str]) -> str:
    value = value.strip()
    return mapping.get(value.casefold(), value)


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
    if not notion_key:
        raise ValueError("NOTION_API_KEY must be set")

    headers = {
        "Authorization": f"Bearer {notion_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        data_source = await _resolve_data_source(client, headers)
        schema = data_source.get("properties", {})

        title_name = _property_name(schema, ["Name"], "title")
        if not title_name:
            raise RuntimeError("Notion data source must have a title property")

        properties: dict[str, Any] = {
            title_name: {"title": _rich_text(person or "-")},
        }

        company_name = _property_name(schema, ["Company"], "rich_text")
        if company_name:
            properties[company_name] = {"rich_text": _rich_text(company)}

        role_name = _property_name(schema, ["Role"], "rich_text")
        if role_name:
            properties[role_name] = {"rich_text": _rich_text(role)}

        email_name = _property_name(schema, ["Email"], "email")
        if email_name and email_address:
            properties[email_name] = {"email": email_address}

        linkedin_name = _property_name(schema, ["LinkedIn URL"], "url")
        if linkedin_name and linkedin_url:
            properties[linkedin_name] = {"url": linkedin_url}

        job_link_name = _property_name(schema, ["Job Link", "Job link"], "url")
        if job_link_name and job_link:
            properties[job_link_name] = {"url": job_link}

        contact_method_name = _property_name(schema, ["Contact Method"], "select")
        if contact_method_name and contact_method:
            properties[contact_method_name] = {
                "select": {"name": _select_name(contact_method, {"email": "Email", "linkedin": "LinkedIn"})}
            }

        tone_name = _property_name(schema, ["Tone"], "select")
        if tone_name and tone:
            properties[tone_name] = {"select": {"name": tone}}

        provider_name = _property_name(schema, ["Provider"], "select")
        if provider_name and provider:
            properties[provider_name] = {
                "select": {"name": _select_name(provider, {"claude": "Claude", "groq": "Groq"})}
            }

        payload: dict[str, Any] = {
            "parent": {"type": "data_source_id", "data_source_id": data_source["id"]},
            "properties": properties,
        }

        response = await client.post(
            f"{NOTION_API_BASE}/pages",
            headers=headers,
            json=payload,
            timeout=10,
        )

    if response.status_code in (200, 201):
        return True

    raise _notion_api_error(response)
