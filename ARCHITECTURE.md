# Cold Email Generator — Architecture

## System overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        VERCEL (free tier)                            │
│                                                                      │
│  ┌─────────────────────────────┐  ┌───────────────────────────────┐ │
│  │   STATIC FRONTEND           │  │   SERVERLESS BACKEND          │ │
│  │   frontend/coldemail.html   │  │   api/index.py → backend/     │ │
│  │                             │  │                               │ │
│  │  Fraunces + DM Sans         │  │   FastAPI — all routes        │ │
│  │  Brick-red on cream         │  │   prefixed /api/              │ │
│  │  Single HTML file           │  │   Python serverless function  │ │
│  │  No build step              │  │   10s timeout per request     │ │
│  └──────────────┬──────────────┘  └──────────────┬────────────────┘ │
│                 │   HTTP fetch                    │                  │
│                 └────────────────────────────────►│                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
              ┌─────────────────────┼──────────────────────┐
              ▼                     ▼                      ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────────┐
   │   AI PROVIDERS   │  │  RESEARCH TOOLS  │  │   EXTERNAL APIS     │
   │                  │  │                  │  │                     │
   │ Claude Haiku 4.5 │  │ Perplexity API   │  │ Notion API          │
   │ (primary)        │  │ (person + company│  │ (email logging)     │
   │       ↓ fails    │  │  research)       │  │                     │
   │ Groq llama-3.3   │  │                  │  │ Gmail API           │
   │ (free fallback)  │  │ DuckDuckGo HTML  │  │ (optional send)     │
   └──────────────────┘  │ (LinkedIn posts) │  └─────────────────────┘
                         └──────────────────┘
```

---

## Full user workflow

```
                        USER OPENS coldemail.html
                                   │
                    ┌──────────────▼──────────────┐
                    │         STEP 1               │
                    │       Fill the form          │
                    │                              │
                    │  • Job description           │
                    │  • Person name               │
                    │  • Their role                │
                    │  • Contact method toggle:    │
                    │    [Email] or [LinkedIn DM]  │
                    │  • Email addr / LinkedIn URL │
                    │  • Additional notes (opt.)   │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │         STEP 2               │
                    │      Upload résumé           │
                    │                              │
                    │  PDF → POST /api/parse-pdf   │
                    │  pdfplumber extracts text    │
                    │  Stored in JS state          │
                    │  Never saved to disk         │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │         STEP 3  (optional)   │
                    │    Research this person      │
                    │                              │
                    │  POST /api/research          │
                    │  ↓ (runs in parallel)        │
                    │  DuckDuckGo → LinkedIn posts │
                    │  Perplexity → person hooks   │
                    │  Perplexity → company news   │
                    │  AI → extract 4 clean hooks  │
                    │                              │
                    │  User reviews + edits hooks  │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │         STEP 4               │
                    │      Pick tone(s)            │
                    │                              │
                    │  ┌────────┐ ┌─────────────┐  │
                    │  │ Formal │ │Conversation │  │
                    │  └────────┘ └─────────────┘  │
                    │  ┌──────────────┐ ┌────────┐ │
                    │  │ Story Driven │ │Data    │ │
                    │  └──────────────┘ │Driven  │ │
                    │                   └────────┘ │
                    │  Select 1–4. "Select all 4→" │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │         STEP 5               │
                    │      Generate drafts         │
                    │                              │
                    │  POST /api/generate          │
                    │  { jd, resume, person,       │
                    │    role, tones, hooks,        │
                    │    notes }                    │
                    │                              │
                    │  prompt_builder assembles    │
                    │  structured prompt           │
                    │                              │
                    │  Try Claude Haiku 4.5        │
                    │  → fail → Groq llama-3.3     │
                    │                              │
                    │  Response parsed into tabs   │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │         STEP 6               │
                    │    Review & edit drafts      │
                    │                              │
                    │  Tabbed panel — one per tone │
                    │  Editable subject line       │
                    │  Editable email body         │
                    │  Live word count             │
                    │  Regenerate single tab       │
                    │  Copy to clipboard           │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │         STEP 7               │
                    │           Send               │
                    │                              │
                    │  ┌──────────────────────┐    │
                    │  │ Email method         │    │
                    │  │ Opens mail client    │    │
                    │  │ Subject + body       │    │
                    │  │ pre-filled via       │    │
                    │  │ mailto: link         │    │
                    │  └──────────────────────┘    │
                    │                              │
                    │  ┌──────────────────────┐    │
                    │  │ LinkedIn DM method   │    │
                    │  │ Copies body text     │    │
                    │  │ Opens LinkedIn DM /  │    │
                    │  │ their profile in new │    │
                    │  │ tab                  │    │
                    │  └──────────────────────┘    │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │         STEP 8               │
                    │      Auto-logged to Notion   │
                    │                              │
                    │  POST /api/notion/save       │
                    │  Logs: name, company, role,  │
                    │  tone, draft, hooks, date    │
                    │  Status → Sent               │
                    └──────────────────────────────┘
