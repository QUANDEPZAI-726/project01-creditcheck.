import copy, io, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from core import make_state, baseline, read_csv, assisted_prompt, edit_field, import_assisted, review_extraction, refresh
from sample_data import load_sample
class CoreTests(unittest.TestCase):
    def setUp(self):self.s=load_sample('HS01')
    def import_body(self,s=None):
        s=s or self.s
        return {'expected_version':s['version'],'model':'Test fixture (not a real LLM)','attest':True,
          'result':{'case_id':s['case']['case_id'],'documents':[{'document_id':d['document_id'],'fields':copy.deepcopy(d['fields'])} for d in s['case']['documents'] if d['available'] and d['source_type']!='bank_statement']}}
    def test_happy_baseline(self):
        self.assertEqual(self.s['mode'],'RULE_BASELINE');self.assertEqual(self.s['case']['documents'][0]['fields']['net_monthly_income_vnd']['value'],20000000)
        self.assertEqual(len(self.s['case']['transactions']),9);self.assertFalse(self.s['issues']);self.assertEqual(self.s['llm_runs'],[])
    def test_all_five(self):
        for cid in ['HS01','HS02','HS03','HS04','HS05']:self.assertEqual(load_sample(cid)['case']['case_id'],cid)
    def test_missing_statement(self):
        s=load_sample('HS02');self.assertEqual(s['case']['review']['data_status'],'Insufficient information');self.assertEqual(s['case']['transactions'],[])
    def test_income_mismatch(self):self.assertIn('INCOME_MISMATCH',[i['code'] for i in load_sample('HS03')['issues']])
    def test_identity_mismatch(self):self.assertIn('BORROWER_ID_MISMATCH',[i['code'] for i in load_sample('HS04')['issues']])
    def test_no_auto_classification(self):self.assertTrue(all(t['llm_label'] is None for t in load_sample('HS05')['case']['transactions']))
    def test_review_is_limited(self):
        review_extraction(self.s,{'expected_version':1,'checked':True,'reviewer':'A','reason':'Checked source'})
        self.assertEqual(self.s['extraction_review']['status'],'Reviewed');self.assertEqual(self.s['case']['review']['data_status'],'Human review required');self.assertFalse(self.s['extraction_review']['identity_verified'])
    def test_review_block_missing(self):
        with self.assertRaises(ValueError):review_extraction(load_sample('HS02'),{'expected_version':1,'checked':True,'reviewer':'A','reason':'test'})
    def test_review_block_mismatch(self):
        with self.assertRaises(ValueError):review_extraction(load_sample('HS04'),{'expected_version':1,'checked':True,'reviewer':'A','reason':'test'})
    def test_stale_revision(self):
        with self.assertRaises(ValueError):review_extraction(self.s,{'expected_version':0,'checked':True,'reviewer':'A','reason':'test'})
    def test_human_edit_clears_review(self):
        review_extraction(self.s,{'expected_version':1,'checked':True,'reviewer':'A','reason':'check'})
        f=self.s['case']['documents'][0]['fields']['net_monthly_income_vnd']
        edit_field(self.s,{'expected_version':1,'document_id':'HS01-APP','field':'net_monthly_income_vnd','value':f['value'],'evidence':f['evidence'],'reviewer':'B','reason':'Recheck'})
        self.assertEqual(self.s['version'],2);self.assertEqual(self.s['extraction_review']['status'],'Pending')
    def test_edit_rejects_wrong_source_value(self):
        f=self.s['case']['documents'][0]['fields']['net_monthly_income_vnd']
        with self.assertRaises(ValueError):edit_field(self.s,{'expected_version':1,'document_id':'HS01-APP','field':'net_monthly_income_vnd','value':30000000,'evidence':f['evidence'],'reviewer':'A','reason':'test'})
    def test_import_valid_fixture(self):
        import_assisted(self.s,self.import_body());self.assertEqual(self.s['mode'],'ASSISTED_USER_IMPORTED');self.assertEqual(len(self.s['llm_runs']),1)
    def test_import_rejects_fabricated_quote(self):
        b=self.import_body();b['result']['documents'][0]['fields']['full_name']['evidence'][0]['quote']='Nobody'
        with self.assertRaises(ValueError):import_assisted(self.s,b)
    def test_import_rejects_wrong_page(self):
        b=self.import_body();b['result']['documents'][0]['fields']['full_name']['evidence'][0]['locator']='page=99; field=Họ và tên'
        with self.assertRaises(ValueError):import_assisted(self.s,b)
    def test_import_rejects_wrong_case(self):
        b=self.import_body();b['result']['case_id']='HS04'
        with self.assertRaises(ValueError):import_assisted(self.s,b)
    def test_import_rejects_missing_field(self):
        b=self.import_body();del b['result']['documents'][0]['fields']['full_name']
        with self.assertRaises(ValueError):import_assisted(self.s,b)
    def test_import_rejects_duplicate_doc(self):
        b=self.import_body();b['result']['documents'][1]=b['result']['documents'][0]
        with self.assertRaises(ValueError):import_assisted(self.s,b)
    def test_prompt_has_no_answers(self):
        p=assisted_prompt(self.s);self.assertIn('"value": null',p);self.assertNotIn('evaluation_only',p);self.assertNotIn('ground_truth',p)
    def test_invalid_pdf(self):
        with self.assertRaises(ValueError):make_state('HS01',{'application':b'not a PDF'})
    def test_empty_csv(self):
        with self.assertRaises(ValueError):read_csv(b'transaction_id,date,direction,amount_vnd,account_holder_id,counterparty,description\n','TEST')
    def test_csv_duplicate(self):
        p=ROOT/'runtime/cases/HS01/bank_statement.csv';data=p.read_text(encoding='utf-8-sig');data+=data.splitlines()[1]+'\n'
        with self.assertRaises(ValueError):read_csv(data.encode(),'TEST')
    def test_unknown_template_returns_null(self):
        self.assertIsNone(baseline(['Unrelated text'],'T',['full_name'])['full_name']['value'])
    def test_threshold_boundary(self):
        d=self.s['case']['documents'][0]['fields'];d['net_monthly_income_vnd']['value']=24000000;refresh(self.s)
        self.assertNotIn('INCOME_MISMATCH',[i['code'] for i in self.s['issues']])
    def test_pathlike_case_rejected(self):
        with self.assertRaises(ValueError):make_state('../bad',{'application':b'anything'})
if __name__=='__main__':unittest.main(verbosity=2)
