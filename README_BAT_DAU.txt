PROJECT 01 — CREDITCHECK GEMINI v0.5
Đọc tệp này trước khi đưa mã lên GitHub.

ĐÃ LÀM
- Giao diện Streamlit, giữ tám bước nghiệp vụ và thêm trang chatbox hồ sơ.
- Ba nút gọi Gemini thật qua SDK google-genai: trích xuất, phân loại, báo cáo.
- Kiểm tra đầu ra bằng các bộ kiểm tra Python cũ; lỗi giữ dữ liệu cũ.
- Ba checkpoint con người, căn cứ nguồn, trạng thái thiếu/ cần rà soát, nhật ký và xuất ZIP/TXT/JSON.
- Hồ sơ và chat riêng theo st.session_state, không dùng máy chủ STATE chung cũ.
- Năm mẫu giả lập, HS01 đã kiểm tra là kết quả lưu từ v0.4, không phải đầu ra Gemini mới.
- Mã truy cập demo cho phần API, giới hạn số lượt và độ dài; khóa giữ phía máy chủ.

CHƯA XÁC NHẬN
Chưa gọi Gemini bằng khóa thật của nhóm. Kiểm thử API sử dụng phản hồi mô phỏng và không đo độ chính xác Gemini.
Chưa triển khai vào tài khoản GitHub/Streamlit của nhóm, nên chưa có link mới.
Đã có kiểm thử bằng framework Streamlit, chưa kiểm thử toàn bộ giao diện trong trình duyệt thật.
Không có cơ sở dữ liệu theo tài khoản; dữ liệu phiên có thể mất khi tải lại/đóng tab hoặc máy chủ khởi động lại. Tải ZIP trước.
Không hỗ trợ OCR. Reviewer tự khai. Kiểm tra quote/refs không bảo đảm diễn giải đúng hoặc tài liệu thật.
Ngưỡng và lãi suất là giả định học tập; không quyết định vay. PDF báo cáo chưa thêm, giữ TXT/JSON/ZIP.

CÁCH LẤY LINK — LÀM MỘT LẦN, KHÔNG CẦN COLAB

1. Giải nén Project01_CreditCheck_Gemini_v05.zip trên máy.
Mở thư mục: phải thấy streamlit_app.py, requirements.txt và các thư mục app, runtime, seed, incoming, tests.

2. Tạo repository GitHub, ví dụ project01-creditcheck.
Đăng nhập GitHub, chọn New repository, nhập tên rồi Create repository. Không tải khóa lên GitHub.
Chọn Add file > Upload files. Tải NỘI DUNG thư mục giải nén lên: streamlit_app.py nằm ở gốc repository, không nằm trong một thư mục bọc bên ngoài.
Giữ nguyên cấu trúc app/runtime/seed/incoming/tests. Không upload __pycache__, secrets.toml, tệp dữ liệu thật.
Tệp .streamlit/secrets.example.toml chỉ chứa giá trị mẫu, không có khóa thật. Có thể không upload tệp này; nhập cấu hình ở bước 4.
Commit changes. Nếu giao diện GitHub không nhận cả thư mục, kéo các thư mục cùng các tệp vào vùng upload.

3. Mở https://share.streamlit.io/ và đăng nhập/kết nối GitHub.
Chọn Create app, chọn repository vừa tạo, branch main và Main file path: streamlit_app.py.
Nếu chọn Python version, dùng Python 3.12. Thư viện được cài từ requirements.txt.

4. Advanced settings > Secrets: nhập cấu hình sau.
GEMINI_API_KEY = "KHÓA_THẬT_CỦA_BẠN"
GEMINI_MODEL = "gemini-flash-latest"
DEMO_ACCESS_CODE = "MÃ_RIÊNG_BẠN_TỰ_ĐẶT_CHO_NHÓM"

Thay ba giá trị, giữ dấu nháy. Không đưa khóa thật vào README, GitHub hoặc hội thoại ChatGPT.
Model alias trên là giá trị khởi đầu theo SDK; nếu tài khoản không hỗ trợ, thay GEMINI_MODEL bằng model Gemini hỗ trợ generateContent + JSON hiện có quyền dùng trong AI Studio.
Được hướng dẫn tạo khóa không bảo đảm khóa còn hiệu lực hoặc có hạn mức. Xác nhận ở lần chạy thật.
Mã demo do bạn tự đặt và chỉ chia cho người được phép dùng API. Nó không phải khóa Gemini; không chia khóa Gemini cho người xem.

