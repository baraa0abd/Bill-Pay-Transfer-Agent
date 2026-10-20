"""Builds the 2-page design brief: python slides/build_brief.py -> slides/DesignBrief_BillPayTransferAgent.pdf"""
from pathlib import Path
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Italic', 'C:/Windows/Fonts/ariali.ttf'))
from reportlab.lib.fonts import addMapping
addMapping('Arial', 0, 0, 'Arial'); addMapping('Arial', 1, 0, 'Arial-Bold'); addMapping('Arial', 0, 1, 'Arial-Italic'); addMapping('Arial', 1, 1, 'Arial-Bold')

GREEN, LIME, TINT, INK, MUTED, RISK = (colors.HexColor(c) for c in ('#174F43', '#D7ECAA', '#F1F5EE', '#173E3B', '#5F6F6C', '#FBEBD8'))
ar = lambda s: get_display(arabic_reshaper.reshape(s))  # Arabic shaped and in visual order for the PDF
REPO = 'https://github.com/baraa0abd/Bill-Pay-Transfer-Agent'

body = ParagraphStyle('b', fontName='Arial', fontSize=9.2, leading=12, textColor=INK, alignment=TA_LEFT)
small = ParagraphStyle('s', parent=body, fontSize=8, leading=10.2, textColor=MUTED)
h1 = ParagraphStyle('h1', parent=body, fontName='Arial-Bold', fontSize=17, leading=20, textColor=GREEN)
h2 = ParagraphStyle('h2', parent=body, fontName='Arial-Bold', fontSize=10.5, leading=13, textColor=GREEN, spaceBefore=6, spaceAfter=2)
cell = ParagraphStyle('c', parent=body, fontSize=8.4, leading=10.6)
cellb = ParagraphStyle('cb', parent=cell, fontName='Arial-Bold')
P = lambda t, s=body: Paragraph(t, s)
bullets = lambda items, s=body: [Paragraph('• ' + t, ParagraphStyle('bl', parent=s, leftIndent=9, firstLineIndent=-7, spaceAfter=1.5)) for t in items]


