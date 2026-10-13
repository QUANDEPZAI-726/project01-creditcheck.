import copy,json,sys,unittest
from pathlib import Path
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from core import edit_field
from sample_data import load_sample
from phase2 import sync,import_classification,verify_income,edit_classification,pmt,set_rate,months_in_period,review_extraction_phase2
class Phase2Tests(unittest.TestCase):
    def setUp(self):
        self.s=json.loads((ROOT/'seed/HS01_session.json').read_text());sync(self.s)
        self.obj=json.loads((ROOT/'incoming/HS01_classification.json').read_text())
    def imported(self):
        import_classification(self.s,{'expected_version':self.s['version'],'model':'Test fixture, not live call','attest':True,'result':copy.deepcopy(self.obj)})
    def reviewed(self):
        verify_income(self.s,{'expected_version':self.s['version'],'reviewer':'Tester','reason':'Checked salary source','checked':True,'coverage_checked':True,'coverage_start':'2026-07-01','coverage_end':'2026-09-30','acknowledge_gap':True})
    def test_preserves_seed_review(self):self.assertEqual(self.s['extraction_review']['reviewer'],'Anh Quân');self.assertEqual(self.s['extraction_review']['status'],'Reviewed')
    def test_metrics_null_before_human(self):self.imported();self.assertTrue(all(v is None for v in self.s['phase2']['metrics'].values()))
    def test_income_mean_excludes_refunds(self):self.imported();self.assertEqual(self.s['phase2']['preview']['mean_salary_vnd'],20000000)
    def test_hs01_metrics(self):
        self.imported();self.reviewed();m=self.s['phase2']['metrics'];self.assertEqual(m['monthly_payment_vnd'],4707347);self.assertEqual(m['dti_pct'],33.54);self.assertEqual(m['income_gap_pct'],0);self.assertEqual(self.s['case']['review']['data_status'],'Validated for summary')
    def test_zero_rate(self):self.assertEqual(pmt(120000000,24,0),Decimal(5000000))
    def test_invalid_rate(self):
        for rate in [-.01,float('nan'),1.1]:
            with self.assertRaises(ValueError):pmt(100000000,24,rate)
    def test_invalid_period(self):
        with self.assertRaises(ValueError):months_in_period('2026-07-02','2026-09-30')
    def test_fingerprint_change_clears_income(self):
        self.imported();self.reviewed();f=self.s['case']['documents'][0]['fields']['full_name']
        edit_field(self.s,{'expected_version':self.s['version'],'document_id':'HS01-APP','field':'full_name','value':f['value'],'evidence':f['evidence'],'reviewer':'Test','reason':'Recheck'})
        sync(self.s);self.assertIsNone(self.s['phase2']['income_review']);self.assertIsNone(self.s['phase2']['classification']);self.assertIsNone(self.s['phase2']['metrics']['dti_pct'])
    def test_reimport_clears_income(self):self.imported();self.reviewed();self.imported();self.assertIsNone(self.s['phase2']['income_review'])
    def test_label_edit_clears_income(self):
        self.imported();self.reviewed();edit_classification(self.s,{'expected_version':self.s['version'],'transaction_id':'HS01-T0703','label':'other','reviewer':'Test','reason':'Confirm refund'})
        self.assertIsNone(self.s['phase2']['income_review'])
    def test_uncertain_blocks_verification(self):
        self.obj['transactions'][2]['label']='uncertain';self.imported()
        with self.assertRaises(ValueError):self.reviewed()
    def test_debit_salary_rejected(self):
        self.obj['transactions'][1]['label']='salary'
        with self.assertRaises(ValueError):self.imported()
    def test_bad_source_hash(self):
        self.obj['source_sha256']='wrong'
        with self.assertRaises(ValueError):self.imported()
    def test_duplicate_id_rejected(self):
        self.obj['transactions'][1]=self.obj['transactions'][0]
        with self.assertRaises(ValueError):self.imported()
    def test_stale_version(self):
        with self.assertRaises(ValueError):import_classification(self.s,{'expected_version':0,'model':'Test','attest':True,'result':self.obj})
    def test_missing_statement_blocks(self):
        self.s=load_sample('HS02')
        with self.assertRaises(ValueError):self.reviewed()
    def test_identity_mismatch_blocks_income(self):
        self.s=load_sample('HS04');review_extraction_phase2(self.s,{'expected_version':self.s['version'],'reviewer':'Test','reason':'Transcribed source accurately','checked':True})
        bank=self.s['sources']['HS04-BANK'];self.obj={'case_id':'HS04','source_sha256':bank['sha256'],'transactions':[{'transaction_id':t['transaction_id'],'label':'salary' if t['description'].startswith('LUONG') else 'other','reason':'Synthetic test fixture','evidence':t['evidence']} for t in self.s['case']['transactions']]}
        self.imported()
        with self.assertRaises(ValueError):self.reviewed()
    def test_hs03_gap_and_high_dti(self):
        self.s=load_sample('HS03');review_extraction_phase2(self.s,{'expected_version':self.s['version'],'reviewer':'Test','reason':'Facts copied accurately, mismatch remains','checked':True})
        self.obj={'case_id':'HS03','source_sha256':self.s['sources']['HS03-BANK']['sha256'],'transactions':[{'transaction_id':t['transaction_id'],'label':'salary' if t['description'].startswith('LUONG') else 'other','reason':'Synthetic test fixture','evidence':t['evidence']} for t in self.s['case']['transactions']]}
        self.imported();self.reviewed();m=self.s['phase2']['metrics'];self.assertEqual(m['dti_pct'],50.31);self.assertEqual(m['income_gap_pct'],50);self.assertIn('HIGH_DTI',[f['code'] for f in self.s['phase2']['flags']])
    def test_rate_change_recomputes(self):
        self.imported();self.reviewed();set_rate(self.s,{'expected_version':self.s['version'],'annual_nominal_rate':0,'reviewer':'Test','reason':'Boundary zero interest'})
        self.assertIsNotNone(self.s['phase2']['income_review']);self.assertEqual(self.s['phase2']['metrics']['monthly_payment_vnd'],4166667)
    def test_zero_income_no_division(self):
        self.obj['transactions'][0]['label']='other';self.obj['transactions'][3]['label']='other';self.obj['transactions'][6]['label']='other';self.imported()
        with self.assertRaises(ValueError):self.reviewed()
if __name__=='__main__':unittest.main(verbosity=2)
