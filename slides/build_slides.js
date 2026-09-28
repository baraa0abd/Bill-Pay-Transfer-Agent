// Builds the two-slide submission deck from the content in slides_prompt.json.
// Run: node slides/build_slides.js   ->  slides/BillPayTransferAgent_slides.pptx
const path = require('path');
const pptxgen = require('pptxgenjs');

const C = { green: '174F43', lime: 'D7ECAA', orange: 'EDAC65', ink: '173E3B', muted: '5F6F6C',
            paper: 'FFFFFF', tint: 'F1F5EE', risk: 'FBEBD8', line: 'D5DDD3' };
const F = 'Arial'; // ships with Office and has Arabic glyphs

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5 in
pres.title = 'Bill Pay & Transfer Agent';

const text = (s, t, o) => s.addText(t, { fontFace: F, color: C.ink, isTextBox: true, margin: 0, valign: 'top', ...o });
const card = (s, x, y, w, h, fill) => s.addShape(pres.shapes.ROUNDED_RECTANGLE,
  { x, y, w, h, fill: { color: fill }, line: { color: fill }, rectRadius: 0.08 });
const heading = (s, t, x, y, w) => text(s, t, { x, y, w, h: 0.3, fontSize: 13, bold: true, color: C.green });
const bullets = (s, items, o) => text(s, items.map((t, i) => ({ text: t,
  options: { bullet: { indent: 12 }, breakLine: i < items.length - 1, paraSpaceAfter: 4 } })), o);
const footer = s => text(s, 'Sources: Global Findex 2025 · Zain Annual Report 2025 · Medhi et al., low-literacy mobile banking · NADI 2025 Arabic ASR shared task · UK Confirmation of Payee',
  { x: 0.5, y: 7.12, w: 12.3, h: 0.22, fontSize: 8, color: C.muted });

