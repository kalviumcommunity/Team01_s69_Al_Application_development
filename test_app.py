import copy, json, os, tempfile, unittest
import app
class RetrievalTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); app.DB=self.tmp.name+'/test.db'; app.init(); self.c=app.conn()
 def tearDown(self): self.c.close(); self.tmp.cleanup()
 def test_twenty_queries(self):
  cases=[('CV-100','E101 belt not moving','answered'),('CV-100','conveyor will not start','answered'),('CV-100','E202 vibration','answered'),('CV-100','conveyor rattling','answered'),('CV-100','E303 overheating','answered'),('CV-100','high temperature','answered'),('CV-100','E404 sensor blocked','answered'),('CV-100','optical sensor alarm','answered'),('P-200','P10 low pressure','answered'),('P-200','pump no flow','answered'),('CV-100','smoke and sparks','safety'),('CV-100','burning smell','safety'),('CV-100','bypass interlock','safety'),('CV-100','electric shock','safety'),('CV-100','exposed wiring','safety'),('CV-100','quantum calibration','no_answer'),('CV-100','unicorn propulsion','no_answer'),('UNKNOWN','E101','no_answer'),('P-200','E101 belt not moving','no_answer'),('P-200','unicorn fault','no_answer')]
  for machine,q,state in cases:
   with self.subTest(q=q):
    a=app.answer(self.c,machine,q); self.assertEqual(a['state'],state)
    for p in a['checks']+a['safety']+a['history']:
     row=self.c.execute('SELECT text FROM passages WHERE id=?',(p['id'],)).fetchone(); self.assertEqual(row['text'],p['text'])
 def test_reject_unapproved(self):
  d=copy.deepcopy(app.json.loads((app.ROOT/'corpus.json').read_text())[0]); d['approved']=False
  with self.assertRaises(ValueError): app.insert(self.c,d)
 def test_reject_missing_locator(self):
  d=copy.deepcopy(json.loads((app.ROOT/'corpus.json').read_text())[0]); d['passages'][0]['locator']=''
  with self.assertRaises(ValueError): app.insert(self.c,d)
 def test_conflict(self):
  d=copy.deepcopy(json.loads((app.ROOT/'corpus.json').read_text())[0]); d['conflict_key']='restart'; d['conflict_value']='A'; app.insert(self.c,d); d['conflict_value']='B'; app.insert(self.c,d)
  a=app.answer(self.c,'CV-100','E101'); self.assertEqual(a['state'],'conflict'); self.assertEqual(a['checks'],[])
 def test_retire(self):
  ids=[r['id'] for r in self.c.execute("SELECT id FROM documents WHERE type='manual' AND machine='CV-100'")]; self.c.execute("UPDATE documents SET active=0 WHERE type='manual' AND machine='CV-100'")
  a=app.answer(self.c,'CV-100','E101'); self.assertEqual(a['state'],'no_answer'); self.assertFalse(any(p['document_id'] in ids for p in a['retrieval']))
 def test_safety_required(self):
  self.c.execute("UPDATE documents SET active=0 WHERE type='safety'"); self.assertEqual(app.answer(self.c,'CV-100','E101')['state'],'no_answer')
if __name__=='__main__': unittest.main(verbosity=2)