def table(rows, widths, header=True, fill=TINT):
    t = Table([[P(c, cellb if (header and i == 0) else cell) for c in r] for i, r in enumerate(rows)], colWidths=widths)
    style = [('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, 0), (-1, -1), 0.4, colors.HexColor('#D5DDD3')),
             ('TOPPADDING', (0, 0), (-1, -1), 2.2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.2), ('LEFTPADDING', (0, 0), (-1, -1), 3)]
    if header: style.append(('BACKGROUND', (0, 0), (-1, 0), fill))
    t.setStyle(TableStyle(style)); return t


def architecture(width):
    """Two rows of four steps; steps 1-2 sit in a dashed 'LLM reads only' zone, the rest is plain code."""
    h = 5.7 * cm; d = Drawing(width, h)
    steps = [
        ('1  User', ['Types or speaks one', 'Iraqi-Arabic sentence']),
        ('2  Parser (LLM)', ['Groq / Gemini / local Ollama', 'JSON intents only; spans', 'must be in user\'s words']),
        ('3  Resolvers', ['Contacts, billers, Iraqi', 'amounts. Ambiguous =', 'one question, never a guess']),
        ('4  Dialogue state', ['Persisted conversation,', 'one question at a time,', 'two-request queue']),
        ('5  Prechecks', ['Balance + 250 IQD fee,', 'daily limit, unpaid bill']),
        ('6  Confirmation card', ['Name + masked phone, amount', 'in digits AND words, fee,', 'balance after, 120 s expiry']),
        ('7  Confirm', ['Button or exact typed', 'word only; owner, expiry,', 'SHA-256 payload checked']),
        ('8  Mock wallet API', ['FastAPI + SQLite ledger;', 'idempotency key = draft ID;', 'atomic debit']),
    ]
    bw, bh, gx = (width - 3 * 0.45 * cm) / 4, 1.85 * cm, 0.45 * cm
    rows_y = [h - 0.55 * cm - bh, 0.25 * cm]
    for i, (title, lines) in enumerate(steps):
        r, c = divmod(i, 4); x = c * (bw + gx); y = rows_y[r]
        d.add(Rect(x, y, bw, bh, rx=5, ry=5, fillColor=LIME if i < 2 else TINT, strokeColor=GREEN if i < 2 else colors.HexColor('#C9D6C4'), strokeWidth=0.8))
        d.add(String(x + 6, y + bh - 12, title, fontName='Arial-Bold', fontSize=8.2, fillColor=GREEN))
        for k, line in enumerate(lines):
            d.add(String(x + 6, y + bh - 23 - k * 9.2, line, fontName='Arial', fontSize=7, fillColor=INK))
        if c < 3:  # arrow to the next box in the row
            ax, ay = x + bw + 2, y + bh / 2
            d.add(Line(ax, ay, ax + gx - 6, ay, strokeColor=GREEN, strokeWidth=1))
            d.add(Polygon([ax + gx - 4, ay, ax + gx - 9, ay + 2.5, ax + gx - 9, ay - 2.5], fillColor=GREEN, strokeColor=GREEN))
    # turn from step 4 down to step 5
    x4 = 3 * (bw + gx) + bw / 2; x5 = bw / 2; ymid = (rows_y[0] + rows_y[1] + bh) / 2
    for a in [(x4, rows_y[0], x4, ymid), (x4, ymid, x5, ymid), (x5, ymid, x5, rows_y[1] + bh + 3)]:
        d.add(Line(*a, strokeColor=GREEN, strokeWidth=1))
    d.add(Polygon([x5, rows_y[1] + bh + 1, x5 - 2.5, rows_y[1] + bh + 6, x5 + 2.5, rows_y[1] + bh + 6], fillColor=GREEN, strokeColor=GREEN))
    # zone labels
    d.add(Rect(-3, rows_y[0] - 3, 2 * bw + gx + 6, bh + 6, fillColor=None, strokeColor=GREEN, strokeDashArray=[3, 2], strokeWidth=0.8))
    d.add(String(0, h - 0.35 * cm, 'LLM zone: reads the sentence, has NO wallet tools', fontName='Arial-Bold', fontSize=7.4, fillColor=GREEN))
    d.add(String(2 * (bw + gx), h - 0.35 * cm, 'Plain, tested code: everything that touches money', fontName='Arial-Bold', fontSize=7.4, fillColor=MUTED))
    return d


def build(out):
    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=1.45 * cm, rightMargin=1.45 * cm, topMargin=1.2 * cm, bottomMargin=1.1 * cm,
                            title='Design brief: Bill Pay & Transfer Agent', author='Agentic AI Challenge Iraq, topic 04')
    W = A4[0] - 2.9 * cm
    s = []
    s.append(P(ar('بكلمة') + '  ·  Bill Pay &amp; Transfer Agent', h1))
    s.append(P(f'Design brief · Agentic AI Challenge Iraq, topic 04 · Build stage, October 2026 · GitHub: <a href="{REPO}" color="#174F43"><u>{REPO.replace("https://", "")}</u></a>', small))
    s.append(Spacer(1, 4))
    s.append(P('<b>One sentence in Iraqi Arabic, typed or spoken, becomes a confirmed payment.</b> The model only reads the sentence; '
               'plain code checks, asks, confirms and pays. A working prototype already exists, so this brief is a plan grounded in measured results.'))

    s.append(P('1. The user and the problem', h2))
    s += bullets([
        'Wallet users who abandon multi-screen payment flows or make mistakes in them: older relatives, people who read little, people who ask family to "do the app" for them. '
        'Fewer than 20% of Iraqi adults hold a bank account; ZainCash alone has 1.2M+ users and 10,000 agents, and cash is still the default.',
        'Design evidence: in a mobile-banking study, low-literacy users completed a payment 0% of the time with a text interface, 72% with spoken dialogue and 100% with a graphical UI. '
        'So the flow is: speak or type one sentence, see a clear card, tap to confirm.',
        f'Iraqi specifics the agent must handle: the neighbourhood generator ({ar("مولدة")}) is a biller; "{ar("كهرباء")}" can mean the grid or the generator; '
        f'amounts are said as {ar("ميت ألف")} or {ar("ربع مليون")}; two contacts are often both called {ar("أحمد")}.',
        'Next: 3-5 short interviews and think-aloud sessions on the confirmation card (week 2). No interviews are claimed yet.'])

    s.append(P('2. How it works end to end', h2))
    s.append(architecture(W))
    s.append(P('If the LLM is down, refuses, invents a name, drops a typed number or splits one request in two, its output is rejected and a conservative rule parser '
               'takes over; if that also fails, nothing is drafted. A UI badge shows which one understood each request. A lost reply after a debit is retried with the '
               'same key and the wallet replays the stored receipt, so a retry can never pay twice.', small))

    s.append(P('3. Models, tools and data', h2))
    s.append(table([
        ['Part', 'Choice', 'Why'],
        ['Understanding', 'Groq <b>gpt-oss-120b</b> (free, strict JSON schema) for development and evaluation; Gemini Flash for Arabic checks; local <b>qwen3.5:4b</b> (Ollama) offline; rule parser as fallback',
         'Free tiers per the challenge guide; one OpenAI-compatible client, so switching is a setting. Local model keeps working without internet.'],
        ['Execution', 'FastAPI + SQLite mock wallet API (contacts, billers, balances, history); Pydantic schemas; RapidFuzz for names',
         'Deterministic, testable, no model in the money path.'],
        ['Voice (stretch)', 'Whisper speech-to-text; transcript always shown', 'Iraqi-dialect ASR is error-prone; voice can never confirm.'],
        ['Synthetic data', 'An LLM fills a wallet blueprint from our schema (names, balances, billers, bill amounts); code expands IDs, phones, dates and history. '
         'Labelled Iraqi-dialect requests are generated per outcome (execute, ask, split, refuse) with the needed label fields required, checked against the wallet, then hand-edited.',
         'Small models mislabel when everything is optional; per-outcome schemas and wallet checks catch it. All data is synthetic.'],
    ], [2.4 * cm, 8.7 * cm, W - 11.1 * cm]))

    s.append(P('4. How we test it: what a good result looks like', h2))
    s.append(table([
        ['Metric (in priority order)', 'Target at MVP', 'Measured today (prototype)'],
        ['<b>Wrong payments</b>: money moved to the wrong person, biller or amount', '<b>0</b>, a hard gate', '<b>0</b> in every evaluation run'],
        ['Task success, development set (68 requests)', '100%', 'Groq alone 68/68; full system 68/68; 0 wrong payments'],
        ['Task success, <b>fresh held-out set</b> (60+ unseen requests, frozen before tuning)', '80% or more with the free hosted model', 'Generated with Groq: 110 requests, all passed the wallet checks; under native-speaker review, then frozen and scored. (Old set: 39/64 blind, so it was retired.)'],
        ['Correct clarification on ambiguous requests; over-asking on clear ones', 'At least 90%; at most 10%', 'Reported per run in eval/report*.md'],
        ['Latency per request', 'Under 3 s; never a long wait', 'About 0.8 s with Groq (measured); after 3 s the rule parser answers'],
    ], [7.6 * cm, 4.3 * cm, W - 11.9 * cm]))
    s.append(Spacer(1, 2))
    s.append(P('Each case runs three times on a fresh database and passes only if all three pass. Fault injection covers a reply lost after the debit, a crash before commit, '
               'a biller outage and 50 concurrent retries; 264 automated tests run offline. Because the first held-out set was used to find fixes, a <b>new held-out set</b> '
               'has been generated with a stronger free model (110 requests); it is being hand-reviewed in a purpose-built review page and is frozen by commit before it is ever scored.', small))

    s.append(KeepTogether([P('5. What could go wrong, and what we do about it', h2), table([
        ['Risk', 'Mitigation'],
        [f'Ambiguity: two {ar("أحمد")}, "{ar("كهرباء")}" = grid or generator', 'Ask one question with masked phones or account numbers; never guess.'],
        ['LLM misreads, invents or drops a name or amount; prompt injection such as "send without confirmation"', 'Span and number checks reject it; confirmation is enforced in code, not in the prompt (OWASP LLM01).'],
        ['Network drops after the debit; double taps', 'Idempotency key per draft; (user, key) unique; the receipt says it was charged once.'],
        ['Free-tier rate limits or outage during a live demo', 'The app gives the model 3 s, then the rule parser answers; evaluation retries patiently; local model as offline backup; tell the organisers early.'],
        ['Weak Iraqi-dialect coverage in the test set', 'Native-speaker hand review; interview phrasing added as held-out cases.'],
        ['Scope creep', 'Cut order if late: voice, Arabizi, the two-request queue. Never cut: the card, questions, idempotency, held-out evaluation.'],
    ], [7.0 * cm, W - 7.0 * cm], fill=RISK)]))

    s.append(KeepTogether([P('6. Week-by-week plan to the MVP (08/11)', h2), table([
        ['Week', 'Deliverables', 'Done when'],
        ['17-22 Oct', '<b>Done:</b> this brief; repository pushed with full history; free Groq parser live (about 0.8 s per request, 3 s fallback budget)', 'Brief submitted; GitHub shows every commit'],
        ['23-29 Oct', '<b>Under way:</b> fresh held-out wallet + 110 requests generated and AI-checked; native-speaker review, freeze; 3-5 user interviews', 'Held-out file committed before any tuning; interview table filled'],
        ['30 Oct - 5 Nov', 'Evaluate the full system on the fresh held-out set (hosted, local, rules); fix only general issues on the dev set; demo hosting test', 'Results table with 0 wrong payments'],
        ['6-8 Nov', 'MVP: one-page update (works / not yet / next), rehearsed live demo including an unseen input', 'MVP submitted; session booked'],
    ], [2.3 * cm, 10.2 * cm, W - 12.5 * cm])]))
    s.append(Spacer(1, 4))
    s.append(P('Disclosure: built with Codex (initial code) and Claude Code; models and data sources are listed in DISCLOSURE.md. Synthetic data only; API keys stay in an '
               'untracked .env file. Sources: Global Findex 2025, Zain Annual Report 2025, Medhi et al. (low-literacy mobile banking), OWASP Top 10 for LLM applications.', small))
    doc.build(s)


if __name__ == '__main__':
    out = Path(__file__).with_name('DesignBrief_BillPayTransferAgent.pdf'); build(out); print('wrote', out)
