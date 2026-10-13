"""CreditCheck 0.5 — per-browser session, Gemini tasks and grounded chat."""
import base64
import copy
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import sys
import threading
import time
import zipfile
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'app'))
from core import make_state, public_state, edit_field, LABELS, now
from phase2 import review_extraction_phase2, verify_income, edit_classification, set_rate
from phase3 import report_text
from traceability import sync
from gemini_service import GeminiClient, run_task, chat

st.set_page_config(page_title='CreditCheck · Project 01', page_icon='🏦', layout='wide')
st.markdown('''<style>
.stApp {background:#f5f7fc;} h1,h2,h3 {color:#142448;}
[data-testid="stSidebar"] {background:#eaf0fa;}
[data-testid="stMetric"] {background:white;padding:16px;border-radius:12px;}
</style>''', unsafe_allow_html=True)

def secret(name, default=''):
    try:
        return str(st.secrets.get(name, os.environ.get(name, default)))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return os.environ.get(name, default)

@st.cache_resource
def shared_budget():
    # Counters only; never store user dossiers/chats in a shared cache.
    return {'lock': threading.Lock(), 'times': []}

def reserve_call():
    code = secret('DEMO_ACCESS_CODE')
    if not code or not st.session_state.get('api_unlocked'):
        raise ValueError('Mở quyền chạy API bằng mã demo trước.')
    if not secret('GEMINI_API_KEY') or secret('GEMINI_API_KEY').startswith('REPLACE_'):
        raise ValueError('Chưa cấu hình Gemini API key thật trong Secrets.')
    b = shared_budget()
    current = time.monotonic()
    with b['lock']:
        b['times'] = [x for x in b['times'] if current - x < 3600]
        if len(b['times']) >= 60:
            raise ValueError('Đã đạt giới hạn demo 60 lượt/giờ trên máy chủ này.')
        if current - st.session_state.get('last_api_call', -100) < 5:
            raise ValueError('Chờ ít nhất 5 giây giữa hai lượt API.')
        if st.session_state.get('api_calls', 0) >= 30:
            raise ValueError('Phiên này đã đạt giới hạn 30 lượt API.')
        b['times'].append(current)
        st.session_state.last_api_call = current
        st.session_state.api_calls = st.session_state.get('api_calls', 0) + 1
    return GeminiClient(secret('GEMINI_API_KEY'), secret('GEMINI_MODEL', 'gemini-flash-latest'))

def sample(cid):
    folder = ROOT / 'runtime/cases' / cid
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    files = {d['source_type']: (folder / d['path']).read_bytes()
             for d in manifest['documents'] if d['available']}
    coverage = next(d for d in manifest['documents'] if d['source_type'] == 'bank_statement')
    state = make_state(cid, files, coverage if coverage['available'] else None)
    sync(state)
    return state

def commit(state, reset_chat=True):
    sync(state)
    st.session_state.dossier = state
    if reset_chat:
        st.session_state.messages = []
    st.session_state.notice = 'Đã cập nhật. Kiểm tra nguồn và trạng thái trước khi tiếp tục.'
    st.rerun()

def mutate(fn, body):
    try:
        state = copy.deepcopy(st.session_state.dossier)
        fn(state, dict(body, expected_version=state['version']))
        commit(state)
    except (ValueError, TypeError, KeyError) as exc:
        st.error(str(exc))

def api_button(task, label, key):
    consent = st.checkbox('Tôi đồng ý gửi dữ liệu giả lập của hồ sơ này đến Google Gemini.', key=key+'_consent')
    if st.button(label, key=key, type='primary', disabled=not consent):
        try:
            client = reserve_call()
            with st.spinner('Gemini đang xử lý; Python sẽ kiểm tra kết quả…'):
                state = run_task(st.session_state.dossier, task, client)
            commit(state)
        except (ValueError, TypeError, KeyError) as exc:
            st.error(str(exc))
            st.caption('Dữ liệu cũ được giữ. Không tự dùng kết quả mẫu thay cho API.')

