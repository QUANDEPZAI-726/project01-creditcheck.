"""Streamlit framework tests, not full browser tests; no network API calls."""
import unittest
import copy
import json
from unittest.mock import patch
from pathlib import Path
from streamlit.testing.v1 import AppTest
APP=Path(__file__).resolve().parents[1]/'streamlit_app.py'

class StreamlitTests(unittest.TestCase):
    def fresh(self):
        at=AppTest.from_file(str(APP)).run(timeout=30)
        self.assertFalse(at.exception,[e.message for e in at.exception])
        return at

    def test_all_nine_pages_without_key(self):
        at=self.fresh()
        for page in list(at.radio[0].options):
            at.radio[0].set_value(page).run(timeout=30)
            self.assertFalse(at.exception,(page,[e.message for e in at.exception]))

    def test_all_samples_and_session_isolation(self):
        a,b=self.fresh(),self.fresh()
        for cid in ('HS01','HS02','HS03','HS04','HS05'):
            a.selectbox[0].select(cid)
            next(x for x in a.button if x.label=='Mở hồ sơ mẫu').click().run(timeout=30)
            self.assertFalse(a.exception)
            self.assertEqual(a.session_state['dossier']['case']['case_id'],cid)
            self.assertEqual(b.session_state['dossier']['case']['case_id'],'HS01')

    def test_restore_and_report_page(self):
        at=self.fresh()
        next(x for x in at.button if x.label.startswith('Khôi phục HS01')).click().run(timeout=30)
        at.radio[0].set_value('7 · Credit Summary').run(timeout=30)
        self.assertFalse(at.exception)
        self.assertIsNotNone(at.session_state['dossier']['phase3']['summary'])

    def test_review_form_requires_checks(self):
        at=self.fresh();at.radio[0].set_value('4 · Kiểm tra & xuất').run(timeout=30)
        next(x for x in at.button if x.label=='Xác nhận phần trích xuất').click().run(timeout=30)
        self.assertFalse(at.exception)
        self.assertTrue(at.error)
        self.assertEqual(at.session_state['dossier']['extraction_review']['status'],'Pending')

    def test_api_no_credentials_keeps_state(self):
        at=self.fresh();at.radio[0].set_value('3 · Gemini trích xuất').run(timeout=30)
        at.checkbox[0].check().run(timeout=30)
        next(x for x in at.button if x.label=='Chạy Gemini trích xuất').click().run(timeout=30)
        self.assertFalse(at.exception)
        self.assertTrue(at.error)
        self.assertEqual(at.session_state['dossier']['mode'],'RULE_BASELINE')

    def test_complete_api_workflow_with_mocked_transport(self):
        at=self.fresh()
        at.secrets={'GEMINI_API_KEY':'test-not-a-real-key','DEMO_ACCESS_CODE':'test-code','GEMINI_MODEL':'test-model'}
        at.session_state['api_unlocked']=True
        def call(task_page, label, obj):
            at.radio[0].set_value(task_page).run(timeout=30)
            at.session_state['last_api_call']=-100
            at.checkbox[0].check().run(timeout=30)
            with patch('gemini_service.GeminiClient.generate',return_value=(obj,{'mock':True,'model':'test-model'})):
                next(x for x in at.button if x.label==label).click().run(timeout=30)
            self.assertFalse(at.exception)
            self.assertFalse(at.error, [e.value for e in at.error])
        s=at.session_state['dossier']
        obj={'case_id':'HS01','documents':[{'document_id':d['document_id'],'fields':copy.deepcopy(d['fields'])} for d in s['case']['documents'] if d['available'] and d['source_type']!='bank_statement']}
        call('3 · Gemini trích xuất','Chạy Gemini trích xuất',obj)
        at.radio[0].set_value('4 · Kiểm tra & xuất').run(timeout=30)
        next(x for x in at.text_input if x.label=='Người kiểm tra').set_value('TEST')
        at.text_area[0].set_value('Mock workflow source check')
        at.checkbox[0].check()
        next(x for x in at.button if x.label=='Xác nhận phần trích xuất').click().run(timeout=30)
        self.assertFalse(at.error)
        obj=json.loads((APP.parent/'incoming/HS01_classification.json').read_text())
        call('5 · Phân loại & nguồn thu','Chạy Gemini phân loại',obj)
        next(x for x in at.text_input if x.label=='Người xác minh thu nhập').set_value('TEST')
        next(x for x in at.text_area if x.label.startswith('Ghi chú xác minh')).set_value('Mock workflow period check')
        next(x for x in at.checkbox if x.label=='Đã đối chiếu nhãn và nguồn trả lương.').check()
        next(x for x in at.checkbox if x.label=='Đã kiểm tra kỳ sao kê đầy đủ.').check()
        next(x for x in at.button if x.label=='Xác minh thu nhập và tính chỉ số').click().run(timeout=30)
        self.assertFalse(at.error,[e.value for e in at.error])
        from phase3 import template
        obj=template(at.session_state['dossier'])
        for sec in ('overview','metric_explanations','limitations','verification_questions'):
            obj[sec]=[{'text':'Kiểm tra diễn giải giả lập theo căn cứ.', 'refs':['METRICS' if sec=='metric_explanations' else 'CASE']}]
        call('7 · Credit Summary','Chạy Gemini tạo báo cáo',obj)
        self.assertIsNotNone(at.session_state['dossier']['phase3']['summary'])
        self.assertIsNone(at.session_state['dossier']['phase3']['content_review'])

if __name__=='__main__':unittest.main()
