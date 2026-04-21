# Cold Email, *warmly* written. ✦

A personal cold email generator for job applications. Paste a job description, upload your résumé, optionally research the contact — get AI-drafted, personalized emails. Review, edit, copy, and save the entry to Notion.

---

## What it does

- Researches the contact using **DuckDuckGo** (finds LinkedIn posts — no API key needed)
- Generates 4 email styles: **Formal**, **Conversational**, **Story Driven**, **Data Driven**
- Connects your résumé experience directly to the job description
- Lets you review and edit subject + body for each tone in separate tabs
- Supports **Email** and **LinkedIn DM** formats — pick the channel, the draft adapts
- Copy the draft to clipboard with one click
- **Save to Notion** logs the contact, company, role, and job link to your tracking database
- Falls back to **Groq API** (free) if no Claude API key is available
- **No scheduler. No automation. You send when you're ready.**

---

## Project structure

```
outreach-atelier/
├── frontend/
│   ├── index.html              # Main HTML shell
│   ├── css/styles.css          # All styles
│   └── js/app.js               # All frontend logic
│
├── backend/
│   ├── main.py                 # FastAPI app — routes, CORS
│   ├── generate.py             # AI email generation (Claude + Groq fallback)
│   ├── research.py             # Person research (DuckDuckGo)
│   ├── pdf_parser.py           # Résumé PDF text extraction via pdfplumber
│   ├── notion_client.py        # Notion API — save sent emails only
│   └── prompt_builder.py       # Builds structured AI prompts
│
├── api/
│   └── index.py                # Vercel entry point — imports FastAPI app
│
├── vercel.json                 # Vercel deployment config
├── requirements.txt
├── .env.example
├── CLAUDE.md
└── README.md
```

---

## Tech stack

| Layer | Tool | Cost |
|---|---|---|
| Frontend | Vanilla HTML/CSS/JS | Free |
| Backend | FastAPI (Python) | Free |
| Hosting | Vercel (fullstack) | Free |
| Primary AI | Claude Haiku 4.5 | ~$0.005 / generation |
| Fallback AI | Groq llama-3.3-70b | Free |
| LinkedIn research | DuckDuckGo search | Free, no key |
| PDF parsing | pdfplumber | Free |
| Email logging | Notion API | Free |

---

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/yourname/outreach-atelier.git
cd outreach-atelier
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Fill in `.env` — at minimum you need `ANTHROPIC_API_KEY` or `GROQ_API_KEY`.

### 3. Run locally

**Terminal 1 — start the API:**
```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — serve the frontend:**

Open `frontend/index.html` with VS Code Live Server (runs on `http://localhost:5500` or `http://127.0.0.1:5500`).

The frontend auto-detects `localhost` / `127.0.0.1` and sends API requests to `http://localhost:8000`. CORS is pre-configured for both Live Server addresses.

---

## Environment variables

```bash
# AI — at least one required
ANTHROPIC_API_KEY=sk-ant-...         # Claude Haiku 4.5 (primary, ~$0.005/req)
GROQ_API_KEY=gsk_...                 # Groq llama-3.3-70b (fallback, free)

# Notion — required for email logging
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=your-db-id

# App
FRONTEND_URL=https://your-app.vercel.app
```

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check — shows active AI provider |
| `POST` | `/api/parse-pdf` | Upload résumé PDF → extracted text |
| `POST` | `/api/research` | Research person via DuckDuckGo (optional) |
| `POST` | `/api/generate` | Generate 1–4 email/DM drafts (Claude or Groq) |
| `POST` | `/api/notion/save` | Log sent email to Notion |

---

## Research feature — how it works

When you click "Research this person", the backend runs a DuckDuckGo HTML search:

```
site:linkedin.com/posts "[Person Name]"
```

Searches the public web for LinkedIn post snippets. Fast, free, no account needed.

**Hook extraction (Claude or Groq):**
The raw snippets and résumé are fed to the AI which extracts 3 clean hooks:
- Recent LinkedIn activity / topics they've discussed
- Likely pain point for their role
- Connection between their world and your résumé

You review and edit every hook before generating.

---

## AI fallback logic

```
Request arrives
      ↓
ANTHROPIC_API_KEY present and valid?
      ↓ yes                    ↓ no
Claude Haiku 4.5         Groq llama-3.3-70b
      ↓ error?                 (always free)
      ↓ yes
Groq llama-3.3-70b
```

Response always includes `"provider": "claude"` or `"provider": "groq"`.

---

## Notion database setup

Create a Notion database with these properties:

| Property | Type | Populated from |
|---|---|---|
| Name | Title | Person name field |
| Company | Text | Company field |
| Role | Text | Their role field |
| Contact Method | Select | Email or LinkedIn toggle |
| Email | Email | Contact field (email mode) |
| LinkedIn URL | URL | Contact field (LinkedIn mode) |
| Job Link | URL | Job posting URL field |
| Tone | Select | Active tone tab |
| Provider | Select | AI provider used (claude / groq) |

Share the database with your Notion integration. Copy the database ID from the URL (the 32-character string after the last `/` and before `?`).

---

## Deploying to Vercel

**One command deploy:**
```bash
vercel --prod
```

Add environment variables via dashboard or:
```bash
vercel env add ANTHROPIC_API_KEY
vercel env add GROQ_API_KEY
vercel env add NOTION_API_KEY
vercel env add NOTION_DATABASE_ID
```

### Vercel free tier limits

| Limit | Free tier | Your usage |
|---|---|---|
| Serverless function duration | 10 seconds | AI calls ~3–6s ✓ |
| Bandwidth | 100 GB/month | Negligible ✓ |
| Deployments | Unlimited | ✓ |

---

## Cost estimate

Using Claude Haiku 4.5 (`$1/M input, $5/M output`):

| Per request | Tokens | Cost |
|---|---|---|
| Input (JD + résumé + prompt + hooks) | ~1,800 | $0.0018 |
| Output (4 email drafts ~150 words each) | ~800 | $0.004 |
| Research hook extraction | ~600 in / ~300 out | $0.002 |
| **Total per full workflow** | | **~$0.008** |

**$25 ≈ 3,000 complete workflows.** Switch to Groq for unlimited free generations.

---

## License

MIT
