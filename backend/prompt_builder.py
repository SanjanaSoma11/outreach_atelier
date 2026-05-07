from __future__ import annotations

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
    context: str = "",
    contact_method: str = "email",
) -> tuple[str, str]:
    """
    Returns (system_prompt, user_prompt) for the AI call.
    hooks dict keys: linkedin_activity, pain_point, resume_connection
    context: optional free-text about the contact, injected into the prompt if provided
    contact_method: "email" (subject line, ≤150 words) or "linkedin" (DM, ≤300 words, no subject)
    """
    tone_list = tones if tones else ["Conversational"]
    tone_descriptions = "\n".join(
        f"- {t}: {TONE_DESCRIPTIONS.get(t, 'genuine and helpful')}"
        for t in tone_list
    )

    is_dm = contact_method == "linkedin"

    if is_dm:
        system_prompt = f"""You are an expert outreach writer helping {user_name} apply for jobs via LinkedIn DM.
Write short, conversational direct messages that feel personal and human — not like a cover letter.
Each DM must be under 300 words. Do NOT include a subject line. Do NOT use a formal sign-off like "Best regards" or "Sincerely".

RULES:
- Opening line references something specific about THEM, not about the applicant
- After the opening line, lead with genuine curiosity about their specific work — not your background
- Your own background gets ONE sentence maximum, woven in naturally — never bulleted or listed
- Never use two consecutive sentences about yourself
- Never use: 'innovative', 'cutting-edge', 'game-changing', 'synergy'
- Casual tone — write like a peer reaching out, not an applicant begging
- End with ONE specific ask — either about their work OR about the hiring bar, not both. Keep it a single question.
- The word 'I' may appear at most 3 times in the entire message
- The message has exactly two parts: (1) one opening observation about them, (2) one question. No credential paragraph between them.
- Tone guidance:
{tone_descriptions}"""
    else:
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
    if any(hooks.get(k) for k in ("linkedin_activity", "pain_point", "resume_connection")):
        hooks_section = f"""
Personalization hooks (use these to open and personalize):
- Their recent activity: {hooks.get('linkedin_activity', '')}
- Their pain point: {hooks.get('pain_point', '')}
- Connection between applicant and their world: {hooks.get('resume_connection', '')}
"""

    context_section = f"\nAdditional context about this person: {context}" if context.strip() else ""
    notes_section = f"\nAdditional notes from applicant: {notes}" if notes.strip() else ""

    if is_dm:
        tone_format_instructions = "\n".join(
            f"TONE: {t}\nBODY:\n[DM body]\n---"
            for t in tone_list
        )
        format_note = "Write each as a LinkedIn DM — no subject line, conversational, under 300 words."
    else:
        tone_format_instructions = "\n".join(
            f"TONE: {t}\nSUBJECT: [subject line]\nBODY:\n[email body]\n---"
            for t in tone_list
        )
        format_note = "Write each as a cold email with a subject line, under 150 words."

    if is_dm:
        user_prompt = f"""Job description:
{job_description}

Contact: {person_name}, {person_role} at {company}
{hooks_section}{context_section}{notes_section}
Write {len(tone_list)} DM(s) in these tone(s): {', '.join(tone_list)}
{format_note}

For each tone, use this exact format:
{tone_format_instructions}"""
    else:
        user_prompt = f"""Job description:
{job_description}

Applicant résumé highlights:
{_truncate_resume(resume_text)}

Contact: {person_name}, {person_role} at {company}
{hooks_section}{context_section}{notes_section}
Write {len(tone_list)} email(s) in these tone(s): {', '.join(tone_list)}
{format_note}

For each tone, use this exact format:
{tone_format_instructions}"""

    return system_prompt, user_prompt
