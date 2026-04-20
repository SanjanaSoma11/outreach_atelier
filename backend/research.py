from __future__ import annotations

import json
import os
import urllib.parse

import httpx
import requests
from bs4 import BeautifulSoup


async def _ddg_linkedin_search(name: str) -> list[str]:
    """DuckDuckGo HTML scrape for public LinkedIn posts. Returns up to 3 snippets."""
    query = f'site:linkedin.com/posts "{name}"'
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers, follow_redirects=True, timeout=8)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for result in soup.select(".result__snippet")[:3]:
            text = result.get_text(strip=True)
            if text and len(text) > 30:
                results.append(text)
        return results
    except Exception:
        return []


def _extract_hooks_sync(
    ddg_results: list[str],
    resume_text: str = "",
    role: str = "",
    company: str = "",
) -> tuple[dict, str]:
    """Use Groq to distill DDG snippets into 3 structured hooks."""
    default = {"linkedin_activity": "", "pain_point": "", "resume_connection": ""}

    if not ddg_results and not resume_text:
        return default, "none"

    ddg_str = "\n".join(ddg_results) if ddg_results else "No results found."
    role_context = f"{role} at {company}" if role and company else (role or company or "this person's role")
    extraction_prompt = f"""You have raw research about a person scraped from DuckDuckGo LinkedIn results.
Extract exactly 3 personalization hooks for a cold email:

1. linkedin_activity: What they've recently posted or discussed (be specific, or empty string if nothing found)
2. pain_point: A specific, concrete challenge that a {role_context} typically faces day-to-day (not generic — name the actual problem)
3. resume_connection: How the applicant's background (from their résumé) specifically connects to this person's world

Raw research:
DuckDuckGo LinkedIn results: {ddg_str}
Applicant résumé (for resume_connection hook): {resume_text[:1500] if resume_text else 'Not provided.'}

Respond ONLY in JSON. No markdown, no backticks, no explanation:
{{"linkedin_activity": "...", "pain_point": "...", "resume_connection": "..."}}"""

    messages = [{"role": "user", "content": extraction_prompt}]
    raw_text = ""
    provider = "none"

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "max_tokens": 400,
                },
                timeout=30,
            )
            resp.raise_for_status()
            raw_text = resp.json()["choices"][0]["message"]["content"]
            provider = "groq"
        except Exception:
            pass

    if not raw_text:
        return default, provider

    try:
        cleaned = raw_text.strip().strip("`").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
        hooks = json.loads(cleaned)
        for key in default:
            hooks.setdefault(key, "")
        return hooks, provider
    except (json.JSONDecodeError, ValueError):
        return default, provider


async def research_person(
    name: str,
    role: str,
    company: str,
    resume_text: str = "",
) -> dict:
    """
    Research pipeline using DuckDuckGo only. Returns:
    {
      hooks: {linkedin_activity, pain_point, resume_connection},
      raw: {ddg: [...]},
      provider: str
    }
    """
    ddg_results = await _ddg_linkedin_search(name)

    hooks, provider = _extract_hooks_sync(
        ddg_results=ddg_results,
        resume_text=resume_text,
        role=role,
        company=company,
    )

    return {
        "hooks": hooks,
        "raw": {"ddg": ddg_results},
        "provider": provider,
    }
