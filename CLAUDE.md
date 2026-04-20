# CLAUDE.md — Cold Email Generator

This file gives AI coding assistants full context about this project. Read this before touching any code.

---

## What this project is

A personal cold email tool for job applications. The user pastes a job description, uploads their résumé PDF, optionally researches the contact using free APIs, then generates 4 tone-varied emails using AI. The user reviews and edits each draft, copies the text, and saves the entry to Notion via the "Save to Notion" button.

**Key constraints:**
- Personal single-user tool. No auth, no multi-tenancy.
- No scheduler, no automation. User sends manually every time.
- Deployed on Vercel free tier — serverless functions, 10s timeout.
- Frontend is static HTML/CSS/JS (`frontend/`). No build step, no bundler, no React.

---

## File map

```
outreach-atelier/
├── api/
│   └── index.py            # Vercel entry — just: from backend.main import app
│
├── frontend/
│   ├── index.html          # Main HTML shell. Fraunces + DM Sans + JetBrains Mono.
│   │                       # Brick-red (#8B2500) on cream (#F5EFE4).
│   │                       # DO NOT change the visual design.
│   ├── css/styles.css      # All styles
│   └── js/app.js           # All frontend logic
│
├── backend/
│   ├── main.py             # FastAPI app. All routes prefixed /api/
│   ├── generate.py         # Email/DM generation — Claude primary, Groq fallback
│   ├── research.py         # Person research — DuckDuckGo only
│   ├── pdf_parser.py       # pdfplumber résumé extraction
│   ├── notion_client.py    # Notion save only — no fetch, no update
│   └── prompt_builder.py   # Prompt assembly (email or LinkedIn DM mode)
│
├── vercel.json             # Routing config for Vercel
├── requirements.txt
├── .env.example
├── CLAUDE.md               # This file
└── README.md
```

---

## AI provider strategy

**Email generation: Claude Haiku 4.5** (`claude-haiku-4-5-20251001`)
- Used when `ANTHROPIC_API_KEY` is set and valid
- On any `anthropic.APIError`, falls back to Groq
- Cost: ~$0.006 per generation workflow (4 tones)

**Research hook extraction: Groq only** (`llama-3.3-70b-versatile`)
- Claude is never called during research
- If `GROQ_API_KEY` is missing or Groq fails, returns default empty hooks gracefully

**Groq** (`llama-3.3-70b-versatile`)
- Endpoint: `https://api.groq.com/openai/v1/chat/completions`
- OpenAI-compatible format
- Used exclusively for research; also fallback for email generation
- Free tier, no cost

**Rule for email generation:** Try Claude first; fall back to Groq on any failure. Log `"provider"` in every response.

```python
# Pattern used throughout generate.py and research.py
async def call_ai(messages, max_tokens=1000):
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                messages=messages
            )
            return resp.content[0].text, "claude"
        except anthropic.APIError:
            pass  # fall through to Groq
    # Groq fallback
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"},
        json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": max_tokens}
    )
    return resp.json()["choices"][0]["message"]["content"], "groq"
```

---

## Research module — research.py

Uses a single source: DuckDuckGo HTML search (no API key needed).

### DuckDuckGo (LinkedIn posts)

```python
import httpx
from bs4 import BeautifulSoup

async def ddg_linkedin_search(name: str) -> list[str]:
    query = f'site:linkedin.com/posts "{name}"'
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers, follow_redirects=True, timeout=8)
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for result in soup.select(".result__snippet")[:3]:
        text = result.get_text(strip=True)
        if text and len(text) > 30:
            results.append(text)
    return results
```

**Failure mode:** DuckDuckGo sometimes blocks or returns no results for niche queries. Always catch exceptions and return empty list — hook extraction still runs and can generate pain_point and resume_connection from the résumé alone.

### Hook extraction (Claude or Groq)

DDG snippets + résumé are fed to the AI to extract 3 structured hooks:

```python
extraction_prompt = f"""
You have raw research about a person scraped from DuckDuckGo LinkedIn results.
Extract exactly 3 personalization hooks for a cold email:

1. linkedin_activity: What they've recently posted or discussed (be specific, or empty string if nothing found)
2. pain_point: A real challenge someone in their role likely faces
3. resume_connection: How the applicant's background (from their résumé) specifically connects to this person's world

Raw research:
DuckDuckGo LinkedIn results: {ddg_str}
Applicant résumé (for resume_connection hook): {resume_text[:1500]}

Respond ONLY in JSON. No markdown, no backticks, no explanation:
{{"linkedin_activity": "...", "pain_point": "...", "resume_connection": "..."}}
"""
```

Parse with `json.loads()`. If parsing fails, return a default structure with empty strings — never crash the endpoint.

Response shape: `{ hooks: {linkedin_activity, pain_point, resume_connection}, raw: {ddg: [...]}, provider: str }`

---

## Prompt architecture — prompt_builder.py

The email generation prompt structure:

```
System:
  You are an expert cold email writer helping {user_name} apply for jobs.
  Write emails that feel genuinely personal, not templated.
  Connect the applicant's specific experience directly to the company's work.
  Each email must be under 150 words.
  Include a subject line.
  
  RULES:
  - Opening line references something specific about THEM, not about us
  - Never use: 'innovative', 'cutting-edge', 'game-changing', 'synergy'
  - Never start with 'I hope this email finds you well'
  - One clear, low-friction CTA
  - Tone: confident, {tone_description}, helpful — not salesy

User:
  Job description:
  {jd_text}

  Applicant résumé highlights:
  {resume_text}  ← truncated to 800 tokens

  Contact: {person_name}, {their_role} at {company}
  
  Personalization hooks (use these to open and personalize):
  - Their recent activity: {hooks.linkedin_activity}
  - Their pain point: {hooks.pain_point}
  - Connection between applicant and their world: {hooks.resume_connection}

  Additional notes from applicant: {notes}

  Write {n} email(s)/DM(s) in these tone(s): {tones}

  For email — each tone uses this format:
  TONE: [tone name]
  SUBJECT: [subject line]
  BODY:
  [email body]
  ---

  For LinkedIn DM — each tone uses this format (no subject line):
  TONE: [tone name]
  BODY:
  [DM body]
  ---
```