def source_view(state, did, suffix):
    src = state['sources'].get(did)
    if not src:
        st.info('Nguồn chưa được cung cấp.')
        return
    st.text(src['text'])
    ext = '.csv' if src['role'] == 'bank_statement' else '.pdf'
    st.download_button('Tải nguồn '+did, base64.b64decode(src['bytes_b64']),
                       file_name=did+ext, key='source_'+suffix+'_'+did)

def archive(state):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('case.json', json.dumps(state['case'], ensure_ascii=False, indent=2))
        z.writestr('review_and_log.json', json.dumps(public_state(state), ensure_ascii=False, indent=2))
        z.writestr('evidence_trace.json', json.dumps(state['traceability'], ensure_ascii=False, indent=2))
        z.writestr('chat.json', json.dumps(st.session_state.messages, ensure_ascii=False, indent=2))
        if state['phase3']['summary']:
            z.writestr('summary.txt', report_text(state))
        for did, src in state['sources'].items():
            z.writestr('sources/'+did+('.csv' if src['role']=='bank_statement' else '.pdf'), base64.b64decode(src['bytes_b64']))
    return buf.getvalue()

if 'dossier' not in st.session_state:
    st.session_state.dossier = sample('HS01')
    st.session_state.messages = []
state = st.session_state.dossier
sync(state)
cid = state['case']['case_id']
revision = str(state['version'])
prefix = cid+'_'+revision+'_'

with st.sidebar:
    st.title('🏦 CreditCheck')
    st.caption('Project 01 · Gemini API · v0.5')
    page = st.radio('Quy trình', ['1 · Nhận hồ sơ', '2 · Dữ liệu & nguồn', '3 · Gemini trích xuất',
                                 '4 · Kiểm tra & xuất', '5 · Phân loại & nguồn thu',
                                 '6 · Chỉ số Python', '7 · Credit Summary',
                                 '8 · Truy vết cảnh báo', '9 · Chatbox hồ sơ'])
    st.divider()
    st.write('API: '+('Đã cấu hình khóa' if secret('GEMINI_API_KEY') and not secret('GEMINI_API_KEY').startswith('REPLACE_') else 'Chưa cấu hình khóa'))
    st.caption('Model: '+secret('GEMINI_MODEL', 'gemini-flash-latest'))
    code = st.text_input('Mã truy cập API của nhóm', type='password', key='access_input')
    if st.button('Mở quyền chạy API'):
        expected = secret('DEMO_ACCESS_CODE')
        if expected and not expected.startswith('REPLACE_') and hmac.compare_digest(code.encode(), expected.encode()):
            st.session_state.api_unlocked = True
            st.success('Đã mở quyền cho phiên này.')
        else:
            st.session_state.api_unlocked = False
            st.error('Mã chưa đúng hoặc máy chủ chưa cấu hình mã.')
    st.caption('Mỗi phiên tối đa 30 lượt. Bộ đếm theo máy chủ không thay thế giới hạn ngân sách tại nhà cung cấp.')
    st.caption('Dữ liệu chỉ giữ trong phiên trình duyệt. Tải ZIP trước khi đổi/đóng phiên.')

st.title('AI Credit Underwriting Copilot')
st.caption('Hồ sơ giả lập · LLM hỗ trợ, Python tính và kiểm tra, con người xác minh · Không tự duyệt vay')
cols = st.columns(4)
cols[0].metric('Hồ sơ', cid)
cols[1].metric('Trích xuất', state['extraction_review']['status'])
cols[2].metric('Thu nhập', 'Reviewed' if state['phase2']['income_review'] else 'Chưa xác minh')
cols[3].metric('Rà soát', state['phase3']['report_status'])
if 'notice' in st.session_state:
    st.success(st.session_state.pop('notice'))

