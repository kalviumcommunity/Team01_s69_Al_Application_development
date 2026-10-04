import base64, copy, http.cookiejar, json, os, tempfile, threading, unittest, urllib.error, urllib.request
import app
class ApiTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); app.DB=self.tmp.name+'/api.db'; app.init(); app.SESSIONS.clear()
  self.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler); self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start(); self.url='http://127.0.0.1:'+str(self.server.server_port)
  self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())); self.csrf=''
 def tearDown(self): self.server.shutdown(); self.server.server_close(); self.thread.join(); self.tmp.cleanup()
 def call(self,path,data=None,csrf=True):
  headers={'Content-Type':'application/json','X-CSRF-Token':self.csrf if csrf else 'bad'}
  req=urllib.request.Request(self.url+path,json.dumps(data).encode() if data is not None else None,headers)
  try:
   with self.opener.open(req) as r: return r.status,json.load(r)
  except urllib.error.HTTPError as e: return e.code,json.load(e)
 def login(self,lead=False):
  code,s=self.call('/api/login',{'username':'lead' if lead else 'tech','password':'demo-lead-2026' if lead else 'demo-tech-2026'}); self.assertEqual(code,200); self.csrf=s['csrf']
 def test_auth_and_roles(self):
  self.assertEqual(self.call('/api/documents')[0],401); self.assertEqual(self.call('/api/login',{'username':'tech','password':'wrong'})[0],401); self.login()
  self.assertEqual(self.call('/api/query',{'machine':'CV-100','question':'E101'},False)[0],403)
  self.assertEqual(self.call('/api/documents',{'document':{}})[0],403)
 def test_query_feedback_review(self):
  self.login(); code,a=self.call('/api/query',{'machine':'CV-100','question':'E101'}); self.assertEqual(code,200); self.assertEqual(a['state'],'answered')
  self.assertEqual(self.call('/api/feedback',{'query_id':a['query_id'],'label':'helpful'})[0],200)
  code,rs=self.call('/api/reviews'); self.assertEqual(len(rs['queries']),1); self.assertEqual(rs['queries'][0]['feedback'][0]['label'],'helpful')
 def test_replace_is_atomic_and_retires(self):
  self.login(True); docs=self.call('/api/documents')[1]['documents']; old=next(d for d in docs if d['type']=='manual' and d['machine']=='CV-100'); new=copy.deepcopy(old); new['approved']=True; new['revision']='3'; new['passages']=[{'locator':'Section 5','text':'E909 magnetic alignment: record visible fault and ask the maintenance lead.'}]
  self.assertEqual(self.call('/api/documents',{'document':new,'replace_id':old['id']})[0],201)
  ds=self.call('/api/documents')[1]['documents']; self.assertEqual(next(d for d in ds if d['id']==old['id'])['active'],0)
  a=self.call('/api/query',{'machine':'CV-100','question':'E101'})[1]; self.assertEqual(a['state'],'no_answer')
  self.assertEqual(self.call('/api/query',{'machine':'CV-100','question':'E909'})[1]['state'],'answered')
 def test_ingestion_rejections(self):
  self.login(True); d=json.loads((app.ROOT/'corpus.json').read_text())[0]; d['approved']=False
  self.assertEqual(self.call('/api/documents',{'document':d})[0],400)
  d['approved']=True; d['effective_date']='2999-01-01'; self.assertEqual(self.call('/api/documents',{'document':d})[0],400)
 def test_pdf_extraction(self):
  try: import pypdf
  except ImportError: self.skipTest('Install requirements.txt for PDF test')
  # Small text PDF created locally; exact page locator must survive extraction.
  stream=b'BT /F1 12 Tf 72 720 Td (E777 fictional inspection evidence for software tests only.) Tj ET'
  objs=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
  raw=b'%PDF-1.4\n'; offsets=[0]
  for i,obj in enumerate(objs,1): offsets.append(len(raw)); raw+=str(i).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
  xref=len(raw); raw+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(('%010d 00000 n \n'%o).encode() for o in offsets[1:])+b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF'
  self.login(True); code,r=self.call('/api/extract-pdf',{'base64':base64.b64encode(raw).decode()}); self.assertEqual(code,200); self.assertEqual(r['passages'][0]['locator'],'Page 1 / part 1'); self.assertIn('E777',r['passages'][0]['text'])
if __name__=='__main__': unittest.main(verbosity=2)
