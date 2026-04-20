from __future__ import annotations

import os
import requests
import anthropic

from .prompt_builder import build_prompt


async def _call_ai(messages: list[dict], max_tokens: int = 2000) -> tuple[str, str]:
    """Try Claude Haiku first, fall back to Groq. Returns (text, provider)."""
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                messages=messages,
            )
            return resp.content[0].text, "claude"
        except anthropic.APIError:
            pass

    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise ValueError("No AI provider available — set ANTHROPIC_API_KEY or GROQ_API_KEY")

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {groq_key}"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "max_tokens": max_tokens,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"], "groq"


def _parse_email_blocks(raw: str, tones: list[str]) -> list[dict]:
    """Split raw AI output on --- and extract TONE/SUBJECT/BODY per block."""
    blocks = [b.strip() for b in raw.split("---") if b.strip()]
    emails = []

    for block in blocks:
        lines = block.splitlines()
        tone = subject = ""
        body_lines = []
        in_body = False

        for line in lines:
            if line.startswith("TONE:") and not tone:
                tone = line[len("TONE:"):].strip()
            elif line.startswith("SUBJECT:") and not subject:
                subject = line[len("SUBJECT:"):].strip()
            elif line.startswith("BODY:"):
                in_body = True
            elif in_body:
                body_lines.append(line)

        body = "\n".join(body_lines).strip()
        if tone or subject or body:
            emails.append({"tone": tone, "subject": subject, "body": body})

    # If parsing produced fewer blocks than tones, fill in what we have
    return emails


async def generate_emails(
    resume_text: str,
    job_description: str,
    person_name: str,
    person_role: str,
    company: str,
    tones: list[str],
    hooks: dict,
    notes: str = "",
    user_name: str = "the applicant",
    context: str = "",
    contact_method: str = "email",
) -> dict:
    """Generate tone-varied cold emails or LinkedIn DMs. Returns {emails: [...], provider: str}."""
    system_prompt, user_prompt = build_prompt(
        resume_text=resume_text,
        job_description=job_description,
        person_name=person_name,
        person_role=person_role,
        company=company,
        tones=tones,
        hooks=hooks,
        notes=notes,
        user_name=user_name,
        context=context,
        contact_method=contact_method,
    )

    messages = [{"role": "user", "content": user_prompt}]
    raw, provider = await _call_ai(
        [{"role": "user", "content": system_prompt + "\n\n" + user_prompt}],
        max_tokens=2000,
    )

    emails = _parse_email_blocks(raw, tones)
    return {"emails": emails, "provider": provider}
