#!/usr/bin/env python3
"""FieldGuide: source-backed local troubleshooting. Python 3.10+."""
import collections, datetime, hashlib, http.cookies, json, math, os, pathlib, re, secrets, sqlite3, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
ROOT=pathlib.Path(__file__).parent
DB=os.environ.get('FIELDGUIDE_DB',str(ROOT/'fieldguide.db'))
LOCK=threading.RLock(); SESSIONS={}
STOP=set('a an the is are was were to of in on for and or with how what why i it my this that does do can please has have at by from as when'.split())
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def tokens(s): return [w for w in re.findall(r'[a-z0-9]+',s.lower()) if w not in STOP and len(w)>1]
def conn():
 c=sqlite3.connect(DB,timeout=10); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def validate(d):
 for f in ['title','type','machine','revision','effective_date','owner']:
  if not isinstance(d.get(f),str) or not d[f].strip() or len(d[f])>200: raise ValueError('Missing or invalid '+f)
 if d['type'] not in ['manual','log','safety']: raise ValueError('Invalid document type')
 if datetime.date.fromisoformat(d['effective_date'])>datetime.date.today(): raise ValueError('Future-effective document')
 if d.get('approved') is not True: raise ValueError('Only approved documents can enter the corpus')
 ps=d.get('passages')
 if not isinstance(ps,list) or not 1<=len(ps)<=300: raise ValueError('Provide 1-300 passages')
 for p in ps:
  if not isinstance(p,dict) or not isinstance(p.get('text'),str) or not 10<=len(p['text'].strip())<=20000 or not isinstance(p.get('locator'),str) or not p['locator'].strip() or len(p['locator'])>200: raise ValueError('Each passage needs text and page/section locator')
 if sum(len(p['text']) for p in ps)>500000: raise ValueError('Text exceeds 500 KB')
 if bool(d.get('conflict_key'))!=bool(d.get('conflict_value')): raise ValueError('Provide both conflict key and value')
 for f in ['conflict_key','conflict_value']:
  if d.get(f) and (not isinstance(d[f],str) or len(d[f])>200): raise ValueError('Invalid conflict metadata')
def insert(c,d):
 validate(d); did=secrets.token_hex(12)
 c.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(did,d['title'],d['type'],d['machine'],d['revision'],d['effective_date'],d['owner'],1,1,d.get('conflict_key'),d.get('conflict_value'),now()))
 for i,p in enumerate(d['passages']): c.execute('INSERT INTO passages VALUES(?,?,?,?)',(did+'-'+str(i),did,p['locator'],p['text'].strip()))
 return did

def init():
 with conn() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,title TEXT,type TEXT,machine TEXT,revision TEXT,effective_date TEXT,owner TEXT,approved INTEGER,active INTEGER,conflict_key TEXT,conflict_value TEXT,created_at TEXT);
