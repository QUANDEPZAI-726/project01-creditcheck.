"""Evidence links derived from current sources/rules; no LLM-generated evidence."""
import copy,hashlib,json
from core import ensure
from phase2 import source_evidence

def build(s):
    alerts=[];case=s['case'];docs={d['document_id']:d for d in case['documents']};p=s['phase2']
    raw=[dict(i,origin='source_crosscheck') for i in s['issues']]+[dict(f,origin='python_metrics') for f in p['flags']]
    for i,f in enumerate(raw):
        code=f['code'];ev=copy.deepcopy(f.get('evidence',[]));didset=f.get('source_ids',[])
        fields=[];txs=[];rule='Kiểm tra tính đầy đủ và nhất quán của nguồn.';inputs={}
        if code=='INCOME_MISMATCH':
            fields=['net_monthly_income_vnd'];rule='Chênh lệch tuyệt đối / thu nhập đối chiếu > 20% (ngưỡng giả lập).'
            if f['origin']=='python_metrics':inputs={'metrics':p['metrics'],'calculation_trace':p.get('calculation_trace'),'threshold_pct':p['config']['income_gap_threshold_pct']}
            else:inputs={'threshold_pct':20,'comparison':'Thu nhập trên đơn với giấy xác nhận; chưa xác minh lương sao kê.'}
        elif code=='BORROWER_ID_MISMATCH':
            fields=['borrower_id'];txs=case['transactions'];rule='Có hơn một mã người vay/chủ tài khoản khác nhau trong các nguồn.'
            inputs={'borrower_ids':{d['document_id']:d['fields'].get('borrower_id',{}).get('value') for d in docs.values() if d['source_type']!='bank_statement'},'account_holder_ids':sorted(set(t['account_holder_id'] for t in txs))}
        elif code=='CASE_ID_MISMATCH':fields=['case_id'];rule='Mã hồ sơ trong tài liệu không khớp mã hồ sơ đang mở.';inputs={'current_case_id':case['case_id']}
        elif code=='HIGH_DTI':
            rule='DTI=(nghĩa vụ nợ hiện tại + trả góp mới)/thu nhập đã xác minh × 100 > 40% (giả lập).'
            fields=['existing_monthly_debt_vnd','loan_principal_vnd','term_months','net_monthly_income_vnd']
            inputs={'metrics':p['metrics'],'calculation_trace':p.get('calculation_trace'),'config':p['config'],'income_review':p['income_review']}
        elif code=='AMBIGUOUS_INCOME':
            rule='Có giao dịch mang nhãn uncertain; cần con người bổ sung căn cứ trước khi xác minh.'
            ids=set(p.get('preview',{}).get('unresolved_transaction_ids',[]) if p.get('preview') else [])
            txs=[t for t in case['transactions'] if t['transaction_id'] in ids];inputs={'classification':p['classification']}
        elif code=='COVERAGE_UNVERIFIED':rule='Chưa có metadata kỳ sao kê đầy đủ; trạng thái cần người dùng kiểm tra.'
        elif code.startswith('MISSING'):rule='Thiếu tài liệu hoặc trường bắt buộc; không suy diễn giá trị còn thiếu.'
        selected=[docs[k] for k in didset if k in docs] if didset else list(docs.values())
        inputs['source_values']={d['document_id']:{key:d['fields'].get(key,{}).get('value') for key in fields} for d in selected if d['available'] and d['source_type']!='bank_statement'}
        for d in selected:
            for field in fields:
                ev.extend(copy.deepcopy(d['fields'].get(field,{}).get('evidence',[])))
        for t in txs:
            if code=='BORROWER_ID_MISMATCH':ev.append({'document_id':next(d['document_id'] for d in docs.values() if d['source_type']=='bank_statement'),'locator_type':'csv_account_holder_id','locator':t['transaction_id'],'quote':t['account_holder_id']})
            else:ev.extend(copy.deepcopy(t['evidence']))
        unique=[]
        for e in ev:
            if e not in unique:unique.append(e)
        links=[]
        for e in unique:
            src=s['sources'].get(e['document_id']);found=False;original=None
            if src:
                if src['role']=='bank_statement':
                    t=next((t for t in case['transactions'] if t['transaction_id']==e['locator']),None)
                    found=t is not None and e['quote'] in [t['description'],t['account_holder_id']];original=copy.deepcopy(t)
                else:
                    import re
                    m=re.search(r'page=(\d+)',e['locator']);page=int(m[1]) if m else 0
                    found=0<page<=len(src['pages']) and e['quote'] in src['pages'][page-1]
                links.append({**e,'source_sha256':src['sha256'],'quote_found_in_source':found,'source_available':True,'original_row':original,'download_endpoint':'api/source-file?document_id='+e['document_id']})
        # Absence is an intake finding, not an invented quotation from a missing file.
        if code.startswith('MISSING') or not links:
            for d in selected:
                src=s['sources'].get(d['document_id']);links.append({'document_id':d['document_id'],'locator_type':'intake_status','locator':'available='+str(d['available']).lower(),'quote':None,'source_sha256':src['sha256'] if src else None,'quote_found_in_source':None,'source_available':src is not None,'note':'Ghi nhận thiếu/metadata từ bước tiếp nhận; không có trích dẫn cho giá trị vắng mặt.','download_endpoint':'api/source-file?document_id='+d['document_id'] if src else None})
        aid='ALERT-'+hashlib.sha256(json.dumps({'case_id':case['case_id'],'origin':f['origin'],'code':code,'message':f['message'],'index':i},sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:12]
        alerts.append({'alert_id':aid,'code':code,'message':f['message'],'origin':f['origin'],'blocking':f.get('blocking'), 'rule':rule,'rule_inputs':inputs,'evidence':links,'trace_status':'SOURCE_LINKED' if links else 'NO_EVIDENCE_AVAILABLE'})
    return {'case_id':case['case_id'],'source_fingerprint':s['phase3']['context']['source_fingerprint'],'alerts':alerts,'scope':'Evidence links identify input used by a rule; no independent source authenticity or loan decision.'}

def sync(s):
    from phase3 import sync as sync3
    sync3(s);s['traceability']=build(s)
