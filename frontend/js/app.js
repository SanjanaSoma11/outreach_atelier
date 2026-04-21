const BASE_URL = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") ? "http://localhost:8000" : "";

  const TWEAKS = /*EDITMODE-BEGIN*/{
    "accent": "#8B2500",
    "heading": "serif-italic",
    "texture": "none"
  }/*EDITMODE-END*/;

  const TONES = ["Formal","Conversational","Story Driven","Data Driven"];
  const state = {
    selected: new Set(["Formal"]),
    drafts: {},
    activeTab: null,
    resumeText: '',
    hooks: {},
    provider: '',
  };

  // Date
  const today = new Date();
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  document.getElementById('today-date').textContent = `${months[today.getMonth()]} ${today.getDate()}, ${today.getFullYear()}`;

  // Health check on load — injects green/yellow dot into brand
  (async () => {
    try {
      const r = await fetch(`${BASE_URL}/api/health`);
      if (!r.ok) return;
      const d = await r.json();
      if (d.provider !== 'none') {
        const dot = document.createElement('span');
        dot.style.cssText = 'display:inline-block;width:8px;height:8px;border-radius:50%;margin-left:4px;vertical-align:middle;flex-shrink:0;background:'
          + (d.provider === 'claude' ? '#22c55e' : '#eab308');
        dot.title = d.provider === 'claude' ? 'Claude active' : 'Groq fallback';
        document.querySelector('.brand').appendChild(dot);
      }
    } catch {}
  })();

  // Tone selection
  const tonesEl = document.getElementById('tones');
  const selCount = document.getElementById('sel-count');
  const goLabel = document.getElementById('go-label');
  const switchAll = document.getElementById('switch-all');
  function refreshSelection() {
    document.querySelectorAll('.chip').forEach(c => c.classList.toggle('active', state.selected.has(c.dataset.tone)));
    const n = state.selected.size;
    selCount.textContent = n;
    goLabel.textContent = n === 1 ? `Generate ${[...state.selected][0]} draft` : n === 4 ? `Generate all 4` : `Generate ${n} drafts`;
    switchAll.textContent = n === 4 ? 'Clear selection' : 'Select all 4 →';
  }
  tonesEl.addEventListener('click', e => {
    const chip = e.target.closest('.chip'); if (!chip) return;
    const t = chip.dataset.tone;
    if (state.selected.has(t)) { if (state.selected.size > 1) state.selected.delete(t); }
    else state.selected.add(t);
    refreshSelection();
  });
  switchAll.addEventListener('click', () => {
    state.selected = state.selected.size === 4 ? new Set(["Formal"]) : new Set(TONES);
    refreshSelection();
  });

  // Resume upload → POST /api/parse-pdf
  const resume = document.getElementById('resume');
  const upload = document.getElementById('upload');
  const ut1 = document.getElementById('upload-t1');
  const ut2 = document.getElementById('upload-t2');
  const clearBtn = document.getElementById('upload-clear');
  resume.addEventListener('change', async () => {
    const f = resume.files[0];
    if (!f) { resetUpload(); return; }
    upload.classList.add('has-file');
    ut1.textContent = f.name;
    ut2.textContent = `${(f.size / 1024).toFixed(0)} KB · parsing…`;
    const form = new FormData();
    form.append('file', f);
    try {
      const r = await fetch(`${BASE_URL}/api/parse-pdf`, { method: 'POST', body: form });
      if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || r.statusText); }
      const d = await r.json();
      state.resumeText = d.text;
      ut2.textContent = `${(f.size / 1024).toFixed(0)} KB · parsed ✓`;
    } catch (e) {
      state.resumeText = '';
      ut2.textContent = 'Parse failed — generating without résumé text';
      toast('PDF parse failed: ' + e.message, 'error');
    }
  });
  clearBtn.addEventListener('click', e => {
    e.preventDefault(); e.stopPropagation();
    resume.value = ''; state.resumeText = '';
    resetUpload();
  });
  function resetUpload() {
    upload.classList.remove('has-file');
    ut1.textContent = 'Upload pdf here';
    ut2.textContent = 'Drag a file or click to browse';
  }
  ['dragenter','dragover'].forEach(ev => upload.addEventListener(ev, e => { e.preventDefault(); upload.style.background = 'var(--brick-tint-2)'; }));
  ['dragleave','drop'].forEach(ev => upload.addEventListener(ev, e => { e.preventDefault(); upload.style.background = ''; }));
  upload.addEventListener('drop', e => {
    const f = e.dataTransfer.files[0];
    if (f && f.type === 'application/pdf') {
      const dt = new DataTransfer(); dt.items.add(f); resume.files = dt.files;
      resume.dispatchEvent(new Event('change'));
    }
  });

  // Notes field
  const notes = document.getElementById('notes');
  const notesCount = document.getElementById('notes-count');
  function updateNotesCount() {
    notesCount.textContent = `${notes.value.length} / 500`;
    notesCount.style.color = notes.value.length > 450 ? 'var(--brick)' : '';
  }
  notes.addEventListener('input', updateNotesCount);
  document.getElementById('tag-strip').addEventListener('click', e => {
    const btn = e.target.closest('.tag-pill'); if (!btn) return;
    const phrase = btn.dataset.add;
    const cur = notes.value.trim();
    notes.value = cur ? `${cur} · ${phrase}` : phrase;
    updateNotesCount();
    notes.focus();
  });
  updateNotesCount();

  // Contact method toggle
  const methodToggle = document.getElementById('method-toggle');
  const contactInput = document.getElementById('contact');
  const contactPfx = document.getElementById('contact-pfx');
  const contactNote = document.getElementById('contact-note');
  let contactMethod = 'email';
  const ICON_EMAIL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg>';
  const ICON_LI = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M4.98 3.5a2.5 2.5 0 11.02 5 2.5 2.5 0 01-.02-5zM3 9h4v12H3V9zm7 0h3.8v1.7h.05c.53-1 1.84-2.05 3.78-2.05 4.04 0 4.78 2.66 4.78 6.12V21h-4v-5.5c0-1.3-.02-3-1.82-3s-2.1 1.42-2.1 2.9V21h-4V9z"/></svg>';
  function setMethod(m) {
    contactMethod = m;
    methodToggle.querySelectorAll('button').forEach(b => b.classList.toggle('active', b.dataset.method === m));
    if (m === 'email') {
      contactInput.type = 'email';
      contactInput.placeholder = 'priya.mehta@company.com';
      contactPfx.innerHTML = ICON_EMAIL + '<span id="contact-pfx-label">to:</span>';
      contactNote.textContent = "We'll format the draft as an email with subject line.";
    } else {
      contactInput.type = 'url';
      contactInput.placeholder = 'linkedin.com/in/priyamehta';
      contactPfx.innerHTML = ICON_LI + '<span id="contact-pfx-label">linkedin.com/in/</span>';
      contactNote.textContent = "We'll format the draft as a LinkedIn DM — no subject, shorter.";
    }
    validateContact();
  }
  function validateContact() {
    const v = contactInput.value.trim();
    if (!v) { contactNote.classList.remove('err'); return; }
    const ok = contactMethod === 'email'
      ? /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)
      : /linkedin\.com\/in\/|^[\w\-]+$/i.test(v);
    contactNote.classList.toggle('err', !ok);
    if (!ok) contactNote.textContent = contactMethod === 'email' ? 'That doesn\u2019t look like a valid email.' : 'Enter a LinkedIn profile URL or handle.';
    else if (contactMethod === 'email') contactNote.textContent = "Email looks good. We'll draft with a subject line.";
    else contactNote.textContent = "Looks good. We'll draft as a LinkedIn DM — no subject.";
  }
  methodToggle.addEventListener('click', e => { const b = e.target.closest('button'); if (b) setMethod(b.dataset.method); });
  contactInput.addEventListener('input', validateContact);

  // Research → POST /api/research
  const researchBtn = document.getElementById('research-btn');
  const HOOK_LABELS = {
    linkedin_activity: 'LinkedIn Activity',
    company_news: 'Company News',
    pain_point: 'Pain Point',
    connection: 'Resume Connection',
    resume_connection: 'Resume Connection',
  };
  researchBtn.addEventListener('click', async () => {
    const person = document.getElementById('person').value.trim();
    const role = document.getElementById('role').value.trim();
    const company = document.getElementById('company').value.trim();
    if (!person || !company) { toast('Enter a person name and company first', 'error'); return; }
    researchBtn.disabled = true; researchBtn.classList.add('busy');
    try {
      const r = await fetch(`${BASE_URL}/api/research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: person, role, company, resume_text: state.resumeText }),
      });
      if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || r.statusText); }
      const data = await r.json();
      renderHooks(data.hooks);
      toast('Research complete');
    } catch (e) {
      toast('Research failed — you can still generate without hooks', 'error');
    } finally {
      researchBtn.disabled = false; researchBtn.classList.remove('busy');
    }
  });

  function renderHooks(hooks) {
    state.hooks = {};
    const grid = document.getElementById('hooks-grid');
    grid.innerHTML = '';
    Object.entries(hooks).forEach(([key, val]) => {
      if (!val) return;
      state.hooks[key] = val;
      const card = document.createElement('div');
      card.className = 'hook-card';
      card.innerHTML = `
        <div class="hook-head">
          <span class="hook-label">${HOOK_LABELS[key] || key}</span>
          <button class="hook-del" type="button" data-key="${key}">✕</button>
        </div>
        <textarea class="hook-body">${esc(val)}</textarea>`;
      card.querySelector('.hook-del').addEventListener('click', () => {
        delete state.hooks[key]; card.remove();
      });
      card.querySelector('.hook-body').addEventListener('input', e => { state.hooks[key] = e.target.value; });
      grid.appendChild(card);
    });
    document.getElementById('hooks-section').hidden = false;
  }

  // Generate → POST /api/generate
  const goBtn = document.getElementById('go');
  const tabsEl = document.getElementById('tabs');
  const panelsEl = document.getElementById('panels');
  const copyBtn = document.getElementById('copy');
  const regenBtn = document.getElementById('regen');
  const sendBtn = document.getElementById('send');

  goBtn.addEventListener('click', async () => {
    const inputs = collectInputs();
    if (!inputs.jd.trim()) { focusField('jd'); return; }
    const tonesToGen = [...state.selected];
    setBusy(true);
    initDrafts(tonesToGen);
    try {
      const r = await fetch(`${BASE_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resume_text: state.resumeText,
          job_description: inputs.jd,
          person_name: inputs.person,
          person_role: inputs.role,
          company: inputs.company,
          tones: tonesToGen,
          hooks: state.hooks,
          notes: inputs.notes,
          context: inputs.context,
          user_name: 'the applicant',
          contact_method: inputs.method,
        }),
      });
      if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || r.statusText); }
      const data = await r.json();
      if (data.provider) state.provider = data.provider;
      const emailMap = {};
      (data.emails || []).forEach(e => { emailMap[e.tone] = e; });
      tonesToGen.forEach(tone => {
        const e = emailMap[tone] || { subject: '', body: '' };
        state.drafts[tone] = { status: 'ready', subject: e.subject || '', body: e.body || '' };
        renderPanel(tone);
        const tab = [...document.querySelectorAll('.tab')].find(t => t.dataset.tone === tone);
        if (tab) tab.classList.add('has-content');
      });
      if (state.activeTab) activateTab(state.activeTab);
    } catch (e) {
      toast('Generation failed: ' + e.message, 'error');
      tonesToGen.forEach(tone => { state.drafts[tone] = { status: 'error', subject: '', body: '' }; });
    } finally {
      setBusy(false);
    }
  });

  function collectInputs() {
    return {
      jd: document.getElementById('jd').value,
      person: document.getElementById('person').value.trim() || 'there',
      role: document.getElementById('role').value.trim() || 'team',
      company: document.getElementById('company').value.trim(),
      notes: document.getElementById('notes').value.trim(),
      context: document.getElementById('context').value.trim(),
      method: contactMethod,
      contact: contactInput.value.trim(),
      jobLink: document.getElementById('job-link').value.trim(),
    };
  }
  function focusField(id) {
    const el = document.getElementById(id); el.focus();
    el.style.boxShadow = '0 0 0 4px rgba(196,71,31,0.35)';
    setTimeout(() => el.style.boxShadow = '', 1200);
  }
  function setBusy(b) { goBtn.disabled = b; goBtn.classList.toggle('busy', b); }

  function initDrafts(toneList) {
    // Remove the static empty placeholder on first real generate
    const emptyPanel = panelsEl.querySelector('[data-panel="empty"]');
    if (emptyPanel) emptyPanel.remove();

    toneList.forEach(tone => {
      state.drafts[tone] = { status: 'loading', subject: '', body: '' };
      const existingTab = tabsEl.querySelector(`[data-tone="${CSS.escape(tone)}"]`);
      if (existingTab) {
        // Tab already exists — reset its panel to loading and strip ready marker
        existingTab.classList.remove('has-content');
        const panel = panelsEl.querySelector(`[data-panel="${CSS.escape(tone)}"]`);
        if (panel) panel.innerHTML = loadingMarkup();
      } else {
        // New tone — create tab and panel
        const tab = document.createElement('button');
        tab.className = 'tab';
        tab.dataset.tone = tone;
        tab.innerHTML = `<span class="dot"></span>${tone}`;
        tab.addEventListener('click', () => activateTab(tone));
        tabsEl.appendChild(tab);
        const panel = document.createElement('div');
        panel.className = 'panel';
        panel.dataset.panel = tone;
        panel.innerHTML = loadingMarkup();
        panelsEl.appendChild(panel);
      }
    });

    // Switch to the first tone being generated
    activateTab(toneList[0]);
    [copyBtn, regenBtn, sendBtn].forEach(b => b.disabled = true);
  }
  function loadingMarkup() {
    return `<div class="skeleton title"></div><div class="skeleton med"></div><div class="skeleton"></div><div class="skeleton short"></div><div class="skeleton"></div><div class="skeleton med"></div><div class="skeleton short"></div>`;
  }
  function activateTab(tone) {
    state.activeTab = tone;
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tone === tone));
    document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.dataset.panel === tone));
    const ready = state.drafts[tone]?.status === 'ready';
    [copyBtn, regenBtn, sendBtn].forEach(b => b.disabled = !ready);
  }

  regenBtn.addEventListener('click', async () => {
    const tone = state.activeTab;
    const inputs = collectInputs();
    const panel = panelsEl.querySelector(`[data-panel="${CSS.escape(tone)}"]`);
    if (panel) panel.innerHTML = loadingMarkup();
    [copyBtn, regenBtn, sendBtn].forEach(b => b.disabled = true);
    state.drafts[tone] = { status: 'loading', subject: '', body: '' };
    try {
      const r = await fetch(`${BASE_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resume_text: state.resumeText,
          job_description: inputs.jd,
          person_name: inputs.person,
          person_role: inputs.role,
          company: inputs.company,
          tones: [tone],
          hooks: state.hooks,
          notes: inputs.notes,
          context: inputs.context,
          user_name: 'the applicant',
          contact_method: inputs.method,
        }),
      });
      if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || r.statusText); }
      const data = await r.json();
      const e = (data.emails || [])[0] || { subject: '', body: '' };
      state.drafts[tone] = { status: 'ready', subject: e.subject || '', body: e.body || '' };
      renderPanel(tone);
      const tab = [...document.querySelectorAll('.tab')].find(t => t.dataset.tone === tone);
      if (tab) tab.classList.add('has-content');
      activateTab(tone);
    } catch (e) {
      toast('Regenerate failed: ' + e.message, 'error');
      state.drafts[tone] = { status: 'error', subject: '', body: '' };
    }
  });

  function renderPanel(tone) {
    const panel = panelsEl.querySelector(`[data-panel="${CSS.escape(tone)}"]`);
    if (!panel) return;
    const d = state.drafts[tone];
    const inputs = collectInputs();
    const isDM = inputs.method === 'linkedin';
    panel.innerHTML = `
      <div class="email-meta">
        <div><span class="k">${isDM ? 'DM' : 'To'}</span><span class="v">${esc(inputs.person)}</span></div>
        <div><span class="k">Role</span><span class="v">${esc(inputs.role)}</span></div>
        <div><span class="k">Channel</span><span class="v">${isDM ? 'LinkedIn' : 'Email'}</span></div>
        <div><span class="k">Tone</span><span class="v">${tone}</span></div>
      </div>
      ${isDM ? '' : `<input class="subject-input" data-subject value="${esc(d.subject)}" />`}
      <textarea class="body-edit" data-body>${esc(d.body)}</textarea>
      <div style="font-family:var(--mono);font-size:10.5px;text-transform:uppercase;letter-spacing:0.14em;color:var(--ink-mute);margin-top:6px;text-align:right;"><span data-words>${countWords(d.body)}</span> words</div>`;
    const ta = panel.querySelector('[data-body]');
    const wc = panel.querySelector('[data-words]');
    ta.addEventListener('input', () => { wc.textContent = countWords(ta.value); state.drafts[tone].body = ta.value; });
    const subj = panel.querySelector('[data-subject]');
    if (subj) subj.addEventListener('input', e => { state.drafts[tone].subject = e.target.value; });
  }
  function countWords(s) { return (s.trim().match(/\S+/g) || []).length; }
  function esc(s) { return (s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

  copyBtn.addEventListener('click', () => {
    const d = state.drafts[state.activeTab]; if (!d) return;
    const inputs = collectInputs();
    const text = inputs.method === 'linkedin' ? d.body : `Subject: ${d.subject}\n\n${d.body}`;
    navigator.clipboard.writeText(text).then(() => toast('Copied to clipboard'));
  });

  // Save to Notion → POST /api/notion/save
  sendBtn.addEventListener('click', async () => {
    const tone = state.activeTab;
    const d = state.drafts[tone]; if (!d) return;
    const inputs = collectInputs();
    sendBtn.disabled = true;
    try {
      const r = await fetch(`${BASE_URL}/api/notion/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          person: inputs.person,
          company: inputs.company || '',
          role: inputs.role,
          contact_method: inputs.method,
          email_address: inputs.method === 'email' ? inputs.contact : '',
          linkedin_url: inputs.method === 'linkedin' ? inputs.contact : '',
          job_link: inputs.jobLink || '',
          tone: tone,
          provider: state.provider || '',
        }),
      });
      if (r.ok) {
        toast('Saved to Notion');
      } else {
        const body = await r.json().catch(() => ({}));
        toast('Notion save failed: ' + (body.detail || r.statusText), 'error');
      }
    } catch (e) {
      toast('Notion save failed: ' + e.message, 'error');
    } finally {
      sendBtn.disabled = false;
    }
  });

  const toastEl = document.getElementById('toast'); let toastT;
  function toast(msg, type) {
    toastEl.textContent = msg;
    toastEl.className = 'toast show' + (type === 'error' ? ' toast-err' : '');
    clearTimeout(toastT);
    toastT = setTimeout(() => toastEl.classList.remove('show'), type === 'error' ? 4000 : 2000);
  }
  toastEl.addEventListener('click', () => { clearTimeout(toastT); toastEl.classList.remove('show'); });

  // Tweaks
  const tweaksEl = document.getElementById('tweaks');
  const ACCENTS = [
    { name: 'brick', hex: '#8B2500', glow: '#C4471F', deep: '#6B1C00' },
    { name: 'olive', hex: '#5A6B2F', glow: '#7A8C42', deep: '#3F4B22' },
    { name: 'navy',  hex: '#1F3A5F', glow: '#3A5A85', deep: '#142845' },
    { name: 'plum',  hex: '#5B2A4A', glow: '#7E3F69', deep: '#421E36' },
    { name: 'ink',   hex: '#2A1810', glow: '#5C4636', deep: '#1A0E08' },
  ];
  const swatches = document.getElementById('swatches');
  ACCENTS.forEach(a => {
    const sw = document.createElement('div'); sw.className = 'sw'; sw.style.background = a.hex; sw.dataset.hex = a.hex; sw.title = a.name;
    sw.addEventListener('click', () => setAccent(a.hex));
    swatches.appendChild(sw);
  });
  function setAccent(hex) {
    const a = ACCENTS.find(x => x.hex === hex) || ACCENTS[0];
    document.documentElement.style.setProperty('--brick', a.hex);
    document.documentElement.style.setProperty('--brick-glow', a.glow);
    document.documentElement.style.setProperty('--brick-deep', a.deep);
    [...swatches.children].forEach(s => s.classList.toggle('sel', s.dataset.hex === hex));
    TWEAKS.accent = hex; persist();
  }
  function setHeading(v) {
    const h1 = document.querySelector('h1');
    h1.style.fontFamily = v === 'sans' ? 'var(--sans)' : 'var(--serif)';
    h1.style.fontStyle = v === 'serif-italic' ? 'italic' : 'normal';
    h1.style.fontWeight = v === 'sans' ? '700' : '600';
    document.getElementById('t-heading').value = v; TWEAKS.heading = v; persist();
  }
  function setTexture(v) {
    const dots = 'radial-gradient(circle at 20% 0%, rgba(196,71,31,0.06), transparent 45%), radial-gradient(circle at 90% 100%, rgba(139,37,0,0.05), transparent 50%), radial-gradient(circle, rgba(139,37,0,0.18) 0.9px, transparent 1.1px)';
    const grid = 'linear-gradient(rgba(139,37,0,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(139,37,0,0.08) 1px, transparent 1px)';
    document.body.style.backgroundImage = v === 'grid' ? grid : v === 'none' ? 'none' : dots;
    document.body.style.backgroundSize = v === 'grid' ? '24px 24px' : v === 'none' ? 'auto' : 'auto, auto, 22px 22px';
    document.getElementById('t-texture').value = v; TWEAKS.texture = v; persist();
  }
  function persist() { try { window.parent.postMessage({ type: '__edit_mode_set_keys', edits: TWEAKS }, '*'); } catch(e) {} }
  document.getElementById('t-heading').addEventListener('change', e => setHeading(e.target.value));
  document.getElementById('t-texture').addEventListener('change', e => setTexture(e.target.value));

  setAccent(TWEAKS.accent); setHeading(TWEAKS.heading); setTexture(TWEAKS.texture);

  window.addEventListener('message', e => {
    const t = e.data?.type;
    if (t === '__activate_edit_mode') tweaksEl.classList.add('show');
    if (t === '__deactivate_edit_mode') tweaksEl.classList.remove('show');
  });
  window.parent.postMessage({ type: '__edit_mode_available' }, '*');

  refreshSelection();