CREATE TABLE IF NOT EXISTS passages(id TEXT PRIMARY KEY,document_id TEXT REFERENCES documents(id),locator TEXT,text TEXT);
CREATE TABLE IF NOT EXISTS queries(id TEXT PRIMARY KEY,machine TEXT,question TEXT,result TEXT,created_at TEXT,username TEXT);
CREATE TABLE IF NOT EXISTS feedback(id TEXT PRIMARY KEY,query_id TEXT REFERENCES queries(id),label TEXT,note TEXT,created_at TEXT,username TEXT);
CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY,role TEXT,salt TEXT,password_hash TEXT);''')
  for name,role,pwd in [('tech','technician',os.environ.get('FIELDGUIDE_TECH_PASSWORD','demo-tech-2026')),('lead','maintainer',os.environ.get('FIELDGUIDE_ADMIN_PASSWORD','demo-lead-2026'))]:
   if not c.execute('SELECT 1 FROM users WHERE username=?',(name,)).fetchone():
    salt=secrets.token_hex(16); c.execute('INSERT INTO users VALUES(?,?,?,?)',(name,role,salt,hashlib.pbkdf2_hmac('sha256',pwd.encode(),salt.encode(),200000).hex()))
  if not c.execute('SELECT 1 FROM documents LIMIT 1').fetchone():
   for d in json.loads((ROOT/'corpus.json').read_text()): insert(c,d)

def answer(c,machine,question):
 rows=[dict(r) for r in c.execute('SELECT p.*,d.title,d.type,d.machine,d.revision,d.conflict_key,d.conflict_value FROM passages p JOIN documents d ON p.document_id=d.id WHERE d.active=1 AND d.approved=1 AND d.machine=?',(machine,))]
 q=set(tokens(question))-set(tokens(machine)) - {'fault','error','code','problem','issue','machine','equipment','conveyor','pump','unit'}; df=collections.Counter()
 for r in rows: df.update(set(tokens(r['text'])))
 ranked=[]
 for r in rows:
  ws=tokens(r['text']); counts=collections.Counter(ws)
  score=sum((1+math.log(counts[t]))*math.log(1+(len(rows)+1)/(df[t]+1)) for t in q if t in counts)/math.sqrt(max(len(ws),1))
  for code in re.findall(r'\b(?:e\d{3}|p\d{2})\b',question.lower()):
   if code in ws: score+=2
  r['score']=round(score,4)
  if score>0: ranked.append(r)
 ranked.sort(key=lambda r:r['score'],reverse=True)
 safety=[r for r in rows if r['type']=='safety']; manuals=[r for r in ranked if r['type']=='manual' and r['score']>=.15 and len(q & set(tokens(r['text'])))/max(len(q),1)>=.5]
 codes=set(re.findall(r'\b(?:e\d{3}|p\d{2})\b',question.lower()))
 if codes: manuals=[r for r in manuals if codes & set(tokens(r['text']))]
 vals=collections.defaultdict(set)
 for r in rows:
  if r['conflict_key']: vals[r['conflict_key']].add(r['conflict_value'])
 state='answered'; reason='Relevant approved passages found. Verify the original before acting.'
 if not rows: state='no_answer'; reason='No approved active sources for this machine. Escalate to maintenance lead.'
 elif any(len(v)>1 for v in vals.values()): state='conflict'; reason='Tagged instructions conflict. No checks shown. Ask the lead to resolve the sources.'
 elif re.search(r'\b(smoke|sparks?|fire|burning|shock|exposed|bypass|interlocks?|guards?)\b',question,re.I): state='safety'; reason='Possible hazard or bypass request. Stop troubleshooting and follow the site safety process.'
 elif not safety: state='no_answer'; reason='No active safety procedure. Escalate rather than suggesting checks.'
 elif not manuals: state='no_answer'; reason='Insufficient matching manual evidence. No invented fix. Escalate to the maintenance lead.'
 return dict(state=state,reason=reason,machine=machine,question=question,safety=safety,checks=manuals[:3] if state=='answered' else [],history=[r for r in ranked if r['type']=='log' and (codes & set(tokens(r['text'])) if codes else len(q & set(tokens(r['text'])))/max(len(q),1)>=.5)][:2] if state=='answered' else [],retrieval=ranked[:3],mode='Local TF-IDF ranking + verbatim evidence (no LLM)',created_at=now())

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a): pass
 def respond(self,data,status=200,mime='application/json',cookie=None):
  if not isinstance(data,bytes): data=json.dumps(data).encode()
  self.send_response(status); self.send_header('Content-Type',mime+'; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('X-Frame-Options','DENY'); self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
  if cookie: self.send_header('Set-Cookie',cookie)
  self.end_headers(); self.wfile.write(data)
 def session(self):
  try:
   cookie=http.cookies.SimpleCookie(self.headers.get('Cookie','')); k=cookie.get('fieldguide'); s=SESSIONS.get(k.value if k else '')
   return s if s and s['expires']>time.time() else None
  except http.cookies.CookieError: return None
 def do_GET(self):
  path=self.path.split('?')[0]
  if path=='/': return self.respond((ROOT/'index.html').read_bytes(),mime='text/html')
  if path=='/health': return self.respond({'status':'ok'})
  s=self.session()
  if not s: return self.respond({'error':'Sign in required'},401)
  with conn() as c:
   if path=='/api/session': return self.respond({k:s[k] for k in ['username','role','csrf']})
   if path=='/api/documents':
    docs=[dict(r) for r in c.execute('SELECT * FROM documents ORDER BY created_at DESC')]
    for d in docs: d['passages']=[dict(r) for r in c.execute('SELECT * FROM passages WHERE document_id=?',(d['id'],))]
    return self.respond({'documents':docs})
   if path=='/api/reviews':
    sql='SELECT * FROM queries'+('' if s['role']=='maintainer' else ' WHERE username=?')+' ORDER BY created_at DESC LIMIT 100'
    rs=[dict(r) for r in c.execute(sql,() if s['role']=='maintainer' else (s['username'],))]
    for r in rs: r['result']=json.loads(r['result']); r['feedback']=[dict(f) for f in c.execute('SELECT * FROM feedback WHERE query_id=?',(r['id'],))]
    return self.respond({'queries':rs})
  return self.respond({'error':'Not found'},404)
 def do_POST(self):
  try:
   origin=self.headers.get('Origin')
   if origin and origin.split('://',1)[-1]!=self.headers.get('Host'): return self.respond({'error':'Cross-origin request blocked'},403)
   n=int(self.headers.get('Content-Length','0'))
   if not 0<n<=2000000: raise ValueError('Invalid payload length (max 2 MB)')
   data=json.loads(self.rfile.read(n)); path=self.path.split('?')[0]
   if path=='/api/login':
    with conn() as c: row=c.execute('SELECT * FROM users WHERE username=?',(data.get('username'),)).fetchone()
    pwd=data.get('password','')
    if not row or not isinstance(pwd,str) or not secrets.compare_digest(hashlib.pbkdf2_hmac('sha256',pwd.encode(),row['salt'].encode(),200000).hex(),row['password_hash']): return self.respond({'error':'Invalid credentials'},401)
    key=secrets.token_urlsafe(32); s=dict(username=row['username'],role=row['role'],csrf=secrets.token_urlsafe(24),expires=time.time()+28800); SESSIONS[key]=s
    return self.respond({k:s[k] for k in ['username','role','csrf']},cookie='fieldguide='+key+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800')
   s=self.session()
   if not s: return self.respond({'error':'Sign in required'},401)
   if not secrets.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']): return self.respond({'error':'Invalid CSRF token'},403)
   if path=='/api/logout':
    for k,v in list(SESSIONS.items()):
     if v is s: del SESSIONS[k]
    return self.respond({},cookie='fieldguide=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
   with LOCK,conn() as c:
    if path=='/api/query':
     machine=data.get('machine',''); question=data.get('question','')
     if not isinstance(question,str) or not 3<=len(question.strip())<=1500 or not isinstance(machine,str) or not 1<=len(machine)<=200: raise ValueError('Select machine and enter 3-1500 character question')
     result=answer(c,machine,question.strip()); qid=secrets.token_hex(12); result['query_id']=qid
     c.execute('INSERT INTO queries VALUES(?,?,?,?,?,?)',(qid,machine,question.strip(),json.dumps(result),now(),s['username']))
     return self.respond(result)
    if path=='/api/feedback':
     qid=data.get('query_id'); label=data.get('label'); note=data.get('note','')
     if label not in ['helpful','unsafe','not_helpful'] or not isinstance(note,str) or len(note)>1000: raise ValueError('Invalid feedback')
     q=c.execute('SELECT username FROM queries WHERE id=?',(qid,)).fetchone()
     if not q or (s['role']!='maintainer' and q['username']!=s['username']): return self.respond({'error':'Query not found'},404)
     c.execute('INSERT INTO feedback VALUES(?,?,?,?,?,?)',(secrets.token_hex(12),qid,label,note,now(),s['username'])); return self.respond({'saved':True})
    if s['role']!='maintainer': return self.respond({'error':'Maintainer role required'},403)
    if path=='/api/documents':
     d=data.get('document',{}); replace=data.get('replace_id')
     if replace:
      old=c.execute('SELECT * FROM documents WHERE id=? AND active=1',(replace,)).fetchone()
      if not old or old['machine']!=d.get('machine') or old['type']!=d.get('type'): raise ValueError('Replacement must match active machine and document type')
     did=insert(c,d)
     if replace: c.execute('UPDATE documents SET active=0 WHERE id=?',(replace,))
     return self.respond({'id':did},201)
    if path=='/api/retire':
     r=c.execute('UPDATE documents SET active=0 WHERE id=? AND active=1',(data.get('id'),))
     if not r.rowcount: raise ValueError('Active source not found')
     return self.respond({'retired':True})
    if path=='/api/extract-pdf':
     import base64,io
     try: from pypdf import PdfReader
     except ImportError: return self.respond({'error':'PDF import needs: pip install -r requirements.txt. Text import works without it.'},422)
     raw=base64.b64decode(data.get('base64',''),validate=True)
     if len(raw)>1000000: raise ValueError('PDF exceeds 1 MB limit')
     reader=PdfReader(io.BytesIO(raw))
     if reader.is_encrypted or len(reader.pages)>100: raise ValueError('Use unencrypted PDF, max 100 pages')
     ps=[]
     for i,page in enumerate(reader.pages):
      text=(page.extract_text() or '').strip()
      for n in range(0,len(text),4000):
       part=text[n:n+4000].strip()
       if len(part)>=10: ps.append({'locator':'Page '+str(i+1)+' / part '+str(n//4000+1),'text':part})
     if not ps: raise ValueError('No text extracted. Scanned PDFs need OCR (not included).')
     return self.respond({'passages':ps})
   return self.respond({'error':'Not found'},404)
  except (ValueError,TypeError,KeyError) as e: self.respond({'error':str(e)},400)
  except Exception: self.respond({'error':'Request could not be processed. Check source format.'},500)
def main():
 import argparse
 p=argparse.ArgumentParser(); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',type=int,default=int(os.environ.get('PORT','8080'))); a=p.parse_args()
 if a.host not in ['127.0.0.1','localhost','::1'] and not (os.environ.get('FIELDGUIDE_ADMIN_PASSWORD') and os.environ.get('FIELDGUIDE_TECH_PASSWORD')): raise SystemExit('Public binding requires both password environment variables. Demo credentials are loopback-only.')
 init(); server=ThreadingHTTPServer((a.host,a.port),Handler); print('FieldGuide ready at http://'+a.host+':'+str(a.port),flush=True)
 try: server.serve_forever()
 except KeyboardInterrupt: pass
 finally: server.server_close()
if __name__=='__main__': main()
