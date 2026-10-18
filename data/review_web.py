"""Review the held-out set in the browser:  python -m data.review_web  ->  http://127.0.0.1:8010

Same rows and the same validation as the spreadsheet round trip (data/review.py); Save rewrites data/heldout.jsonl
only if every row is valid against the wallet. Local tool: binds to 127.0.0.1 only.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from .review import CHOICES, rows, save_rows, wallet

app = FastAPI(title='Held-out review')


@app.get('/api/data')
def data(): return {'rows': rows(), 'wallet': wallet(), 'choices': {k: v.split(',') for k, v in CHOICES.items()}}


@app.post('/api/save')
def save(edited: list[dict]):
    try: return {'message': save_rows(edited)}
    except Exception as e:  # nothing was written; show the reviewer one plain sentence, not a stack of validator output
        msg = str(e).split('Value error, ')[-1].split(' [type=')[0]
        raise HTTPException(400, msg.replace('labels inconsistent with EXECUTE_AFTER_CONFIRM', 'an "execute" needs a person or a bill, and an amount')
                                .replace('labels inconsistent with ASK', 'an "ask" needs what to ask about')
                                .replace('labels inconsistent with REFUSE', 'a "refuse" needs a reason'))


@app.get('/', response_class=HTMLResponse)
def page(): return PAGE


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Held-out review</title><style>
:root{--g:#174F43;--g2:#0f3a31;--l:#D7ECAA;--t:#F1F5EE;--ink:#173E3B;--m:#5F6F6C;--line:#dfe5dc;--warn:#9A5A12;--warnbg:#FFF4E5;--bad:#a02020}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 "Segoe UI",Arial,sans-serif;color:var(--ink);background:var(--t)}
button,select,input{font:inherit}button{cursor:pointer}
header{background:#fff;border-bottom:1px solid var(--line);padding:10px 16px;display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center}
h1{font-size:16px;margin:0;color:var(--g)}.chips{display:flex;gap:6px}.chip{border:1px solid var(--line);background:#fff;border-radius:99px;padding:4px 12px;font-size:13px;color:var(--ink)}
.chip.on{background:var(--g);border-color:var(--g);color:#fff}.prog{flex:1 1 220px;min-width:220px;display:flex;align-items:center;gap:8px;font-size:13px;color:var(--m)}
.bar{flex:1;height:8px;background:var(--t);border-radius:4px;overflow:hidden}.bar i{display:block;height:100%;background:var(--g);transition:width .2s}
.ghost{background:#fff;border:1px solid var(--line);border-radius:8px;padding:6px 12px;color:var(--ink)}
main{max-width:760px;margin:22px auto;padding:0 16px}
.card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:22px 24px;box-shadow:0 6px 24px #173e3b0d}
.meta{display:flex;justify-content:space-between;gap:8px;color:var(--m);font-size:13px}.badge{border-radius:99px;padding:2px 10px;font-size:12px;background:var(--t)}
.badge.done{background:var(--l);color:var(--g2)}.badge.flag{background:var(--warnbg);color:var(--warn)}
.text{direction:rtl;text-align:right;font-size:30px;line-height:1.5;margin:18px 0 8px;font-weight:600;word-break:break-word}
.text[contenteditable=true]{outline:2px solid var(--l);border-radius:8px;padding:4px 10px;background:#fbfdf8}
.expect{background:var(--t);border-radius:12px;padding:12px 16px;margin:14px 0}.expect small{display:block;color:var(--m);font-size:12px;margin-bottom:2px}
.expect b{font-size:18px}.name{direction:rtl;unicode-bidi:isolate}
.note{background:var(--warnbg);color:var(--warn);border-radius:10px;padding:10px 14px;font-size:14px;margin:10px 0}
.actions{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:18px}
.actions button{border:0;border-radius:12px;padding:14px 8px;font-size:16px;font-weight:600}
.ok{background:var(--g);color:#fff}.fix{background:#fff;color:var(--ink);border:1px solid var(--line)!important}.del{background:#fff;color:var(--bad);border:1px solid #f0d0d0!important}
kbd{font-size:11px;opacity:.7;border:1px solid currentColor;border-radius:4px;padding:0 4px;margin-left:6px;font-weight:400}
.nav{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:14px;color:var(--m);font-size:13px}
.edit{display:none;border-top:1px dashed var(--line);margin-top:16px;padding-top:14px}.edit.open{display:block}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}.grid label{display:flex;flex-direction:column;font-size:12px;color:var(--m);gap:3px}
.grid select,.grid input{border:1px solid var(--line);border-radius:8px;padding:7px 8px;color:var(--ink);background:#fff}
.seg{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}.seg button{border:1px solid var(--line);background:#fff;border-radius:99px;padding:5px 12px;font-size:13px}
.seg button.on{background:var(--g);color:#fff;border-color:var(--g)}
#toast{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);background:var(--ink);color:#fff;padding:9px 16px;border-radius:10px;font-size:14px;opacity:0;transition:opacity .2s;pointer-events:none;max-width:90vw}
#toast.show{opacity:1}#toast.err{background:var(--bad)}
aside{position:fixed;top:0;right:0;height:100%;width:min(360px,92vw);background:#fff;border-left:1px solid var(--line);box-shadow:-8px 0 30px #0002;transform:translateX(105%);transition:transform .2s;overflow:auto;padding:16px;z-index:5}
aside.open{transform:none}aside table{width:100%;border-collapse:collapse;font-size:13px}aside td{padding:3px 4px;border-bottom:1px solid #eef1ec}
td.name{text-align:right}dialog{border:0;border-radius:14px;padding:22px;box-shadow:0 10px 40px #0003;max-width:90vw}dialog input{border:1px solid var(--line);border-radius:8px;padding:8px;width:100%;margin:8px 0 12px}
.empty{text-align:center;color:var(--m);padding:40px}@media(max-width:520px){.text{font-size:24px}.actions button{font-size:14px}.nav span{display:none}}</style></head><body>
<header><h1>Held-out review</h1>
<div class="chips"><button class="chip" data-f="flagged">Flagged first</button><button class="chip" data-f="todo">Undecided</button><button class="chip" data-f="all">All</button></div>
<div class="prog"><span id="count"></span><div class="bar"><i id="prog"></i></div></div>
<button class="ghost" id="walletBtn">Wallet ▸</button><span id="who" class="badge"></span></header>
<main id="main"></main>
<aside id="wallet"></aside><div id="toast"></div>
<dialog id="nameDlg"><b>Who is reviewing?</b><p style="margin:6px 0 0;color:#5F6F6C;font-size:14px">Your name is saved with each decision as the native-speaker reviewer.</p>
<input id="nameIn" placeholder="Your name"><button class="ok" id="nameOk" style="border:0;border-radius:10px;padding:9px 16px">Start reviewing</button></dialog>
<script>
let D,view=[],pos=0,filter='flagged',editing=false,snap=null;const $=id=>document.getElementById(id);
const esc=s=>(s??'').toString().replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const num=n=>Number(n).toLocaleString('en-US');
let who='';try{who=localStorage.getItem('reviewer')||''}catch(e){}
const contact=id=>D.wallet.contacts.find(c=>c.id==id), biller=id=>D.wallet.billers.find(b=>b.biller_id==id);
const SLOT={payee:'which person?',biller:'which bill (e.g. grid or generator)?',amount:'how much?'};
const CODE={INSUFFICIENT_FUNDS:'not enough balance',UNKNOWN_PAYEE:'this person is not in the contacts',UNKNOWN_BILLER:'unknown biller',
 BILL_ALREADY_PAID:'the bill is already paid',AMOUNT_INVALID:'amount does not match the bill',UNSUPPORTED:'service not offered (loans, dollars…)',
 UNCLEAR:'cannot tell what the user wants',LIMIT_EXCEEDED:'over the daily limit'};
const NAME=s=>'<span class="name">'+esc(s)+'</span>';
function expect(r){
 if(r.outcome==='EXECUTE_AFTER_CONFIRM'){
  if(r.biller_id){const b=biller(r.biller_id);return (b&&b.category==='mobile_topup'?'Top up ':'Pay the bill ')+NAME(b?b.name:'#'+r.biller_id)+' · <b>'+num(r.amount_iqd)+' IQD</b>'}
  const c=contact(r.payee_id);return 'Send <b>'+num(r.amount_iqd)+' IQD</b> to '+NAME(c?c.name+(c.nickname?' ('+c.nickname+')':''):'#'+r.payee_id)}
 if(r.outcome==='ASK')return 'Should ask: <b>'+(SLOT[r.ask_slot]||'?')+'</b>';
 if(r.outcome==='REFUSE')return 'Should refuse: <b>'+(CODE[r.refuse_code]||r.refuse_code||'?')+'</b>';
 return 'Two requests in one message: <b>'+esc((r.intent_types||'').split(',').join(' + '))+'</b>'}
function build(){const rs=D.rows.map((r,i)=>i);
 view=filter==='all'?rs:filter==='todo'?rs.filter(i=>!D.rows[i].decision):rs.filter(i=>D.rows[i].ai_note).concat(rs.filter(i=>!D.rows[i].ai_note));
 if(pos>=view.length)pos=Math.max(0,view.length-1)}
function progress(){const n=D.rows.filter(r=>r.decision).length;$('count').textContent=n+' / '+D.rows.length+' reviewed';$('prog').style.width=(100*n/D.rows.length)+'%';
 document.querySelectorAll('.chip').forEach(c=>c.classList.toggle('on',c.dataset.f===filter));$('who').textContent=who?'Reviewer: '+who:''}
function options(list,val){return '<option value=""></option>'+list.map(x=>'<option value="'+x[0]+'"'+(x[0]==val?' selected':'')+'>'+esc(x[1])+'</option>').join('')}
function render(){progress();
 if(!view.length){$('main').innerHTML='<div class="card empty">Nothing left in this filter. Every request here is reviewed.</div>';return}
 const r=D.rows[view[pos]];
 const st=r.decision?'<span class="badge done">'+r.decision+'</span>':(r.ai_note?'<span class="badge flag">flagged</span>':'<span class="badge">to review</span>');
 const OUT={EXECUTE_AFTER_CONFIRM:'Execute',ASK:'Ask a question',REFUSE:'Refuse',SPLIT:'Two requests'};
 let fields='';
 if(r.outcome==='EXECUTE_AFTER_CONFIRM')fields='<label>Person<select data-k="payee_id">'+options(D.wallet.contacts.map(c=>[c.id,c.name+(c.nickname?' ('+c.nickname+')':'')]),r.payee_id)+'</select></label>'+
  '<label>or bill / top-up<select data-k="biller_id">'+options(D.wallet.billers.map(b=>[b.biller_id,b.name]),r.biller_id)+'</select></label>'+
  '<label>Amount (IQD)<input data-k="amount_iqd" type="number" value="'+esc(r.amount_iqd)+'"></label>';
 if(r.outcome==='ASK')fields='<label>Ask about<select data-k="ask_slot">'+options(Object.entries(SLOT),r.ask_slot)+'</select></label>';
 if(r.outcome==='REFUSE')fields='<label>Reason<select data-k="refuse_code">'+options(Object.entries(CODE),r.refuse_code)+'</select></label>';
 $('main').innerHTML='<div class="card"><div class="meta"><span>'+r.id+' · '+(pos+1)+' of '+view.length+'</span>'+st+'</div>'+
  '<div class="text" id="txt" dir="rtl" contenteditable="'+editing+'">'+esc(r.text)+'</div>'+
  '<div class="expect"><small>What the agent should do</small>'+expect(r)+'</div>'+(r.ai_note?'<div class="note">'+esc(r.ai_note)+'</div>':'')+
  '<div class="actions"><button class="ok" id="bKeep">✓ Correct<kbd>K</kbd></button><button class="fix" id="bFix">✎ Fix<kbd>E</kbd></button><button class="del" id="bDel">✕ Remove<kbd>D</kbd></button></div>'+
  '<div class="edit'+(editing?' open':'')+'"><div class="seg">'+Object.keys(OUT).map(o=>'<button data-o="'+o+'" class="'+(r.outcome===o?'on':'')+'">'+OUT[o]+'</button>').join('')+
  '</div><div class="grid">'+fields+'<label>Note (optional)<input data-k="your_note" value="'+esc(r.your_note)+'"></label></div>'+
  '<div class="actions" style="grid-template-columns:1fr"><button class="ok" id="bSave">Save fix and next<kbd>Enter</kbd></button></div></div>'+
  '<div class="nav"><button class="ghost" id="bPrev">← Previous</button><span>After ✎ Fix you can edit the Arabic text directly</span><button class="ghost" id="bNext">Next →</button></div></div>';
 $('bKeep').onclick=()=>decide('keep');$('bDel').onclick=()=>decide('delete');
 $('bFix').onclick=()=>{if(editing){cancelEdit();render();return}snap=JSON.stringify(r);editing=true;render();$('txt').focus()};
 $('bPrev').onclick=()=>{cancelEdit();pos=Math.max(0,pos-1);render()};
 $('bNext').onclick=()=>{cancelEdit();pos=Math.min(view.length-1,pos+1);render()};
 if($('bSave'))$('bSave').onclick=()=>decide('edited');
 document.querySelectorAll('.seg button').forEach(b=>b.onclick=()=>{r.text=$('txt').innerText.trim();r.outcome=b.dataset.o;render()});
 document.querySelectorAll('.edit [data-k]').forEach(el=>el.onchange=()=>{const k=el.dataset.k;r.text=$('txt').innerText.trim();r[k]=el.value||null;
  if(k==='payee_id'&&el.value)r.biller_id=null;if(k==='biller_id'&&el.value)r.payee_id=null;if(k!=='your_note')render()})}
function cancelEdit(){if(editing&&snap)Object.assign(D.rows[view[pos]],JSON.parse(snap));editing=false;snap=null}
function intents(r){if(r.outcome!=='EXECUTE_AFTER_CONFIRM')return r.intent_types;const b=r.biller_id&&biller(r.biller_id);
 return r.payee_id?'transfer':(b&&b.category==='mobile_topup'?'topup':'bill_payment')}
async function decide(d){if(!who){$('nameDlg').showModal();return}
 const r=D.rows[view[pos]],before=JSON.stringify(r);
 if(editing)r.text=$('txt').innerText.trim();r.intent_types=intents(r);r.decision=d;
 D.rows.forEach(x=>{if(x.decision&&x.decision!=='delete')x.reviewer=who});
 const res=await fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(D.rows)});
 if(!res.ok){Object.assign(r,JSON.parse(before));toast('Not saved: '+(await res.json()).detail,true);return}
 toast(d==='delete'?'Removed':'Saved');editing=false;snap=null;
 const cur=view[pos];build();const at=view.indexOf(cur);pos=at>=0?Math.min(at+1,view.length-1):Math.min(pos,view.length-1);render()}
function toast(m,err){const t=$('toast');t.textContent=m;t.className='show'+(err?' err':'');clearTimeout(t._h);t._h=setTimeout(()=>t.className='',err?5000:1200)}
document.addEventListener('keydown',e=>{
 if($('nameDlg').open)return;
 if(e.target.isContentEditable||/INPUT|SELECT/.test(e.target.tagName)){if(e.key==='Enter'&&editing&&!e.shiftKey){e.preventDefault();decide('edited')}return}
 const k=e.key.toLowerCase();
 if(k==='k')decide('keep');else if(k==='d')decide('delete');else if(k==='e')$('bFix')&&$('bFix').click();
 else if(e.key==='ArrowRight')$('bNext')&&$('bNext').click();else if(e.key==='ArrowLeft')$('bPrev')&&$('bPrev').click();
 else if(e.key==='Enter'&&editing)decide('edited')});
document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{cancelEdit();filter=c.dataset.f;pos=0;build();render()});
$('walletBtn').onclick=()=>$('wallet').classList.toggle('open');
$('nameOk').onclick=()=>{who=$('nameIn').value.trim();if(!who)return;try{localStorage.setItem('reviewer',who)}catch(e){}$('nameDlg').close();progress()};
fetch('/api/data').then(r=>r.json()).then(d=>{D=d;const w=d.wallet;
 $('wallet').innerHTML='<div style="display:flex;justify-content:space-between;align-items:center"><b>User 1 wallet</b><button class="ghost" id="wClose">✕</button></div>'+
  '<p>Balance <b>'+num(w.balance_iqd)+' IQD</b> · fee '+w.fee_per_payment_iqd+' IQD per payment</p><b>Contacts</b><table>'+
  w.contacts.map(c=>'<tr><td class="name">'+esc(c.name)+(c.nickname?' ('+esc(c.nickname)+')':'')+'</td></tr>').join('')+'</table><p></p><b>Bills</b><table>'+
  w.billers.map(b=>'<tr><td class="name">'+esc(b.name)+'</td><td>'+(b.unpaid_bills_iqd.length?num(b.unpaid_bills_iqd[0])+' unpaid':'paid')+'</td></tr>').join('')+'</table>';
 $('wClose').onclick=()=>$('wallet').classList.remove('open');
 build();render();if(!who)$('nameDlg').showModal()});
</script></body></html>"""

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8010)