if page.startswith('1 '):
    st.header('Nhận hồ sơ')
    st.write('Ba nguồn: đơn vay PDF, xác nhận thu nhập PDF và sao kê CSV có văn bản đúng mẫu.')
    selected = st.selectbox('Hồ sơ mẫu', ['HS01','HS02','HS03','HS04','HS05'])
    if st.button('Mở hồ sơ mẫu'):
        commit(sample(selected))
    if st.button('Khôi phục HS01 đã kiểm tra · kết quả lưu v0.4'):
        restored = json.loads((ROOT/'seed/HS01_session.json').read_text(encoding='utf-8'))
        commit(restored)
    st.caption('Khôi phục dùng kết quả đã lưu từ demo trước, không gọi Gemini mới.')
    with st.expander('Tải tài liệu giả lập của bạn'):
        with st.form('upload'):
            uploaded_cid = st.text_input('Mã hồ sơ', value='HS06')
            app = st.file_uploader('Đơn vay PDF', type=['pdf'])
            income = st.file_uploader('Xác nhận thu nhập PDF', type=['pdf'])
            bank = st.file_uploader('Sao kê CSV', type=['csv'])
            if st.form_submit_button('Đọc tài liệu'):
                try:
                    files = {k:v.getvalue() for k,v in [('application',app),('income_certificate',income),('bank_statement',bank)] if v}
                    if sum(map(len, files.values())) > 10*1024*1024:
                        raise ValueError('Tổng tệp tối đa 10 MB.')
                    commit(make_state(uploaded_cid, files))
                except (ValueError, TypeError, KeyError) as exc:
                    st.error(str(exc))

elif page.startswith('2 '):
    st.header('Dữ kiện và căn cứ nguồn')
    for doc in state['case']['documents']:
        with st.expander(doc['document_id']+' · '+doc['source_type'], expanded=doc['source_type']=='application'):
            if not doc['available']:
                st.warning('Thiếu nguồn.')
                continue
            if doc['source_type'] != 'bank_statement':
                st.dataframe([{'Trường':LABELS.get(k,k),'Giá trị':str(f['value']),
                               'Căn cứ':json.dumps(f['evidence'],ensure_ascii=False)} for k,f in doc['fields'].items()], width='stretch')
            source_view(state, doc['document_id'], 'facts')
    st.subheader('Giao dịch sao kê')
    st.dataframe(state['case']['transactions'], width='stretch')
    with st.expander('Sửa lỗi trích xuất có căn cứ'):
        editable = {d['document_id']:d for d in state['case']['documents'] if d['available'] and d['source_type']!='bank_statement'}
        if editable:
            did = st.selectbox('Tài liệu cần sửa', list(editable), key=prefix+'edit_doc')
            field = st.selectbox('Trường cần sửa', list(editable[did]['fields']), key=prefix+'edit_field')
            with st.form(prefix+'edit'):
                value_json = st.text_input('Giá trị JSON: số không có dấu phân cách; chuỗi đặt trong dấu nháy', value=json.dumps(editable[did]['fields'][field]['value'],ensure_ascii=False))
                pg = st.number_input('Trang nguồn', min_value=1, value=1)
                quote = st.text_input('Trích dẫn nguyên văn giá trị')
                reviewer = st.text_input('Người sửa')
                reason = st.text_input('Lý do sửa')
                if st.form_submit_button('Sửa và yêu cầu kiểm tra lại'):
                    try:
                        value = json.loads(value_json)
                        ev = [] if value is None else [{'document_id':did,'locator_type':'pdf_page_field',
                              'locator':f'page={pg}; field={LABELS[field]}','quote':quote}]
                        mutate(edit_field, {'document_id':did,'field':field,'value':value,'evidence':ev,'reviewer':reviewer,'reason':reason})
                    except ValueError as exc:
                        st.error(str(exc))

elif page.startswith('3 '):
    st.header('Gemini trích xuất trực tiếp')
    st.write('Gửi văn bản PDF cho Gemini; Python kiểm tra JSON và căn cứ trước khi ghi nhận. Sao kê CSV được đọc bằng Python.')
    api_button('extraction', 'Chạy Gemini trích xuất', prefix+'extract')
    st.info('Nhập kết quả mới hủy các xác nhận liên quan. Sau đó xem tab 2 và xác nhận ở tab 4.')
    with st.expander('Các lần chạy LLM và nguồn gốc'):
        st.json(state['llm_runs'])

