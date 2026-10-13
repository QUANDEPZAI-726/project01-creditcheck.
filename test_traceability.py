import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from sample_data import load_sample
from traceability import sync,build
from phase2 import review_extraction_phase2,import_classification,verify_income
class TraceTests(unittest.TestCase):
    def test_preserves_user_summary_review(self):
        s=json.loads((ROOT/'seed/HS01_session.json').read_text());review=s['phase3']['content_review'];sync(s);self.assertEqual(s['phase3']['content_review'],review);self.assertEqual(s['case']['review']['summary_status'],'Reviewed')
    def test_hs01_has_no_invented_alert(self):
        s=json.loads((ROOT/'seed/HS01_session.json').read_text());sync(s);self.assertEqual(s['traceability']['alerts'],[])
    def test_income_mismatch_links_both_documents(self):
        s=load_sample('HS03');tr=build(s);alert=next(a for a in tr['alerts'] if a['code']=='INCOME_MISMATCH')
        self.assertEqual({e['document_id'] for e in alert['evidence']},{'HS03-APP','HS03-INC'});self.assertTrue(all(e['quote_found_in_source'] for e in alert['evidence']));self.assertEqual({e['quote'] for e in alert['evidence']},{'30.000.000','20.000.000'})
    def test_identity_links_account_column(self):
        s=load_sample('HS04');a=next(a for a in build(s)['alerts'] if a['code']=='BORROWER_ID_MISMATCH');ev=[e for e in a['evidence'] if e['locator_type']=='csv_account_holder_id']
        self.assertTrue(ev);self.assertTrue(all(e['quote']=='SYN-P904' and e['quote_found_in_source'] for e in ev));self.assertTrue(all(e['original_row']['account_holder_id']=='SYN-P904' for e in ev))
    def test_missing_document_has_no_fake_quote(self):
        s=load_sample('HS02');a=next(a for a in build(s)['alerts'] if a['code']=='MISSING_DOCUMENT');self.assertTrue(all(e['quote'] is None and not e['source_available'] and e['download_endpoint'] is None for e in a['evidence']))
    def test_linked_hash_matches_current_source(self):
        s=load_sample('HS03')
        for a in build(s)['alerts']:
            for e in a['evidence']:self.assertEqual(e['source_sha256'],s['sources'][e['document_id']]['sha256'])
    def test_ids_are_stable_unique(self):
        s=load_sample('HS04');a=build(s)['alerts'];self.assertEqual(a,build(s)['alerts']);self.assertEqual(len(a),len({e['alert_id'] for e in a}))
    def test_trace_build_does_not_mutate_review(self):
        s=json.loads((ROOT/'seed/HS01_session.json').read_text());sync(s);before=json.dumps(s,sort_keys=True);build(s);self.assertEqual(json.dumps(s,sort_keys=True),before)
    def test_metrics_alert_keeps_rule_and_salary_evidence(self):
        s=load_sample('HS03');review_extraction_phase2(s,{'expected_version':s['version'],'reviewer':'Test','reason':'Accurate transcription; mismatch remains','checked':True})
        obj={'case_id':'HS03','source_sha256':s['sources']['HS03-BANK']['sha256'],'transactions':[{'transaction_id':t['transaction_id'],'label':'salary' if t['description'].startswith('LUONG') else 'other','reason':'Fixture, not live LLM','evidence':t['evidence']} for t in s['case']['transactions']]}
        import_classification(s,{'expected_version':s['version'],'attest':True,'model':'Test fixture','result':obj})
        verify_income(s,{'expected_version':s['version'],'reviewer':'Test','reason':'Source checked','checked':True,'coverage_checked':True,'acknowledge_gap':True,'coverage_start':'2026-07-01','coverage_end':'2026-09-30'});sync(s)
        a=next(a for a in s['traceability']['alerts'] if a['code']=='HIGH_DTI');self.assertEqual(a['rule_inputs']['metrics']['dti_pct'],50.31);self.assertIn('HS03-BANK',{e['document_id'] for e in a['evidence']});self.assertTrue(all(e['quote_found_in_source'] for e in a['evidence']))
    def test_ambiguous_income_links_exact_transaction(self):
        s=load_sample('HS05');review_extraction_phase2(s,{'expected_version':s['version'],'reviewer':'Test','reason':'Accurate transcription','checked':True})
        obj={'case_id':'HS05','source_sha256':s['sources']['HS05-BANK']['sha256'],'transactions':[{'transaction_id':t['transaction_id'],'label':'uncertain' if t['description'].startswith('THU NHAP') else 'salary' if t['description'].startswith('LUONG') else 'other','reason':'Fixture, not live LLM','evidence':t['evidence']} for t in s['case']['transactions']]}
        import_classification(s,{'expected_version':s['version'],'attest':True,'model':'Test fixture','result':obj});sync(s);a=next(a for a in s['traceability']['alerts'] if a['code']=='AMBIGUOUS_INCOME');self.assertTrue(all('THU NHAP' in e['quote'] and e['original_row'] is not None for e in a['evidence']))
if __name__=='__main__':unittest.main(verbosity=2)