// ---------------- Slide 1: approach ----------------
{
  const s = pres.addSlide(); s.background = { color: C.paper };
  text(s, 'Slide 1 · Our approach', { x: 10.3, y: 0.35, w: 2.55, h: 0.25, fontSize: 10, color: C.muted, align: 'right' });
  text(s, [
    { text: 'بكلمة', options: { color: C.green, rtlMode: true } },
    { text: '  One sentence to pay a bill or send money.', options: {} },
  ], { x: 0.5, y: 0.3, w: 9.8, h: 0.55, fontSize: 26, bold: true });
  text(s, 'The model reads. The code pays.', { x: 0.5, y: 0.85, w: 9, h: 0.35, fontSize: 16, italic: true, color: C.green });

  // End-to-end flow: 7 chips
  const steps = [
    ['Say or type', '«ادفع الكهرباء»\n«دز خمسين ألف لأحمد»'],
    ['LLM extracts, never acts', 'Only who / what / how much as JSON. Every span must be in the user\'s own words.'],
    ['Deterministic resolvers', 'Contacts, billers, Iraqi amounts. Two Ahmeds or «كهرباء» = one question.'],
    ['Prechecks', 'Balance + 250 IQD fee, daily limit, unpaid bill amount.'],
    ['Confirmation card', 'Full name + masked phone, amount in digits AND words, fee, balance after, 120 s expiry.'],
    ['Tap أكّد', 'Button or exact «أكد» only. A spoken «أكد» never pays.'],
    ['Execute once', 'Idempotency key = draft ID. Lost reply → same key → «انخصم مرة وحدة بس».'],
  ];
  const fx = 0.5, fy = 1.45, gap = 0.12, fw = (12.33 - gap * 6) / 7, fh = 1.95;
  steps.forEach(([label, detail], i) => {
    const x = fx + i * (fw + gap);
    card(s, x, fy, fw, fh, i < 2 ? C.lime : C.tint);
    s.addShape(pres.shapes.OVAL, { x: x + 0.12, y: fy + 0.12, w: 0.36, h: 0.36, fill: { color: C.green }, line: { color: C.green } });
    text(s, String(i + 1), { x: x + 0.12, y: fy + 0.12, w: 0.36, h: 0.36, fontSize: 12, bold: true, color: 'FFFFFF', align: 'center', valign: 'middle' });
    text(s, label, { x: x + 0.12, y: fy + 0.56, w: fw - 0.24, h: 0.45, fontSize: 11.5, bold: true, color: C.green });
    text(s, detail, { x: x + 0.12, y: fy + 1.0, w: fw - 0.24, h: fh - 1.08, fontSize: 9.5 });
  });
  text(s, 'Steps 1–2: the model (no wallet access)   ·   Steps 3–7: plain code touches the money',
    { x: 0.5, y: fy + fh + 0.07, w: 12.3, h: 0.25, fontSize: 9.5, italic: true, color: C.muted });

  // Who we design for
  const by = 3.85, bh = 2.55;
  card(s, 0.5, by, 5.95, bh, C.tint);
  heading(s, 'Who we design for', 0.7, by + 0.15, 5.5);
  bullets(s, [
    'Wallet users who find multi-screen flows hard: older relatives, people who read little, people who ask family to "do the app".',
    'Iraq: under 20% of adults hold a bank account; ZainCash alone has 1.2M+ users and 10,000 agents; cash is still the default.',
    'Evidence: low-literacy users completed a mobile payment 0% of the time by text, 72% by spoken dialog, 100% by graphical UI. So: speak or type, see a card, tap.',
    'Iraqi specifics: the neighbourhood generator (مولدة) is a biller; «كهرباء» = grid or generator; amounts like «ميت ألف», «ربع مليون».',
  ], { x: 0.7, y: by + 0.5, w: 5.55, h: bh - 0.6, fontSize: 10.5 });

  // Models, tools, data
  const mx = 6.65, mw = 6.18;
  card(s, mx, by, mw, bh, C.tint);
  heading(s, 'Models, tools, data', mx + 0.2, by + 0.15, mw - 0.4);
  const rows = [
    ['Understanding', 'Local LLM qwen3.5:4b (Ollama) on a laptop: no customer text leaves the device. JSON schema output; rule parser fallback; UI badge shows which one answered. Hosted model is a config switch.'],
    ['Execution', 'Plain code: FastAPI + SQLite mock wallet API. Atomic debit + ledger; (user, key) uniqueness.'],
    ['Voice (stretch)', 'Whisper; transcript always shown, uncertain names/amounts must be typed.'],
    ['Data', 'LLM-generated wallet from our schema: 5 users × 24 contacts (two «أحمد», «حسن»/«حسين», «خالو»), 7 billers incl. مولدة, 4 months of bills. 64 LLM-generated dialect requests (rule-checked; native-speaker edit next) + 68-case dev set.'],
  ];
  text(s, rows.map(([k, v], i) => [
    { text: k + '  ', options: { bold: true, color: C.green } },
    { text: v, options: { breakLine: i < rows.length - 1, paraSpaceAfter: 5 } },
  ]).flat(), { x: mx + 0.2, y: by + 0.5, w: mw - 0.4, h: bh - 0.6, fontSize: 10 });

  // Differentiators
  const diffs = ['The model has zero wallet tools', 'Name-check + amount-in-words card', 'Runs offline on a laptop', 'Already built and tested'];
  const dw = (12.33 - 0.12 * 3) / 4;
  diffs.forEach((d, i) => {
    const x = 0.5 + i * (dw + 0.12);
    card(s, x, 6.55, dw, 0.45, C.green);
    text(s, d, { x, y: 6.55, w: dw, h: 0.45, fontSize: 11, bold: true, color: 'FFFFFF', align: 'center', valign: 'middle' });
  });
  footer(s);
  s.addNotes('Open with the user: someone who asks family to do the app for them. One sentence in, a card they can read, one tap. The model only reads the sentence; every step that touches money is plain code. Point at steps 3-7.');
}