5. Bấm Deploy, chờ cài đặt và mở ứng dụng.
Khi thành công, Streamlit cung cấp URL thực tế. Lưu URL đó để mở lần sau; không cần chạy notebook.
Ứng dụng có thể ngủ/khởi động chậm sau thời gian không dùng. Không cam kết link hoạt động tức thì mọi lúc.
Nếu triển khai lỗi, xem log; gửi ảnh lỗi đã che khóa, không gửi Secrets.

CHẠY THẬT HS01 SAU KHI DEPLOY
1. Nhập mã truy cập demo ở thanh bên, bấm Mở quyền chạy API.
2. Tab 1: Mở hồ sơ mẫu HS01 (bắt đầu mới).
3. Tab 3: tích đồng ý gửi dữ liệu giả lập, bấm Chạy Gemini trích xuất.
4. Tab 2: mở và đối chiếu thông tin với nguồn.
5. Tab 4: điền tên, ghi chú; tích đã đối chiếu; xác nhận trích xuất.
6. Tab 5: tích đồng ý, chạy Gemini phân loại. Kiểm tra đủ chín giao dịch, nhãn và lý do.
7. Nhập kỳ 2026-07-01 đến 2026-09-30; tên, ghi chú; tích kiểm tra nhãn/kỳ. Xác minh thu nhập.
8. Tab 6: kiểm tra thu nhập 20 triệu, khoản vay 100 triệu/24 tháng, giả định 12%/năm; PMT khoảng 4.707.347 VND, DTI 33,54%, lệch 0% nếu nguồn và phân loại đúng.
9. Tab 7: đồng ý gửi dữ liệu; chạy Gemini tạo báo cáo; đọc và đối chiếu; điền tên, ghi chú, hai xác nhận. Tải báo cáo.
10. Tab 9: đồng ý gửi ngữ cảnh; hỏi "DTI của HS01 dựa trên những đầu vào nào?" hoặc "Còn điều gì cần con người xác minh?". Mở tham chiếu của câu trả lời.
11. Tải ZIP để lưu minh chứng; không ghi mọi cuộc gọi Gemini luôn thành công. Đầu ra sai có thể bị chặn và cần chạy lại.
Chờ ít nhất năm giây giữa hai lượt. Giới hạn demo 30 lượt/phiên, 60 lượt/giờ/máy chủ; không thay thế giới hạn ngân sách tại nhà cung cấp và có thể reset khi máy chủ khởi động lại.

XEM KẾT QUẢ KHI CHƯA CÓ API
Tab 1: Khôi phục HS01 đã kiểm tra. Xem tab 5/6/7/8. Ghi rõ đây là kết quả ChatGPT đã lưu trước đó, không phải Gemini vừa chạy.
Mở HS02/HS03/HS04 để thấy thiếu sao kê/lệch thu nhập/sai chủ tài khoản. Đổi hồ sơ xóa chat.
HS05 cần phân loại để hiện cảnh báo giao dịch uncertain. Không tự đổi nhãn nhằm xóa cảnh báo.

CHẠY TẠI MÁY NẾU CẦN
Python 3.12, mở terminal trong thư mục dự án:
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
Nếu cần API tại máy: tạo .streamlit/secrets.toml theo ví dụ, tuyệt đối không commit tệp thật.

KIỂM THỬ
python -m unittest discover -s tests -v
test_results.txt ghi kết quả kiểm thử đã chạy. Test dùng fixture/FakeClient; không phải accuracy AI.
Giữ đáp án chuẩn của bộ dữ liệu ở ngoài runtime ứng dụng để đánh giá riêng.

VAI TRÒ KHI TRÌNH BÀY
LLM: đọc/trích xuất, đề xuất phân loại, viết báo cáo, trả lời theo nguồn.
Python: đọc CSV/PDF mẫu, kiểm tra cấu trúc/căn cứ, tính PMT/DTI/độ lệch, kiểm tra báo cáo khớp dữ liệu, quản lý trạng thái.
Con người: đối chiếu nguồn, xác minh thu nhập/kỳ sao kê, rà soát báo cáo và câu trả lời.
API trực tiếp không có nghĩa nguồn đã được xác minh hoặc khoản vay được duyệt.

TÀI LIỆU KỸ THUẬT THAM KHẢO
https://googleapis.github.io/python-genai/
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
