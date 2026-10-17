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
    except Exception as e: raise HTTPException(400, str(e))  # nothing was written


@app.get('/', response_class=HTMLResponse)
def page(): return PAGE


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Held-out review</title><style>
:root{--g:#174F43;--l:#D7ECAA;--t:#F1F5EE;--ink:#173E3B;--m:#5F6F6C;--r:#FBEBD8}
*{box-sizing:border-box}body{margin:0;font:14px/1.45 "Segoe UI",Arial,sans-serif;color:var(--ink);background:#fff}
header{position:sticky;top:0;z-index:2;background:#fff;border-bottom:1px solid #dfe5dc;padding:10px 18px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
h1{font-size:17px;margin:0;color:var(--g)}.bar{flex:1;height:8px;background:var(--t);border-radius:4px;min-width:120px}.bar i{display:block;height:100%;background:var(--g);border-radius:4px}
input,select,textarea,button{font:inherit}button{background:var(--g);color:#fff;border:0;border-radius:8px;padding:7px 16px;cursor:pointer}
main{display:grid;grid-template-columns:1fr 290px;gap:16px;padding:14px 18px}.card{border:1px solid #dfe5dc;border-radius:10px;padding:10px 12px;margin-bottom:10px}
.card.flag{border-color:#e0b27a;background:#fffaf3}.card.done{border-color:#9fc08a;background:#f8fbf4}
.top{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px}.id{font-weight:700;color:var(--g)}.cat{color:var(--m);font-size:12px}
textarea{width:100%;direction:rtl;text-align:right;font-size:17px;border:1px solid #cfd8cc;border-radius:8px;padding:6px 8px;resize:vertical}
.fields{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}.fields label{font-size:12px;color:var(--m);display:flex;flex-direction:column}
.fields input{width:92px}.note{font-size:12px;color:#8a5a12;margin-top:6px}aside{position:sticky;top:64px;align-self:start;max-height:calc(100vh - 80px);overflow:auto;font-size:13px}
aside table{border-collapse:collapse;width:100%}aside td{border-bottom:1px solid #eee;padding:2px 4px}.ar{direction:rtl;text-align:right}
#msg{font-weight:600}.err{color:#a02020}.ok{color:var(--g)}</style></head><body>
<header><h1>Held-out review</h1><label>Reviewer <input id="who" placeholder="your name" size="14"></label>
<label><input type="checkbox" id="flagged"> flagged / AI-corrected only</label>
<span id="count"></span><div class="bar"><i id="prog"></i></div><span id="msg"></span><button id="save">Save</button></header>
<main><div id="list"></div><aside id="wallet"></aside></main>
<script>
let D;const $=id=>document.getElementById(id);
const opt=(name,val)=>'<select data-k="'+name+'"><option value=""></option>'+D.choices[name].map(c=>'<option'+(c===val?' selected':'')+'>'+c+'</option>').join('')+'</select>';
const esc=s=>(s??'').toString().replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function render(){const only=$('flagged').checked;$('list').innerHTML=D.rows.map((r,i)=>{if(only&&!r.ai_note)return'';
 const cls=r.decision?'done':(r.ai_note?'flag':'');return '<div class="card '+cls+'" data-i="'+i+'"><div class="top"><span class="id">'+r.id+'</span><span class="cat">'+r.category+'</span>'+
 '<label>decision '+opt('decision',r.decision)+'</label></div><textarea rows="2" data-k="text">'+esc(r.text)+'</textarea><div class="fields">'+
 '<label>outcome'+opt('outcome',r.outcome)+'</label><label>ask slot'+opt('ask_slot',r.ask_slot)+'</label><label>refuse code'+opt('refuse_code',r.refuse_code)+'</label>'+
 ['payee_id','biller_id','amount_iqd','intent_types'].map(k=>'<label>'+k+'<input data-k="'+k+'" value="'+esc(r[k])+'"></label>').join('')+
 '<label style="flex:1">your note<input data-k="your_note" style="width:100%" value="'+esc(r.your_note)+'"></label></div>'+
 (r.ai_note?'<div class="note">AI: '+esc(r.ai_note)+'</div>':'')+'</div>'}).join('');progress()}
function progress(){const n=D.rows.filter(r=>r.decision).length;$('count').textContent=n+' / '+D.rows.length+' decided';$('prog').style.width=(100*n/D.rows.length)+'%'}
$('list').addEventListener('input',e=>{const card=e.target.closest('.card'),k=e.target.dataset.k;if(!card||!k)return;const r=D.rows[card.dataset.i];
 r[k]=e.target.value||null;if(k!=='decision'&&k!=='your_note'&&!r.decision){r.decision='edited';card.querySelector('[data-k=decision]').value='edited'}
 card.className='card '+(r.decision?'done':(r.ai_note?'flag':''));progress()});
$('flagged').onchange=render;
$('save').onclick=async()=>{const who=$('who').value.trim();if(!who){$('msg').className='err';$('msg').textContent='Enter your name first';return}
 D.rows.forEach(r=>{if(r.decision&&r.decision!=='delete')r.reviewer=who});
 const res=await fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(D.rows)});const j=await res.json();
 $('msg').className=res.ok?'ok':'err';$('msg').textContent=res.ok?j.message:'Not saved: '+j.detail};
fetch('/api/data').then(r=>r.json()).then(d=>{D=d;const w=d.wallet;
 $('wallet').innerHTML='<b>User 1 wallet</b><br>Balance '+w.balance_iqd.toLocaleString()+' IQD · fee '+w.fee_per_payment_iqd+'<br><br><b>Contacts</b><table>'+
 w.contacts.map(c=>'<tr><td>'+c.id+'</td><td class="ar">'+c.name+(c.nickname?' ('+c.nickname+')':'')+'</td></tr>').join('')+'</table><br><b>Billers</b><table>'+
 w.billers.map(b=>'<tr><td>'+b.biller_id+'</td><td class="ar">'+b.name+'</td><td>'+(b.unpaid_bills_iqd.join(', ')||'paid')+'</td></tr>').join('')+'</table>';render()});
</script></body></html>"""

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8010)