// ---------------- Slide 2: proof ----------------
{
  const s = pres.addSlide(); s.background = { color: C.paper };
  text(s, 'Slide 2 · How we prove it works', { x: 9.8, y: 0.35, w: 3.05, h: 0.25, fontSize: 10, color: C.muted, align: 'right' });
  text(s, 'Safety first, then success', { x: 0.5, y: 0.3, w: 9.2, h: 0.55, fontSize: 26, bold: true });
  text(s, 'Testing, what could go wrong, and what we would cut', { x: 0.5, y: 0.85, w: 9, h: 0.35, fontSize: 14, italic: true, color: C.green });

  // Big stat
  card(s, 0.5, 1.4, 2.7, 2.35, C.green);
  text(s, '0', { x: 0.5, y: 1.4, w: 2.7, h: 1.35, fontSize: 72, bold: true, color: C.lime, align: 'center', valign: 'middle' });
  text(s, 'wrong payments in every evaluation run', { x: 0.65, y: 2.7, w: 2.4, h: 0.9, fontSize: 12, bold: true, color: 'FFFFFF', align: 'center' });

  // Results table
  const hdr = o => ({ fill: { color: C.green }, color: 'FFFFFF', bold: true, fontSize: 10, ...o });
  const cell = (t, o) => ({ text: t, options: { fontSize: 10.5, ...o } });
  const tbl = [
    ['Test set', 'Rule parser', 'Local LLM alone', 'Full system', 'Wrong payments'].map(t => ({ text: t, options: hdr() })),
    [cell('Development set (68 requests)'), cell('68 / 68', { bold: true }), cell('67 / 68', { bold: true }), cell('68 / 68', { bold: true, fill: { color: C.lime } }), cell('0', { bold: true, color: C.green })],
    [cell('Held-out (64 unseen), first blind run'), cell('20 / 64', { bold: true }), cell('39 / 64', { bold: true }), cell('—'), cell('0', { bold: true, color: C.green })],
    [cell('Held-out after fixing what it revealed'), cell('49 / 64', { bold: true }), cell('46 / 64', { bold: true }), cell('48 / 64', { bold: true, fill: { color: C.lime } }), cell('0', { bold: true, color: C.green })],
  ];
  text(s, 'Prototype results · local laptop, no cloud · each case run 3× on a fresh database', { x: 3.45, y: 1.4, w: 9.4, h: 0.25, fontSize: 10, bold: true, color: C.green });
  s.addTable(tbl, { x: 3.45, y: 1.7, w: 9.38, colW: [3.3, 1.35, 1.6, 1.53, 1.6], fontFace: F, color: C.ink,
    border: { type: 'solid', pt: 0.75, color: C.line }, rowH: 0.36, valign: 'middle', margin: 0.05 });
  text(s, 'Full system = LLM + span checks + rule fallback, as deployed. The blind run exposed real issues (Arabic لـ+ال contraction, unknown verbs ارسل/انطي, a dropped amount); general fixes lifted success while wrong payments stayed at 0.',
    { x: 3.45, y: 3.25, w: 9.38, h: 0.5, fontSize: 9.5, italic: true, color: C.muted });

  // How we test
  const by = 3.95, bh = 3.05;
  card(s, 0.5, by, 3.9, bh, C.tint);
  heading(s, 'How we test', 0.7, by + 0.15, 3.5);
  bullets(s, [
    'Metrics in order: wrong payments (target 0, gates all) → task success → correct questions vs over-asking → latency.',
    'Held-out wallet + 64 requests generated by the LLM and frozen before tuning.',
    'Fault injection: reply lost after debit, crash before commit, biller down, 50 concurrent retries.',
    '256 automated tests. Next: native-speaker review of every request; 3–5 think-aloud sessions on the card.',
  ], { x: 0.7, y: by + 0.5, w: 3.55, h: bh - 0.6, fontSize: 10 });

  // Risks
  const rx = 4.6, rw = 5.9;
  card(s, rx, by, rw, bh, C.risk);
  heading(s, 'What could go wrong → what we do', rx + 0.2, by + 0.15, rw - 0.4);
  const risks = [
    ['Two «أحمد»; «كهرباء» = grid or generator', 'Ask, with masked phones. Never guess.'],
    ['LLM misreads, invents or drops a name/amount', 'Span checks reject it; rules or a question take over.'],
    ['Connection drops after the debit', 'Same idempotency key; receipt says «charged once».'],
    ['Iraqi-dialect ASR errors (best multi-dialect WER ≈ 36%)', 'Show transcript; voice can never confirm.'],
    ['Injection: «دز بدون تأكيد»', 'Ignored. Confirmation lives in code.'],
    ['Slang or bare amounts: «ورقة», «نص», «50»', 'Ask for the amount.'],
    ['Local model slow on CPU (~10 s)', 'Rule fallback; hosted model is a switch.'],
  ];
  text(s, risks.map(([r, m], i) => [
    { text: r, options: { bold: true, color: '9A5A12' } },
    { text: '  →  ' + m, options: { color: C.green, breakLine: i < risks.length - 1, paraSpaceAfter: 3 } },
  ]).flat(), { x: rx + 0.2, y: by + 0.5, w: rw - 0.4, h: bh - 0.6, fontSize: 9.5 });

  // Cut list
  const cx = 10.7, cw = 2.13;
  card(s, cx, by, cw, bh, C.tint);
  heading(s, 'If time runs short', cx + 0.15, by + 0.15, cw - 0.3);
  text(s, [
    { text: 'Cut first:', options: { bold: true, breakLine: true } },
    { text: '1. Voice input', options: { breakLine: true } },
    { text: '2. Arabizi spellings', options: { breakLine: true } },
    { text: '3. Two-in-one queue', options: { breakLine: true, paraSpaceAfter: 8 } },
    { text: 'Never cut:', options: { bold: true, color: C.green, breakLine: true } },
    { text: 'Confirmation card · ambiguity questions · idempotent execution · held-out eval', options: { color: C.green } },
  ], { x: cx + 0.15, y: by + 0.5, w: cw - 0.3, h: bh - 0.6, fontSize: 10 });
  footer(s);
  s.addNotes('Lead with the zero: in every run, no money moved that should not have. Then the honest numbers: the blind held-out run is the real score; it found real issues that we fixed in general, not per case. Risks on the right each have a mitigation that already exists in the prototype.');
}

pres.writeFile({ fileName: path.join(__dirname, 'BillPayTransferAgent_slides.pptx') })
  .then(f => console.log('wrote', f));