elif page.startswith('4 '):
    st.header('Kiểm tra phần trích xuất')
    for issue in state['issues']:
        st.warning(issue['code']+': '+issue['message'])
    with st.form(prefix+'review_extraction'):
        name = st.text_input('Người kiểm tra')
        note = st.text_area('Ghi chú đối chiếu nguồn')
        checked = st.checkbox('Tôi đã đối chiếu các trường với tài liệu nguồn.')
        if st.form_submit_button('Xác nhận phần trích xuất'):
            mutate(review_extraction_phase2, {'reviewer':name,'reason':note,'checked':checked})
    st.info('Xác nhận trích xuất không xác minh thu nhập và không duyệt vay.')
    st.download_button('Tải dữ liệu JSON', json.dumps(state['case'],ensure_ascii=False,indent=2), cid+'_case.json', 'application/json')
    st.download_button('Tải ZIP hồ sơ, nguồn và nhật ký', archive(state), cid+'_review.zip', 'application/zip')
    with st.expander('Nhật ký'):
        st.json(state['events'])

elif page.startswith('5 '):
    st.header('Phân loại giao dịch và xác minh nguồn thu')
    api_button('classification', 'Chạy Gemini phân loại', prefix+'classify')
    p = state['phase2']
    if p['classification']:
        st.dataframe(p['classification']['rows'], width='stretch')
        with st.expander('Sửa nhãn giao dịch với lý do và căn cứ'):
            rows = p['classification']['rows']
            tid = st.selectbox('Giao dịch', [r['transaction_id'] for r in rows], key=prefix+'tid')
            with st.form(prefix+'edit_class'):
                label = st.selectbox('Nhãn mới', ['salary','other','uncertain'])
                name = st.text_input('Người kiểm tra nhãn')
                reason = st.text_input('Lý do thay đổi')
                note = st.text_area('Căn cứ bổ sung đã kiểm tra')
                if st.form_submit_button('Cập nhật nhãn'):
                    mutate(edit_classification, {'transaction_id':tid,'label':label,'reviewer':name,'reason':reason,'supporting_note':note})
    st.subheader('Thu nhập xem trước · chưa phải xác minh')
    st.json(p.get('preview'))
    coverage = next((d for d in state['case']['documents'] if d['source_type']=='bank_statement'), {})
    with st.form(prefix+'income_review'):
        start = st.text_input('Từ ngày YYYY-MM-DD', value=coverage.get('coverage_start') or '2026-07-01')
        end = st.text_input('Đến ngày YYYY-MM-DD', value=coverage.get('coverage_end') or '2026-09-30')
        name = st.text_input('Người xác minh thu nhập')
        note = st.text_area('Ghi chú xác minh và căn cứ dùng thu nhập sao kê')
        checked = st.checkbox('Đã đối chiếu nhãn và nguồn trả lương.')
        complete = st.checkbox('Đã kiểm tra kỳ sao kê đầy đủ.')
        gap = st.checkbox('Đã xem chênh lệch thu nhập nếu có và ghi căn cứ ở trên.')
        if st.form_submit_button('Xác minh thu nhập và tính chỉ số'):
            mutate(verify_income, {'coverage_start':start,'coverage_end':end,'reviewer':name,'reason':note,
                                  'checked':checked,'coverage_checked':complete,'acknowledge_gap':gap})

elif page.startswith('6 '):
    st.header('Chỉ số do Python tính')
    st.json(state['phase2']['metrics'])
    st.caption('null = chưa đủ điều kiện tính, không phải giá trị 0. DTI > 40% và chênh lệch > 20% là ngưỡng giả lập.')
    with st.expander('Công thức, giả định và đầu vào'):
        st.json(state['phase2']['config'])
        st.json(state['phase2'].get('calculation_trace'))
    with st.form(prefix+'rate'):
        rate = st.number_input('Lãi danh nghĩa %/năm', min_value=0.0,max_value=100.0,value=state['phase2']['config']['annual_nominal_rate']*100)
        name = st.text_input('Người thay giả định')
        note = st.text_input('Lý do thay lãi suất')
        if st.form_submit_button('Tính lại với lãi suất mới'):
            mutate(set_rate, {'annual_nominal_rate':rate/100,'reviewer':name,'reason':note})
    st.caption('Thay giả định làm báo cáo cũ mất hiệu lực. Chưa tính phí và bảo hiểm.')

