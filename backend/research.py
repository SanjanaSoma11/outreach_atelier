import asyncio
import json
import os
import urllib.parse

import anthropic
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


async def _perplexity_call(prompt: str) -> str:
    """Single Perplexity sonar-small call. Returns text or empty string on failure."""
    key = os.getenv("PERPLEXITY_API_KEY")
    if not key:
        return ""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "llama-3.1-sonar-small-128k-online",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 600,
                },
                timeout=15,
            )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return ""


async def _perplexity_research(name: str, role: str, company: str) -> tuple[str, str]:
    """Run person + company Perplexity calls in parallel."""
    person_prompt = (
        f"Search the web and find what {name}, {role} at {company}, "
        "has publicly posted, written, or discussed recently. "
        "Focus on LinkedIn posts, articles, interviews, or conference talks. "
        "Return bullet points only. Be specific — include actual topics, not generalities."
    )
    company_prompt = (
        f"Search the web for {company}:\n"
        f"1. Notable news or announcements in the last 60 days\n"
        f"2. A likely pain point for someone in a {role} role at this company's stage/size\n"
        "Return bullet points only. Be concise."
    )
    person_result, company_result = await asyncio.gather(
        _perplexity_call(person_prompt),
        _perplexity_call(company_prompt),
    )
    return person_result, company_result


def _extract_hooks_sync(
    name: str,
    role: str,
    company: str,
    ddg_results: list[str],
    perplexity_person: str,
    perplexity_company: str,
    resume_text: str = "",
) -> tuple[dict, str]:
    """Use Claude or Groq to distill raw research into 4 structured hooks."""
    ddg_str = "\n".join(ddg_results) if ddg_results else "No results found."
    extraction_prompt = f"""You have raw research about a person and their company.
Extract exactly 4 personalization hooks for a cold email:

1. linkedin_activity: What they've recently posted or discussed (be specific)
2. company_news: Something notable about the company in the last 60 days
3. pain_point: A real challenge someone in their role at their company faces
4. connection: How the applicant's background (from their résumé) specifically connects to their world

Raw research:
DuckDuckGo LinkedIn results: {ddg_str}
Perplexity person research: {perplexity_person or 'Not available.'}
Perplexity company research: {perplexity_company or 'Not available.'}
Applicant résumé (for connection hook): {resume_text[:1500] if resume_text else 'Not provided.'}

Respond ONLY in JSON. No markdown, no backticks, no explanation:
{{"linkedin_activity": "...", "company_news": "...", "pain_point": "...", "connection": "..."}}"""

    messages = [{"role": "user", "content": extraction_prompt}]
    raw_text = ""
    provider = "none"

    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=600,
                messages=messages,
            )
            raw_text = resp.content[0].text
            provider = "claude"
        except anthropic.APIError:
            pass

    if not raw_text:
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": messages,
                        "max_tokens": 600,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                raw_text = resp.json()["choices"][0]["message"]["content"]
                provider = "groq"
            except Exception:
                pass

    default = {"linkedin_activity": "", "company_news": "", "pain_point": "", "connection": ""}
    if not raw_text:
        return default, provider

    try:
        # Strip any accidental markdown fences before parsing
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
    Full research pipeline. Returns:
    {
      hooks: {linkedin_activity, company_news, pain_point, connection},
      raw: {ddg, perplexity_person, perplexity_company},
      provider: str
    }
    """
    ddg_task = _ddg_linkedin_search(name)
    perplexity_task = _perplexity_research(name, role, company)

    ddg_results, (perplexity_person, perplexity_company) = await asyncio.gather(
        ddg_task, perplexity_task
    )

    hooks, provider = _extract_hooks_sync(
        name=name,
        role=role,
        company=company,
        ddg_results=ddg_results,
        perplexity_person=perplexity_person,
        perplexity_company=perplexity_company,
        resume_text=resume_text,
    )

    return {
        "hooks": hooks,
        "raw": {
            "ddg": ddg_results,
            "perplexity_person": perplexity_person,
            "perplexity_company": perplexity_company,
        },
        "provider": provider,
    }
