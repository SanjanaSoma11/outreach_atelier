# Cold Email, *warmly* written. ✦

A personal cold email generator for job applications. Paste a job description, upload your résumé, research the contact using free tools — get 4 AI-drafted, personalized emails. Review, edit, and send on your own terms. Everything logged to Notion.

---

## What it does

- Researches the contact and company using **Perplexity API** (free tier)
- Finds LinkedIn posts via **Google-indexed search** (DuckDuckGo, no key needed) + **Perplexity**
- Generates 4 email styles: **Formal**, **Conversational**, **Story Driven**, **Data Driven**
- Connects your résumé experience directly to the job description
- Lets you review, edit subject + body, then send
- Supports **Email** (opens mail client) and **LinkedIn DM** (copies + opens profile)
- Logs every sent email to **Notion** automatically
- Falls back to **Groq API** (free) if no Claude API key is available
- **No scheduler. No automation. You send when you're ready.**

---

## Project structure

```
cold-email/
├── frontend/
│   └── coldemail.html          # Single-file frontend — your existing design
│
├── backend/
│   ├── main.py                 # FastAPI app — routes, CORS
│   ├── generate.py             # AI email generation (Claude + Groq fallback)
│   ├── research.py             # Person + company research (Perplexity + DuckDuckGo)
│   ├── pdf_parser.py           # Résumé PDF text extraction via pdfplumber
│   ├── notion_client.py        # Notion API — save sent emails only
│   ├── gmail_client.py         # Gmail API — OAuth send (optional)
│   └── prompt_builder.py       # Builds structured AI prompts
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
| Research | Perplexity API | Free tier |
| LinkedIn posts | DuckDuckGo search | Free, no key |
| LinkedIn activity | Perplexity API | Free tier |
| PDF parsing | pdfplumber | Free |
| Email logging | Notion API | Free |

---

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/yourname/cold-email.git
cd cold-email
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Fill in `.env` — at minimum you need `ANTHROPIC_API_KEY` or `GROQ_API_KEY`, and `PERPLEXITY_API_KEY`.

### 3. Run locally

```bash
uvicorn backend.main:app --reload --port 8000
```

Open `frontend/coldemail.html` in your browser. Done.

---

## Environment variables

```bash
# .env

# AI — at least one required
ANTHROPIC_API_KEY=sk-ant-...         # Claude Haiku 4.5 (primary, ~$0.005/req)
GROQ_API_KEY=gsk_...                 # Groq llama-3.3-70b (fallback, free)

# Research — required for Research feature
PERPLEXITY_API_KEY=pplx-...          # Free tier: 5 req/min, plenty for personal use

# Notion — required for email logging
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=your-db-id

# Gmail — optional, for direct send via API instead of mailto:
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...
SENDER_EMAIL=you@gmail.com

# App
FRONTEND_URL=https://your-app.vercel.app
```

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/parse-pdf` | Upload résumé PDF → extracted text |
| `POST` | `/api/research` | Research person + company (Perplexity + DuckDuckGo) |
| `POST` | `/api/generate` | Generate 1–4 email drafts (Claude or Groq) |
| `POST` | `/api/send` | Send via Gmail API (optional) |
| `POST` | `/api/notion/save` | Log sent email to Notion |
| `GET` | `/api/health` | Health check — shows active AI provider |

---

## Research feature — how it works

When you click "Research this person", the backend runs two parallel searches:

**LinkedIn posts — dual strategy:**

Option A (DuckDuckGo):
```
site:linkedin.com/posts "[Person Name]"
```
Searches Google's index of public LinkedIn posts. Fast, free, no account needed.

Option B (Perplexity):
```
"What has [Name], [Role] at [Company], publicly posted or written about recently?"
```
Perplexity searches the wider web including indexed LinkedIn content and summarizes it.

Both results are merged and deduplicated before being shown to you.

**Company research (Perplexity):**
```
"What notable things has [Company] done in the last 60 days?
 What challenges does a [Role] at [Company] typically face?"
```

**Hook extraction (Claude or Groq):**
All raw research is fed to the AI which extracts 4 clean hooks:
- Recent LinkedIn activity / topics they've discussed
- Company news (last 60 days)
- Likely pain point for their role and company size
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

Response always includes `"provider": "claude"` or `"provider": "groq"` so you know which was used.

---

## Notion database setup

Create a Notion database with these properties:

| Property | Type |
|---|---|
| Name | Title |
| Company | Text |
| Role | Text |
| Email | Email |
| LinkedIn | URL |
| Job Link | URL |
| Tone Used | Select |
| Email Draft | Text |
| Hooks Used | Text |
| Status | Select: `Sent` / `Followed Up` |
| Sent Date | Date |

Share the database with your Notion integration. Copy the database ID from the URL (the 32-character string after the last `/` and before `?`).

---

## Deploying to Vercel

This project is fully deployable on Vercel's free tier — both frontend and backend together. See the Vercel deployment section below for details.

**One command deploy:**
```bash
vercel --prod
```

Full deploy instructions: see [Vercel Deployment](#vercel-deployment) section.

---

## Vercel deployment

Vercel supports Python FastAPI via serverless functions. The project is structured to work out of the box.

### 1. Project structure for Vercel

```
cold-email/
├── api/
│   └── index.py        # Vercel entry point — imports your FastAPI app
├── frontend/
│   └── coldemail.html  # Served as static file
├── backend/
│   └── ...             # Your FastAPI modules
├── vercel.json
└── requirements.txt
```

### 2. vercel.json

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    },
    {
      "src": "frontend/**",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "api/index.py"
    },
    {
      "src": "/(.*)",
      "dest": "frontend/$1"
    }
  ]
}
```

### 3. api/index.py (Vercel entry point)

```python
from backend.main import app
```

### 4. Deploy steps

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy (first time — answers prompts)
vercel

# Production deploy
vercel --prod
```

### 5. Add environment variables on Vercel

```bash
vercel env add ANTHROPIC_API_KEY
vercel env add GROQ_API_KEY
vercel env add PERPLEXITY_API_KEY
vercel env add NOTION_API_KEY
vercel env add NOTION_DATABASE_ID
```

Or add them in the Vercel dashboard → Project → Settings → Environment Variables.

### Vercel free tier limits

| Limit | Free tier | Your usage |
|---|---|---|
| Serverless function duration | 10 seconds | AI calls ~3–6s ✓ |
| Bandwidth | 100 GB/month | Negligible ✓ |
| Deployments | Unlimited | ✓ |
| Custom domain | 1 free `.vercel.app` | ✓ |

**One watch-out:** Vercel serverless functions have a cold start (~1–2s). First request after inactivity will feel slow. Subsequent requests are fast. For a personal tool used a few times a day, this is fine.

---

## Cost estimate with $25 API credits

Using Claude Haiku 4.5 (`$1/M input, $5/M output`):

| Per request | Tokens | Cost |
|---|---|---|
| Input (JD + résumé + prompt + hooks) | ~1,800 | $0.0018 |
| Output (4 email drafts ~150 words each) | ~800 | $0.004 |
| Research hook extraction | ~600 in / ~300 out | $0.002 |
| **Total per full workflow** | | **~$0.008** |

**$25 ≈ 3,000 complete workflows** (research + generate). Switch to Groq for unlimited free generations with slightly lower quality.

---

## Roadmap

- [ ] Follow-up email generator — auto-drafts a follow-up referencing the original
- [ ] Chrome extension — pull JD directly from job listing page
- [ ] Response tracker — log replies back to Notion
- [ ] Email open tracking via pixel (requires Gmail API send)
- [ ] Multi-language support — generate emails in the contact's language

---

## License

MIT
