# Cold Email Generator — Architecture

## System overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        VERCEL (free tier)                            │
│                                                                      │
│  ┌─────────────────────────────┐  ┌───────────────────────────────┐ │
│  │   STATIC FRONTEND           │  │   SERVERLESS BACKEND          │ │
│  │   frontend/index.html       │  │   api/index.py → backend/     │ │
│  │   frontend/css/styles.css   │  │                               │ │
│  │   frontend/js/app.js        │  │   FastAPI — all routes        │ │
│  │                             │  │   prefixed /api/              │ │
│  │  Fraunces + DM Sans         │  │   Python serverless function  │ │
│  │  Brick-red on cream         │  │   10s timeout per request     │ │
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
   │ Claude Haiku 4.5 │  │ DuckDuckGo HTML  │  │ Notion API          │
   │ (primary)        │  │ (LinkedIn posts) │  │ (email logging)     │
   │       ↓ fails    │  │ Free — no key    │  │                     │
   │ Groq llama-3.3   │  └──────────────────┘  └─────────────────────┘
   │ (free fallback)  │
   └──────────────────┘
```

---

## Full user workflow

```
                        USER OPENS frontend/index.html
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
                    │  DuckDuckGo → LinkedIn posts │
                    │  AI → extract 3 clean hooks  │
                    │                              │
                    │  User reviews + edits hooks  │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │         STEP 4               │
                    │      Pick tone(s)            │
                    │                              │
                    │  ┌────────┐ ┌─────────────────┐ │
                    │  │ Formal │ │ Conversational  │ │
                    │  └────────┘ └─────────────────┘ │
                    │  ┌──────────────┐ ┌──────────┐  │
                    │  │ Story Driven │ │Data      │  │
                    │  └──────────────┘ │Driven    │  │
                    │                   └──────────┘  │
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
                    │    notes, contact_method }    │
                    │                              │
                    │  prompt_builder assembles    │
                    │  structured prompt           │
                    │  (email or DM format)        │
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
                    │  Editable email/DM body      │
                    │  Live word count             │
                    │  Regenerate single tab       │
                    │  Copy to clipboard           │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │         STEP 7               │
                    │      Save to Notion          │
                    │                              │
                    │  "Save to Notion" button     │
                    │  POST /api/notion/save       │
                    │  Logs: name, company, role,  │
                    │  email/LinkedIn URL,         │
                    │  job posting URL             │
                    │                              │
                    │  Success → toast             │
                    │  Failure → toast with        │
                    │  Notion error detail         │
                    └──────────────────────────────┘
```

---

## Research flow — detail

```
POST /api/research
{ name, company, role, resume_text }
         │
         ▼
┌─────────────────────┐
│  DuckDuckGo Search  │
│                     │
│  Query:             │
│  site:linkedin.com/ │
│  posts "[Name]"     │
│                     │
│  Parses HTML result │
│  Returns up to 3   │
│  snippets of public │
│  LinkedIn posts     │
│                     │
│  Free — no key      │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────────┐
│    AI Hook Extraction        │
│    (Groq only)               │
│                              │
│  DDG snippets + résumé +     │
│  role + company fed to Groq  │
│  Returns structured JSON:    │
│                              │
│  {                           │
│    linkedin_activity: "...", │
│    pain_point: "...",        │
│    resume_connection: "..."  │
│  }                           │
│                              │
│  role + company sharpen the  │
│  pain_point hook             │
│  Falls back to empty hooks   │
│  if Groq unavailable         │
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

### Email generation (/api/generate)

```
ANTHROPIC_API_KEY in env?
      │              │
     yes             no ──────────────────┐
      │                                   │
      ▼                                   ▼
Call Claude                         Call Groq
Haiku 4.5                           llama-3.3-70b
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

### Research hook extraction (/api/research)

```
GROQ_API_KEY in env?
      │              │
     yes             no
      │               │
      ▼               ▼
Call Groq       Return default
llama-3.3-70b   empty hooks
      │         { ..., provider: "none" }
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
         index.html               CDN edge cached
         css/styles.css           Instant load
         js/app.js
         │
         │  Routes (vercel.json):
         │  /api/* → serverless function
         │  /*     → static files
         ▼
  vercel.app domain (free)
  Custom domain (free, 1 per project)
```

---

## Notion data model

```
Notion Database: "Cold Emails"
─────────────────────────────────────────────────────────────────
Database properties (filterable/sortable columns):

Name            │ Title   │ Person name
Company         │ Text    │ Company
Role            │ Text    │ Their role
Contact Method  │ Select  │ email | linkedin
Email           │ Email   │ Recipient email address
LinkedIn URL    │ URL     │ LinkedIn profile URL
Job Link        │ URL     │ Job posting URL
Tone            │ Select  │ Formal | Conversational | Story Driven | Data Driven
Provider        │ Select  │ claude | groq
─────────────────────────────────────────────────────────────────

Flow:
User clicks "Save to Notion"
      ↓
POST /api/notion/save (minimal metadata payload)
      ↓
New row created in Notion with properties only
      ↓
Notion becomes searchable history of all outreach
Filter by: company, tone, provider, contact method, date
```
