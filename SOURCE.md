# Nguồn và phạm vi bài làm

Ngày đối chiếu: **17/11/2026**, múi giờ Asia/Bangkok.

- Link người dùng cung cấp: <https://github.com/VinUni-AI20k/Batch02-Day9_Multi-Agent_MCP-A2A.git>. GitHub connector, web và Git đều báo không tìm thấy tại thời điểm đọc.
- Bản công khai dùng làm cơ sở: <https://github.com/HTChieens/Batch02-Day9_Multi-Agent_MCP-A2A>.
- Commit cơ sở: `02d5af54b5b13cd77d64e85212b3c64de60d9513`.
- Đây là repo công khai cùng tên (`fork: false` theo metadata GitHub), không khẳng định là fork chính thức hoặc đồng nhất với phiên bản mới nhất của repo gốc.
- Người dùng đã xác nhận: **“Làm toàn bộ codelab Multi-Agent/A2A ngày 9”**. Vì vậy căn cứ thực hiện là `CODELAB.md` và `exercises/README.md`; không thực hiện `Lab_Assignment/README.md` vốn ghi Ngày 8 — RAG.

## Phần kế thừa và phần hoàn thiện

Bản công khai đã có sẵn nhiều đáp án: temperature 0.3, câu hỏi tiếng Việt ở Stage 1, entry lao động, tool thời hiệu, `search_case_law`, Privacy Agent trong Stage 4 và bài exercise. Bài làm giữ và ghi nhận các phần này; không nhận đó là phần được viết mới hoàn toàn.

Phần hoàn thiện trong lượt làm này:

- Sửa router exercise 4: trả `Send` từ conditional edge thay vì đưa hàm trả list vào một node cập nhật state.
- Sửa tìm kiếm cụm nhiều từ tiếng Việt ở Stage 2.
- Chuẩn hóa đường dẫn Stage 4 bị viết sai `milti` thành `multi` trong source; ghi cách chạy tại `HUONG-DAN.md` và giữ nguyên file đề `CODELAB.md` để đối chiếu.
- Bật debug đúng API ở Stage 3; thay câu hỏi demo bằng câu hỏi phù hợp kho án lệ mẫu.
- Cho phép `get_llm(temperature=...)`, kiểm tra key, timeout và số lần retry của client LLM.
- Rút gọn prompt Tax Agent theo bài 5.3.
- Cập nhật đường dẫn Agent Card; kiểm tra lỗi A2A và task thất bại; không dùng câu hỏi trong history làm câu trả lời.
- Kiểm tra JSON routing phải chứa boolean thực; chặn quá độ sâu ở delegation helper và Customer.
- Cho phép cấu hình cổng service để kiểm thử HTTP độc lập.
- Thay launcher Windows phụ thuộc đường dẫn uv cố định và biến `$pid` thành launcher Python có kiểm tra readiness và dọn process.
- Thêm 61 test, harness 5 process thật với model fixture, báo cáo, hướng dẫn và script đóng gói.
- Khóa lại dependency theo bộ chạy được trên Windows hiện tại.
- Rà soát tiếp theo: bỏ fallback LLM trong router Stage 4 để đúng điều kiện từ khóa bài 4.2; thêm test hồi quy và làm rõ trạng thái demo LLM thật chưa xác minh.
- Theo yêu cầu tiếp theo của người dùng, bổ sung Gemini trực tiếp bằng key Google; giữ lựa chọn OpenRouter theo codelab. Người dùng đã cung cấp key mới, lưu tại `.env` local và không đưa vào source/ZIP.
- Xác minh Gemini thật: HTTP 200; 6 entry point đạt; 4 kiểm tra A2A đạt, gồm Tax shutdown/rediscovery và so sánh prompt gốc 690 từ → prompt sửa 145 từ. Sửa adapter để giữ `extra_content.google.thought_signature` qua các lượt tool calling của Gemini.

## Tài liệu kỹ thuật dùng đối chiếu

- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api): node cập nhật state, conditional edge quyết định đích, `Send` dùng cho fan-out.
- [A2A specification](https://a2a-protocol.org/latest/specification/): Message, Task, Artifact và discovery. Code ở đây giữ API của `a2a-sdk==0.3.26`; không tuyên bố đã chuyển toàn bộ lên phiên bản protocol mới nhất.
- API Python thực tế được đối chiếu thêm với source thư viện đã cài trong `.venv`.
- [Google OpenAI compatibility](https://aistudio.google.com/docs/openai) và [Gemini 3.1 Flash-Lite](https://aistudio.google.com/docs/models/gemini-3.1-flash-lite): endpoint tương thích OpenAI, tên model và khả năng function calling cho lựa chọn Gemini trực tiếp được người dùng yêu cầu.

## Giới hạn bằng chứng

Model fixture nằm trong `tests/fake_llm.py`, được chèn vào process bằng `tests/service_runner.py`. Source chạy thật không import model này. HTTP, Registry, LangGraph và A2A SDK chạy thật; nội dung LLM là câu cố định có nhãn `[FIXTURE:...]`.

Ngoài bộ test fixture còn có phiên Gemini thật độc lập: `scripts/verify_live_codelab.py` chạy file demo thực tế; `scripts/verify_live_a2a.py` dùng process manager chung nhưng khởi động trực tiếp `python -m <service>`, không dùng bootstrap giả lập. Output và trace nằm trong `reports/live-*`.

Các kiểm tra thật chứng minh luồng thực thi, tool calling, routing, trace, lỗi dịch vụ và độ ngắn của phản hồi trong phiên đã chạy. Không báo cáo đó là đánh giá tính đúng pháp luật, chi phí đầy đủ hoặc bảo đảm model luôn giữ giới hạn số từ. Các con số pháp luật trong knowledge base là dữ liệu mẫu kế thừa của codelab, không phải kho văn bản pháp luật hiện hành đã được thẩm định.