```

---

## Research flow — detail

```
POST /api/research
{ name, company, role, linkedin_url }
         │
         ├──────────────────────────────────────────┐
         │                                          │
         ▼  (parallel via asyncio.gather)           ▼
┌─────────────────────┐               ┌─────────────────────────┐
│  DuckDuckGo Search  │               │   Perplexity API        │
│  (Option A)         │               │   (Option B + Company)  │
│                     │               │                         │
│  Query:             │               │  Call 1 — person:       │
│  site:linkedin.com/ │               │  "What has [Name],      │
│  posts "[Name]"     │               │   [Role] at [Company]   │
│                     │               │   publicly posted or    │
│  Parses HTML result │               │   written about         │
│  Returns snippets   │               │   recently?"            │
│  of public posts    │               │                         │
│                     │               │  Call 2 — company:      │
│  Free — no key      │               │  "What notable things   │
│  No account needed  │               │   has [Company] done    │
│  Searches Google    │               │   in last 60 days?      │
│  indexed LinkedIn   │               │   Pain points for       │
│  posts              │               │   [Role] at their       │
└──────────┬──────────┘               │   stage?"               │
           │                          │                         │
           │                          │  Model: sonar-small     │
           │                          │  Web-connected          │
           │                          │  Free tier: 5 req/min   │
           └──────────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │    AI Hook Extraction        │
         │    (Claude or Groq)          │
         │                              │
         │  All raw research fed in     │
         │  Returns structured JSON:    │
         │                              │
         │  {                           │
         │    linkedin_activity: "...", │
         │    company_news: "...",      │
         │    pain_point: "...",        │
         │    connection: "..."         │
         │  }                           │
         └──────────────┬───────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │   Hooks Panel in Frontend    │
         │                              │
         │  User reviews each hook      │
         │  Can edit any text           │
         │  Can delete unwanted hooks   │
         │  Edited hooks passed to      │
         │  /api/generate               │
         └──────────────────────────────┘
```

---

## AI provider fallback

```
/api/generate OR /api/research called
              │
              ▼
  ANTHROPIC_API_KEY in env?
        │              │
       yes             no ──────────────────┐
        │                                   │
        ▼                                   ▼
  Call Claude                         Call Groq
  Haiku 4.5                           llama-3.3-70b
        │                             (OpenAI-compat.)
        ▼
  anthropic.APIError?
        │          │
       yes         no
        │           │
        ▼           ▼
  Call Groq    Return result
  fallback     { ..., provider: "claude" }
        │
        ▼
  Return result
  { ..., provider: "groq" }
```

---

## Vercel deployment architecture

```
GitHub repo
     │
     │  git push / vercel --prod
     ▼
Vercel Build
     │
     ├── api/index.py ──────────► Serverless Python Function
     │   (FastAPI app)            Runtime: Python 3.11
     │                            Timeout: 10s (free tier)
     │                            Cold start: ~1–2s
     │
     └── frontend/ ─────────────► Static file serving
         coldemail.html           CDN edge cached
                                  Instant load
         │
         │  Routes (vercel.json):
         │  /api/* → serverless function
         │  /*     → static files
         ▼
  vercel.app domain (free)
  Custom domain (free, 1 per project)

  Environment variables:
  Set via `vercel env add` or dashboard
  Available to serverless function at runtime
  Never exposed to static frontend
```

---

## Notion data model

```
Notion Database: "Cold Emails"
─────────────────────────────────────────────────────
Name          │ Title        │ Contact person name
Company       │ Text         │ Company name
Role          │ Text         │ Their role/title
Email         │ Email        │ Recipient email
LinkedIn      │ URL          │ Their LinkedIn URL
Job Link      │ URL          │ Job posting URL
Tone Used     │ Select       │ Formal/Conversation/etc.
Email Draft   │ Rich text    │ Final body that was sent
Hooks Used    │ Rich text    │ Research hooks used
Status        │ Select       │ Sent / Followed Up
Sent Date     │ Date         │ ISO date of send
─────────────────────────────────────────────────────

Flow:
User sends email
      ↓
POST /api/notion/save
      ↓
New row created — Status: Sent
      ↓
Notion becomes searchable history of all outreach
Filter by: company, date range, tone, status
```

---

## What was removed vs v1

| Feature | v1 | v2 (current) |
|---|---|---|
| Scheduler (launchd) | ✓ | Removed |
| Pending lead queue | ✓ | Removed |
| Load from Notion | ✓ | Removed |
| Approved status | ✓ | Removed |
| Auto-send | ✓ | Removed |
| Research feature | — | Added |
| DuckDuckGo LinkedIn search | — | Added |
| Perplexity integration | — | Added |
| Hooks panel UI | — | Added |
| Vercel deployment | Render | Vercel (simpler) |
| Notion role | Lead DB + log | Log only |
