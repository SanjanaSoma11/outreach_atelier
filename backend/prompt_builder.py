TONE_DESCRIPTIONS = {
    "Formal": "professional and structured",
    "Conversational": "warm and direct, like talking to a peer",
    "Story Driven": "narrative, connecting your journey to their mission",
    "Data Driven": "metrics-first, leading with specific impact numbers",
}

_APPROX_CHARS_PER_TOKEN = 4
_RESUME_TOKEN_LIMIT = 800


def _truncate_resume(text: str) -> str:
    char_limit = _RESUME_TOKEN_LIMIT * _APPROX_CHARS_PER_TOKEN
    if len(text) <= char_limit:
        return text
    return text[:char_limit] + "\n[résumé truncated]"


def build_prompt(
    resume_text: str,
    job_description: str,
    person_name: str,
    person_role: str,
    company: str,
    tones: list[str],
    hooks: dict,
    notes: str = "",
    user_name: str = "the applicant",
) -> tuple[str, str]:
    """
    Returns (system_prompt, user_prompt) for the AI call.
    hooks dict keys: linkedin_activity, company_news, pain_point, connection
    """
    tone_list = tones if tones else ["Conversational"]
    tone_descriptions = "\n".join(
        f"- {t}: {TONE_DESCRIPTIONS.get(t, 'genuine and helpful')}"
        for t in tone_list
    )

    system_prompt = f"""You are an expert cold email writer helping {user_name} apply for jobs.
Write emails that feel genuinely personal, not templated.
Connect the applicant's specific experience directly to the company's work.
Each email must be under 150 words. Include a subject line.

RULES:
- Opening line references something specific about THEM, not about the applicant
- Never use: 'innovative', 'cutting-edge', 'game-changing', 'synergy'
- Never start with 'I hope this email finds you well'
- One clear, low-friction CTA (ask for a 15-min call or reply, nothing more)
- Tone guidance:
{tone_descriptions}"""

    hooks_section = ""
    if any(hooks.get(k) for k in ("linkedin_activity", "company_news", "pain_point", "connection")):
        hooks_section = f"""
Personalization hooks (use these to open and personalize):
- Their recent activity: {hooks.get('linkedin_activity', '')}
- Company news: {hooks.get('company_news', '')}
- Their pain point: {hooks.get('pain_point', '')}
- Connection between applicant and their world: {hooks.get('connection', '')}
"""

    notes_section = f"\nAdditional notes from applicant: {notes}" if notes.strip() else ""

    tone_format_instructions = "\n".join(
        f"TONE: {t}\nSUBJECT: [subject line]\nBODY:\n[email body]\n---"
        for t in tone_list
    )

    user_prompt = f"""Job description:
{job_description}

Applicant résumé highlights:
{_truncate_resume(resume_text)}

Contact: {person_name}, {person_role} at {company}
{hooks_section}{notes_section}
Write {len(tone_list)} email(s) in these tone(s): {', '.join(tone_list)}

For each tone, use this exact format:
{tone_format_instructions}"""

    return system_prompt, user_prompt