Parse by splitting on `---`, then extract TONE/SUBJECT/BODY from each block using simple string operations (not regex — too fragile).

`contact_method` ("email" or "linkedin") is passed through from the frontend → `GenerateRequest` → `generate_emails()` → `build_prompt()`, which switches the system prompt and format template accordingly.

**Tone descriptions injected into system prompt:**
- Formal → "professional and structured"
- Conversational → "warm and direct, like talking to a peer"
- Story Driven → "narrative, connecting your journey to their mission"
- Data Driven → "metrics-first, leading with specific impact numbers"

---

## Notion — notion_client.py

**Save only.** No fetch, no update, no status management. Saves 6 fields.

```python
async def save_sent_email(person, company, role, email_address, linkedin_url, job_link):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {os.getenv('NOTION_API_KEY')}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    payload = {
        "parent": {"database_id": os.getenv("NOTION_DATABASE_ID")},
        "properties": {
            "Name":         {"title": [{"text": {"content": person}}]},
            "Company":      {"rich_text": [{"text": {"content": company}}]},
            "Role":         {"rich_text": [{"text": {"content": role}}]},
            "Email":        {"email": email_address},
            "LinkedIn URL": {"url": linkedin_url or None},
            "Job Link":     {"url": job_link or None},
        }
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=payload, timeout=10)
    return r.status_code == 200
```

---

## Vercel deployment

### How it works

Vercel runs FastAPI as a **serverless Python function**. Each request spins up a function instance. Cold start: ~1–2s. Warm: fast.

### Critical constraints for Vercel

- **10 second function timeout** on free tier. AI calls typically take 3–6s — this is fine. PDF parsing is fast. Research (DuckDuckGo + AI extraction) takes ~3–5s — fine.
- **No persistent filesystem.** pdfplumber reads the uploaded bytes directly from memory — never writes to disk. This already works correctly.
- **No background tasks.** Everything must complete within the request lifecycle. No async fire-and-forget.
- **Environment variables** set via `vercel env add` or the dashboard. Never committed to git.

### vercel.json structure

```json
{
  "version": 2,
  "builds": [
    { "src": "api/index.py", "use": "@vercel/python" },
    { "src": "frontend/**", "use": "@vercel/static" }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "api/index.py" },
    { "src": "/(.*)", "dest": "frontend/$1" }
  ]
}
```

### api/index.py (one line)

```python
from backend.main import app  # noqa
```

Vercel looks for `app` in the imported module automatically.

### CORS in main.py

```python
from fastapi.middleware.cors import CORSMiddleware

origins = [
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
    "http://localhost:8000",
    "http://localhost:5500",    # VS Code Live Server
    "http://127.0.0.1:5500",   # VS Code Live Server (alternate hostname)
    "null",                    # file:// origin
]
app.add_middleware(CORSMiddleware,
                   allow_origins=origins,
                   allow_origin_regex=r"https://.*\.vercel\.app",
                   allow_methods=["*"], allow_headers=["*"])
```

---

## requirements.txt

```
fastapi==0.115.0
uvicorn==0.30.6
anthropic==0.40.0
httpx==0.27.2
pdfplumber==0.11.4
beautifulsoup4==4.12.3
python-multipart==0.0.12
pydantic==2.9.2
requests==2.32.3
```

---

## What NOT to do

- Do not add a database — Notion is the only datastore
- Do not add user authentication — personal single-user tool
- Do not change the frontend visual design (colors, fonts, layout)
- Do not store PDFs on disk — parse bytes in memory only
- Do not commit `.env` — it contains real keys
- Do not use any OpenAI models — Claude and Groq only
- Do not add a scheduler or any automation — user sends manually
- Do not add streaming — return complete response after AI call finishes
- Do not use `playwright` or `selenium` for LinkedIn — ToS risk
- Do not use `site:linkedin.com/in/` for DuckDuckGo — use `/posts/` only
- Never touch auth/middlewware without explicit approval

---

## Common tasks for AI assistants

**Adding a new email tone:**
1. Add chip to `#tones` div in `frontend/index.html`
2. Add to `TONES` JS array in `frontend/js/app.js`
3. Add tone description to `TONE_DESCRIPTIONS` dict in `prompt_builder.py`
4. No other changes needed

**Improving research quality:**
Edit the extraction prompt in `research.py`. DuckDuckGo is the only source — if results are sparse, consider adding a second free search (e.g. Bing HTML scrape with the same pattern).

**Debugging DuckDuckGo:**
DuckDuckGo blocks requests without a proper User-Agent. Always set `"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"`. If still blocked, add a 1–2s delay before the request.

**Debugging Notion:**
Most common errors:
- 404 → database ID wrong or integration not shared with the database
- 400 → property name mismatch (case-sensitive) or wrong property type

**Updating frontend API URL:**
In `frontend/js/app.js`, `BASE_URL` is set dynamically: `localhost` or `127.0.0.1` → `http://localhost:8000`, any other hostname → `""` (relative, works on Vercel). No manual change needed for deployment. Local dev: run the backend on port 8000 and open the frontend via Live Server (`http://localhost:5500` or `http://127.0.0.1:5500`). CORS is pre-configured for both.
