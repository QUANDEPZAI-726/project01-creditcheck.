import copy,json,sys,unittest,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from phase3 import sync,template,validate,summary_prompt,import_summary,review_summary,report_text,same_data
from phase2 import set_rate,edit_classification
from core import edit_field
from sample_data import load_sample
class Phase3Tests(unittest.TestCase):
    def setUp(self):
        self.s=json.loads((ROOT/'seed/HS01_session.json').read_text());sync(self.s)
        self.s['phase3']['summary']=None;self.s['phase3']['content_review']=None;sync(self.s)
        self.obj=json.loads((ROOT/'incoming/HS01_summary.json').read_text())
    def imported(self):import_summary(self.s,{'expected_version':self.s['version'],'model':'Test fixture, not live LLM','attest':True,'result':copy.deepcopy(self.obj)})
    def reviewed(self):review_summary(self.s,{'expected_version':self.s['version'],'reviewer':'Test','reason':'Read and checked all content','checked_facts':True,'checked_limits':True})
    def incomplete_object(self,cid):
        self.s=load_sample(cid);sync(self.s);obj=template(self.s)
        for section in ['overview','limitations','verification_questions']:obj[section]=[{'text':'Synthetic test fixture: needs human verification.','refs':['SCOPE']}]
        obj['metric_explanations']=[{'text':'Metrics pending; insufficient verified inputs.','refs':['PENDING_METRICS']}]
        return obj
    def test_preserves_user_verified_income(self):self.assertEqual(self.s['phase2']['income_review']['reviewer'],'Anh Quân');self.assertEqual(self.s['phase2']['metrics']['dti_pct'],33.54)
    def test_prepared_is_current(self):validate(self.s,self.obj)
    def test_browser_json_roundtrip(self):
        result=subprocess.run(['node','-e','let s="";process.stdin.on("data",x=>s+=x);process.stdin.on("end",()=>process.stdout.write(JSON.stringify(JSON.parse(s))))'],input=json.dumps(self.obj),text=True,capture_output=True,check=True)
        browser_obj=json.loads(result.stdout);validate(self.s,browser_obj)
        self.obj=browser_obj;self.imported();self.reviewed();self.assertEqual(self.s['case']['review']['summary_status'],'Reviewed')
    def test_numeric_comparison_keeps_types_and_values(self):
        self.assertTrue(same_data(0,0.0));self.assertTrue(same_data(20000000,20000000.0))
        self.assertFalse(same_data(False,0));self.assertFalse(same_data('0',0));self.assertFalse(same_data(33.54,33.55));self.assertFalse(same_data(float('nan'),float('nan')))
    def test_import_stays_draft(self):self.imported();self.assertIsNone(self.s['phase3']['content_review']);self.assertEqual(self.s['case']['review']['summary_status'],'Draft')
    def test_review_keeps_human_review_status(self):self.imported();self.reviewed();self.assertEqual(self.s['case']['review']['summary_status'],'Reviewed');self.assertEqual(self.s['phase3']['report_status'],'Human review required')
    def test_no_attest_rejected(self):
        with self.assertRaises(ValueError):import_summary(self.s,{'expected_version':self.s['version'],'model':'Test','attest':False,'result':self.obj})
    def test_no_model_rejected(self):
        with self.assertRaises(ValueError):import_summary(self.s,{'expected_version':self.s['version'],'attest':True,'result':self.obj})
    def test_tampered_metrics_rejected(self):
        self.obj['metrics']['dti_pct']=10
        with self.assertRaises(ValueError):validate(self.s,self.obj)
    def test_tampered_borrower_rejected(self):
        self.obj['key_information']['full_name']='Different person'
        with self.assertRaises(ValueError):validate(self.s,self.obj)
    def test_tampered_status_rejected(self):
        self.obj['review_status']='Approved'
        with self.assertRaises(ValueError):validate(self.s,self.obj)
    def test_missing_context_hash_rejected(self):
        del self.obj['context_hash']
        with self.assertRaises(ValueError):validate(self.s,self.obj)
    def test_unknown_ref_rejected(self):
        self.obj['overview'][0]['refs']=['FAKE-DOC']
        with self.assertRaises(ValueError):validate(self.s,self.obj)
    def test_metric_trace_ref_required(self):
        for r in self.obj['metric_explanations']:r['refs']=['SCOPE']
        with self.assertRaises(ValueError):validate(self.s,self.obj)
    def test_decision_language_rejected(self):
        self.obj['overview'][0]['text']='Đề xuất duyệt khoản vay này.'
        with self.assertRaises(ValueError):validate(self.s,self.obj)
    def test_html_rejected(self):
        self.obj['overview'][0]['text']='<script>bad</script>'
        with self.assertRaises(ValueError):validate(self.s,self.obj)
    def test_stale_revision_rejected(self):
        with self.assertRaises(ValueError):import_summary(self.s,{'expected_version':0,'model':'Test','attest':True,'result':self.obj})
    def test_review_without_summary_rejected(self):
        with self.assertRaises(ValueError):self.reviewed()
    def test_review_without_two_checks_rejected(self):
        self.imported()
        with self.assertRaises(ValueError):review_summary(self.s,{'expected_version':self.s['version'],'reviewer':'Test','reason':'Test','checked_facts':True})
    def test_review_without_reason_rejected(self):
        self.imported()
        with self.assertRaises(ValueError):review_summary(self.s,{'expected_version':self.s['version'],'reviewer':'Test','checked_facts':True,'checked_limits':True})
    def test_rate_change_invalidates_reviewed_summary(self):
        self.imported();self.reviewed();set_rate(self.s,{'expected_version':self.s['version'],'annual_nominal_rate':0,'reviewer':'Test','reason':'Scenario'});sync(self.s)
        self.assertIsNone(self.s['phase3']['summary']);self.assertIsNone(self.s['phase3']['content_review']);self.assertEqual(self.s['case']['review']['summary_status'],'Draft')
        with self.assertRaises(ValueError):validate(self.s,self.obj)
    def test_label_change_invalidates_summary(self):
        self.imported();edit_classification(self.s,{'expected_version':self.s['version'],'transaction_id':'HS01-T0703','label':'other','reviewer':'Test','reason':'Recheck refund'});sync(self.s)
        self.assertIsNone(self.s['phase3']['summary']);self.assertIsNone(self.s['phase2']['income_review'])
    def test_source_edit_invalidates_summary(self):
        self.imported();f=self.s['case']['documents'][0]['fields']['full_name'];edit_field(self.s,{'expected_version':self.s['version'],'document_id':'HS01-APP','field':'full_name','value':f['value'],'evidence':f['evidence'],'reviewer':'Test','reason':'Recheck source'});sync(self.s)
        self.assertIsNone(self.s['phase3']['summary'])
    def test_missing_case_report_has_null_metrics(self):
        obj=self.incomplete_object('HS02');validate(self.s,obj);self.assertEqual(obj['review_status'],'Insufficient information');self.assertTrue(all(v is None for v in obj['metrics'].values()))
        self.obj=obj;self.imported();self.reviewed();self.assertEqual(self.s['case']['review']['data_status'],'Insufficient information');self.assertEqual(self.s['phase3']['report_status'],'Insufficient information')
    def test_flags_cannot_be_deleted(self):
        obj=self.incomplete_object('HS04');self.assertIn('BORROWER_ID_MISMATCH',[r['code'] for r in obj['risk_flags']]);obj['risk_flags']=[]
        with self.assertRaises(ValueError):validate(self.s,obj)
    def test_missing_fields_not_collapsed(self):
        self.s=load_sample('HS01');self.s['case']['documents'][0]['fields']['employer']['value']=None;self.s['case']['documents'][0]['fields']['full_name']['value']=None;sync(self.s)
        self.assertEqual(len(self.s['phase3']['context']['missing_information']),2)
    def test_export_marks_draft_and_provenance(self):
        self.imported();txt=report_text(self.s);self.assertIn('Draft',txt);self.assertIn('Không phải quyết định',txt);self.assertIn('33.54',txt)
    def test_prompt_contains_only_current_context(self):
        txt=summary_prompt(self.s);self.assertIn('MẪU JSON',txt);self.assertIn(self.s['phase3']['context_hash'],txt);self.assertNotIn('evaluation_only',txt)
    def test_reimport_clears_report_review(self):self.imported();self.reviewed();self.imported();self.assertIsNone(self.s['phase3']['content_review'])
    def test_restore_sync_preserves_content_review(self):self.imported();self.reviewed();self.s=json.loads(json.dumps(self.s));sync(self.s);self.assertEqual(self.s['case']['review']['summary_status'],'Reviewed')
if __name__=='__main__':unittest.main(verbosity=2)
