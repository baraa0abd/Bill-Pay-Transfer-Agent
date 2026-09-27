# AI review — 2026-09-27

Codex reviewed all 68 development requests, their labels, and `agent/messages_ar.py`.
Each development item now includes a specific AI review note. No native-speaker
or other human approval is claimed. A human reviewer must add their own findings.

The requests cover recognizable Iraqi verbs and kinship names. The 50-IQD
transfer, Persian digits, diacritics and malformed numbers are boundary cases;
they should not be presented as evidence of common everyday phrasing. Bare
fifty, half, and ورقه remain intentionally ambiguous. Ahmed and electricity
must be disambiguated even when a request asks to skip confirmation.

The error messages distinguish known failure before debit from an unknown
payment result. IN_PROGRESS and STATUS_UNKNOWN correctly avoid claiming that
money was not debited. Conflict, forbidden and tampered messages refer to no
new payment rather than denying a possible earlier payment. Receipt wording
includes amount, fee, balance and reference. The recovered-response wording
explains a single debit. Colloquial forms لگينا, هسه, باچر and تكدر are internally
consistent; a native Iraqi reviewer still needs to verify regional preference,
readability, amount words and pronunciation. No speculative wording edits were
made solely to make the text look reviewed.

Remaining human work: read each request aloud, check whether the intended
meaning matches its label, revise unnatural phrases, and record actual reviewer
notes. Conduct 3–5 real interviews using PROBLEM.md; AI review cannot replace them.