elif page.startswith('7 '):
    st.header('Credit Review Summary')
    api_button('summary', 'Chạy Gemini tạo báo cáo', prefix+'summary')
    p = state['phase3']
    if p['summary']:
        st.text(report_text(state))
        with st.form(prefix+'summary_review'):
            name = st.text_input('Người kiểm tra báo cáo')
            note = st.text_area('Ghi chú kiểm tra nội dung')
            facts = st.checkbox('Đã kiểm tra số liệu, nguồn, cảnh báo và thông tin thiếu.')
            limits = st.checkbox('Đã kiểm tra giới hạn và câu hỏi xác minh; đây không phải quyết định vay.')
            if st.form_submit_button('Xác nhận đã kiểm tra nội dung'):
                from phase3 import review_summary
                mutate(review_summary, {'reviewer':name,'reason':note,'checked_facts':facts,'checked_limits':limits})
        st.download_button('Tải báo cáo TXT', report_text(state), cid+'_Credit_Review_Summary.txt')
        st.download_button('Tải ZIP báo cáo và hồ sơ', archive(state), cid+'_review.zip', 'application/zip')
    else:
        st.info('Chưa có bản nháp. Có thể tạo báo cáo khi thiếu dữ liệu, nhưng chỉ số phải giữ null và thông tin thiếu phải được nêu rõ.')

elif page.startswith('8 '):
    st.header('Truy vết cảnh báo')
    trace = state['traceability']
    if not trace['alerts']:
        st.success('Không có cảnh báo theo các quy tắc hiện tại. Điều này không có nghĩa được duyệt vay.')
    for alert in trace['alerts']:
        with st.expander(alert['code']+' · '+alert['message'], expanded=True):
            st.write(alert['rule'])
            st.json(alert['rule_inputs'])
            for i,evidence in enumerate(alert['evidence']):
                st.write(evidence['document_id']+' · '+evidence['locator'])
                st.text(evidence.get('quote') or 'Không có trích dẫn vì thiếu nguồn/metadata.')
                with st.expander('Mở nguồn · '+str(i+1), expanded=False):
                    source_view(state, evidence['document_id'], alert['alert_id']+'_'+str(i))
    st.download_button('Tải bảng truy vết JSON', json.dumps(trace,ensure_ascii=False,indent=2), cid+'_trace.json')

else:
    st.header('Chatbox theo hồ sơ '+cid)
    st.info('Gemini giải thích với căn cứ; không sửa dữ liệu hoặc xác nhận. Kiểm tra ngữ nghĩa câu trả lời với nguồn.')
    st.caption('Có thể hỏi: Vì sao hồ sơ bị cảnh báo? Chỉ số DTI dựa trên đầu vào nào? Cần bổ sung tài liệu gì?')
    consent = st.checkbox('Đồng ý gửi câu hỏi, ngữ cảnh hồ sơ giả lập và lịch sử gần đây đến Gemini.', key=prefix+'chat_consent')
    if st.button('Xóa lịch sử chat của phiên'):
        st.session_state.messages=[]
        st.rerun()
    for entry in st.session_state.messages:
        with st.chat_message('user'):
            st.text(entry['question'])
        with st.chat_message('assistant'):
            for row in entry['answer']:
                st.text(row['text'])
                st.caption('Căn cứ: '+', '.join(row['refs']))
            with st.expander('Dữ liệu tham chiếu lúc trả lời'):
                st.json(entry['references'])
    question = st.chat_input('Hỏi về hồ sơ đang mở…', disabled=not consent)
    if question:
        try:
            client = reserve_call()
            with st.spinner('Gemini đang giải thích…'):
                entry = chat(state, question, st.session_state.messages, client)
            st.session_state.messages = (st.session_state.messages+[entry])[-20:]
            st.rerun()
        except (ValueError, TypeError, KeyError) as exc:
            st.error(str(exc))

st.divider()
st.caption('Prototype học tập · Reviewer tự khai, chưa xác thực danh tính · Không dùng dữ liệu khách hàng thật · API có thể có chi phí/hạn mức')
