# Problem and users

## Who and what

People who are not comfortable with smartphones (older relatives, people who read little, people who rely on family to "do the app for them") abandon wallet flows or mis-tap them. One sentence, typed or spoken in Iraqi dialect, should be enough, with a confirmation they can read before anything moves.

## Evidence: conversations with real people

> Fill this in from real conversations only. Leave rows empty rather than inventing them.

| # | Date | Age range | Smartphone comfort (1–5) | How they pay bills / send money today | What goes wrong | Their exact words for "pay electricity" / "send money" | Tried the demo? What happened |
|---|---|---|---|---|---|---|---|
| 1 | | | | | | | |
| 2 | | | | | | | |
| 3 | | | | | | | |
| 4 | | | | | | | |
| 5 | | | | | | | |

### What we changed because of it

- _(one line per change, e.g. "confirmation card font enlarged after #2 couldn't read the amount")_

## How to run a conversation (15 minutes)

**Privacy:** no names, phone numbers, account numbers or real balances. Record age range only. Ask before writing anything down. Nothing they say goes into the repo except their phrasing, anonymised.

1. **Today** (5 min)
   - شلون تدفع فاتورة الكهرباء أو المولدة هسه؟ — How do you pay electricity or the generator now?
   - شلون تدز فلوس لأحد من أهلك؟ — How do you send money to family?
   - صار وياك مرة غلط، أو تركت العملية بالنص؟ شنو صار؟ — Ever made a mistake or given up halfway? What happened?
   - منو يساعدك بالتطبيق؟ — Who helps you with the app?
2. **Their words** (3 min). Don't prompt with our phrasing.
   - لو تكدر تكتب أو تحچي جملة وحدة للتطبيق حتى يدفع الكهرباء، شنو تكول؟ — If you could say one sentence to the app to pay electricity, what would you say?
   - ونفس الشي حتى تدز خمسين ألف لواحد من أهلك؟ — And to send 50,000 to a relative?
   - Write their sentences down exactly as they said them, spelling mistakes included.
3. **Try it** (5 min). Run `./make.ps1 run` on your laptop. It is a mock wallet, so no real money moves. Hand it over and give one task at a time, without helping:
   - Pay the electricity bill.
   - Send money to Ahmed. There are several Ahmeds, so watch what they do with the question.
   - On the confirmation card: can they read the amount and the recipient? Do they know which button to press?
4. **Close** (2 min)
   - تستخدمه لو صار بالتطبيق الحقيقي؟ ليش لا؟ — Would you use this in the real app? Why not?

## What to do with the results

- Fill in the table and the "what we changed" list above.
- Each of their sentences is a realistic test case. Add them to `data/heldout.jsonl` with ids `interview-001` onward and `review_status: "real_user_phrasing"`, labelled against user 1 in `data/heldout_seed.json` (swap a name for a contact that exists there). The parser was never tuned on them, so they stay held-out even if added after the freeze. Do **not** change the parser to make them pass.
- Put one or two quotes in the demo's opening. "Problem and impact" is 20% of the score, and a real quote is the evidence judges look for.
