import copy
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
from core import make_state
from traceability import sync
from phase2 import review_extraction_phase2, import_classification, verify_income
from phase3 import template
from gemini_service import run_task, chat, GeminiError

def state(cid='HS01'):
    folder=ROOT/'runtime/cases'/cid
    m=json.loads((folder/'manifest.json').read_text())
    files={d['source_type']:(folder/d['path']).read_bytes() for d in m['documents'] if d['available']}
    coverage=next(d for d in m['documents'] if d['source_type']=='bank_statement')
    s=make_state(cid,files,coverage if coverage['available'] else None);sync(s);return s

class FakeClient:
    model='TEST-MOCK-NOT-A-LIVE-MODEL'
    def __init__(self,result):self.result=result;self.calls=0
    def generate(self,prompt):
        self.calls+=1
        if isinstance(self.result,Exception):raise self.result
        return copy.deepcopy(self.result), {'model':self.model,'usage':{'total_token_count':0},'mock':True}

def reviewed():
    s=state()
    review_extraction_phase2(s,{'expected_version':s['version'],'reviewer':'TEST','reason':'Fixture only','checked':True})
    return s

class GeminiWorkflowTests(unittest.TestCase):
    def test_extraction_uses_validator_and_no_auto_review(self):
        s=state();before=copy.deepcopy(s)
        obj={'case_id':'HS01','documents':[{'document_id':d['document_id'],'fields':d['fields']} for d in s['case']['documents'] if d['available'] and d['source_type']!='bank_statement']}
        out=run_task(s,'extraction',FakeClient(obj))
        self.assertEqual(s,before)
        self.assertEqual(out['mode'],'API_DIRECT')
        self.assertEqual(out['extraction_review']['status'],'Pending')
        self.assertEqual(out['llm_runs'][-1]['provenance'],'server_gemini_api')

    def test_wrong_case_keeps_state(self):
        s=state();before=copy.deepcopy(s)
        with self.assertRaises(ValueError):run_task(s,'extraction',FakeClient({'case_id':'WRONG','documents':[]}))
        self.assertEqual(s,before)

    def test_classification_precondition_prevents_call(self):
        c=FakeClient({})
        with self.assertRaises(ValueError):run_task(state(),'classification',c)
        self.assertEqual(c.calls,0)

    def test_classification_requires_human_income_review(self):
        s=reviewed();obj=json.loads((ROOT/'incoming/HS01_classification.json').read_text())
        out=run_task(s,'classification',FakeClient(obj))
        self.assertIsNone(out['phase2']['income_review'])
        self.assertTrue(all(x is None for x in out['phase2']['metrics'].values()))
        self.assertEqual(out['phase2']['classification']['provenance'],'server_gemini_api')

    def test_api_failure_is_transactional(self):
        s=reviewed();before=copy.deepcopy(s)
        with self.assertRaises(GeminiError):run_task(s,'summary',FakeClient(GeminiError('mock quota')))
        self.assertEqual(s,before)

    def test_summary_numbers_are_locked(self):
        s=json.loads((ROOT/'seed/HS01_session.json').read_text());sync(s)
        obj=template(s);obj['metrics']['dti_pct']=999
        before=copy.deepcopy(s)
        with self.assertRaises(ValueError):run_task(s,'summary',FakeClient(obj))
        self.assertEqual(s,before)

    def test_summary_real_validator_sets_draft_only(self):
        s=json.loads((ROOT/'seed/HS01_session.json').read_text());sync(s)
        obj=template(s)
        for section in ('overview','metric_explanations','limitations','verification_questions'):
            obj[section]=[{'text':'Diễn giải thử nghiệm có nguồn để kiểm tra.', 'refs':['METRICS' if section=='metric_explanations' else 'CASE']}]
        out=run_task(s,'summary',FakeClient(obj))
        self.assertEqual(out['phase3']['report_status'],'Human review required')
        self.assertIsNone(out['phase3']['content_review'])
        self.assertEqual(out['phase3']['summary']['mode'],'API_DIRECT')

    def test_chat_is_read_only(self):
        s=state();before=copy.deepcopy(s)
        out=chat(s,'Cần kiểm tra gì?',[],FakeClient({'answer':[{'text':'Cần kiểm tra thông tin hồ sơ.', 'refs':['CASE']}]}))
        self.assertEqual(s,before)
        self.assertIn('CASE',out['references'])

    def test_chat_rejects_fabricated_refs(self):
        with self.assertRaises(ValueError):chat(state(),'x',[],FakeClient({'answer':[{'text':'Không có nguồn này','refs':['BOGUS']}]}))

    def test_chat_rejects_decision_language(self):
        with self.assertRaises(ValueError):chat(state(),'x',[],FakeClient({'answer':[{'text':'Đề xuất duyệt khoản vay','refs':['CASE']}]}))

    def test_chat_question_length_limit(self):
        c=FakeClient({})
        with self.assertRaises(ValueError):chat(state(),'x'*2001,[],c)
        self.assertEqual(c.calls,0)

    def test_two_states_are_independent(self):
        a,b=state('HS01'),state('HS05')
        original=copy.deepcopy(b)
        a['case']['case_id']='MODIFIED'
        self.assertEqual(b,original)

if __name__=='__main__':unittest.main()
