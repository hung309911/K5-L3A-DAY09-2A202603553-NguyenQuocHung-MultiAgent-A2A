# Bài làm Day 9 — Multi-Agent / A2A

Đọc [BAO-CAO.md](BAO-CAO.md) để xem đáp án từng bài; [SOURCE.md](SOURCE.md) ghi nguồn đề và phần kế thừa. Đã triển khai Stage 1–5/hai exercise và xác minh bằng Gemini thật: 6 demo, 4 kiểm tra A2A đạt. Chi tiết: [reports/LIVE-RESULTS.md](reports/LIVE-RESULTS.md). Các test offline do bài làm bổ sung, không phải bộ chấm chính thức.

`CODELAB.md` giữ nguyên nội dung nguồn. Hai lỗi trong hướng dẫn gốc được xử lý ở code và cách chạy bên dưới: API nhận `debug=True` thay cho `verbose=True`; đường dẫn Stage 4 là `stage_4_multi_agent` thay cho `stage_4_milti_agent`.

## Kiểm tra ngay trên máy hiện tại

Mở PowerShell tại thư mục này:

```powershell
.\.venv\Scripts\python.exe scripts\check_assignment.py
```

Không cần API key cho lệnh kiểm tra. Bộ test chạy model giả lập trong `tests/`, đồng thời khởi động 5 tiến trình HTTP thật bằng A2A SDK. Kết quả dùng để xác minh routing, tools, ghép kết quả, trace và lỗi dịch vụ. Kết quả hiện tại: **61 passed**.

Bằng chứng được sinh lại tại:

- `reports/test-output.txt` — output pytest.
- `reports/test-results.xml` — kết quả từng test.
- `reports/verification.json` — lệnh, phiên bản, thời điểm và phạm vi kiểm tra.
- `reports/a2a-evidence.json` — trace xuyên 4 agent, câu trả lời fixture, tình huống Tax Agent dừng và đăng ký lại ở cổng mới.

Logs tạm nằm tại `.qa/http/`; các service test được dừng khi kết thúc. Test dùng cổng trống để không chiếm cổng demo mặc định.

## Cài mới

Python 3.11–3.13; đã kiểm tra bằng Python 3.13.17 trên Windows. Không dùng Python 3.15 mặc định của máy này.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts\check_assignment.py
```

Nếu không có launcher `py`, thay dòng đầu bằng đường dẫn Python 3.13. Trên máy hiện tại Python này nằm tại `C:\Users\new\AppData\Local\Python\pythoncore-3.13-64\python.exe`.

`requirements-dev.txt` tự áp dụng `constraints.txt`. Bộ LangGraph 0.6.6 / LangChain Core 0.3.72 / LangChain OpenAI 0.3.28 / LangSmith 0.3.45 tránh DLL `uuid-utils` bị Windows Application Control chặn. Không cần thay đổi chính sách bảo mật Windows.

Nếu dùng uv: `uv sync --locked`, sau đó `uv run python scripts/check_assignment.py`. `uv.lock` là lock của bản bài làm; `constraints.txt` là bộ phiên bản đã chạy trên Windows cho cách cài pip.

## Chạy với LLM thật

### Dùng Gemini theo yêu cầu của bạn

Đã thêm kết nối Gemini trực tiếp qua OpenAI-compatible API của Google, dùng cùng `ChatOpenAI`, LangGraph và A2A. Đây là thay đổi provider so với OpenRouter trong codelab, được bổ sung theo yêu cầu của bạn; file đề gốc giữ nguyên.

File `.env` local đã được cấu hình bằng key người dùng cung cấp. Ví dụ dưới đây ẩn giá trị key:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
REGISTRY_URL=http://127.0.0.1:10000
```

Key Google chỉ gửi tới `generativelanguage.googleapis.com`; cũng hỗ trợ tên biến `GOOGLE_API_KEY`. `LLM_PROVIDER` chọn provider rõ ràng; nếu không đặt thì tự chọn Gemini khi chỉ có key Google. Trên máy hiện tại đã gọi Gemini thật thành công. ZIP không chứa credential, nên khi chuyển sang máy khác cần tự điền key vào `.env`.

Các lệnh chạy stage và service bên dưới dùng được với cả hai provider. Adapter Gemini giữ nguyên `thought_signature` trong các lượt tool calling. Bộ test offline không gọi provider; các script live dưới đây có gọi Google API và có thể phát sinh usage:

```powershell
.\.venv\Scripts\python.exe scripts\check_gemini_connection.py
.\.venv\Scripts\python.exe scripts\verify_live_codelab.py
.\.venv\Scripts\python.exe scripts\verify_live_a2a.py
```

`verify_live_codelab.py --resume` giữ các phần đã đạt trong phiên trước để tiếp tục phần còn lại. Bằng chứng live nằm trong `reports/live-*.json`, `reports/live-outputs/`; logs A2A tạm trong `.qa/live-a2a/`.

### Dùng OpenRouter theo provider gốc của codelab

```powershell
Copy-Item .env.example .env
notepad .env
```

Điền `OPENROUTER_API_KEY` của bạn và chọn `OPENROUTER_MODEL` có hỗ trợ tool calling. Key chỉ nằm trong `.env`, không đưa vào ZIP hoặc Git. Các script demo gọi `load_dotenv()`; `get_llm()` báo rõ khi key thiếu hoặc còn giá trị mẫu. Không tự chuyển sang fixture khi thiếu key.

Đặt `LLM_PROVIDER=openrouter` khi chọn cách này.

Chạy từng phần:

```powershell
.\.venv\Scripts\python.exe stages\stage_1_direct_llm\main.py
.\.venv\Scripts\python.exe stages\stage_2_rag_tools\main.py
.\.venv\Scripts\python.exe exercises\exercise_2_tools.py
.\.venv\Scripts\python.exe stages\stage_3_single_agent\main.py
.\.venv\Scripts\python.exe stages\stage_4_multi_agent\main.py
.\.venv\Scripts\python.exe exercises\exercise_4_multiagent.py
```

Chạy hệ thống phân tán ở terminal thứ nhất:

```powershell
.\.venv\Scripts\python.exe scripts\run_services.py
```

Hoặc `powershell -File .\start_all.ps1`. Launcher chờ từng service sẵn sàng, lưu logs vào `.qa/services/`, và dọn các tiến trình con khi bấm Ctrl+C. Nếu cổng đang được dùng, launcher báo lỗi trước khi chạy.

Gửi câu hỏi từ terminal thứ hai:

```powershell
.\.venv\Scripts\python.exe test_client.py --trace-id demo-day9 --question "If a company breaks a contract, avoids taxes and violates SEC compliance, what are the consequences?"
```

| Dịch vụ | Cổng mặc định | Vai trò |
| --- | --- | --- |
| Registry | 10000 | Register / discover endpoint theo task |
| Customer | 10100 | Nhận câu hỏi, gọi Law qua tool |
| Law | 10101 | Phân tích, route và tổng hợp |
| Tax | 10102 | Chuyên gia thuế |
| Compliance | 10103 | Chuyên gia tuân thủ |

Agent Card: `http://127.0.0.1:<port>/.well-known/agent-card.json`. Client có fallback sang `/.well-known/agent.json` khi server cũ trả 404. Endpoint giữa các agent được tra trong Registry khi gọi.

## Demo từng yêu cầu Stage 5

1. **5.1 — Trace:** gửi request có `--trace-id demo-day9`; tìm `demo-day9` trong `.qa/services/*.log`. Customer có depth 0, Law 1, Tax và Compliance 2. `context_id` giữ nguyên; `task_id` khác nhau giữa service.
2. **5.2 — Tax Agent dừng:** chạy test `python -m pytest -q tests/test_http_integration.py`. Test chủ động dừng riêng Tax Agent, kiểm tra phản hồi thiếu Tax nhưng giữ Compliance, rồi đăng ký Tax ở cổng mới và gửi lại. Registry lưu bản đăng ký cũ khi process chết; không có health eviction tự động. Đây là điểm phân biệt discovery với kiểm tra liveness.
3. **5.3 — Prompt:** `tax_agent/graph.py` có giới hạn dưới 150 từ, tối đa 4 bullet và yêu cầu nêu dữ kiện còn thiếu. Phiên Gemini thật đã quan sát prompt gốc 690 từ → prompt sửa 145 từ/4 bullet. Khi chạy thủ công, khởi động lại Tax sau khi sửa prompt; số từ có thể thay đổi ở các lần gọi khác.

## Đóng gói

```powershell
.\.venv\Scripts\python.exe scripts\package_submission.py
```

Tạo `DAY9-MULTI-AGENT-A2A-BAI-LAM.zip` ở thư mục cha. Gói chứa source, báo cáo và bằng chứng; loại `.env`, `.venv`, `.git`, cache và logs tạm. `Lab_Assignment/` là bài RAG ngày 8 trong bản nguồn, được loại khỏi gói theo phạm vi bạn xác nhận.

Các challenge memory/auth/retry/monitoring nằm trong mục tự học tùy chọn của đề. Bài làm tập trung toàn bộ yêu cầu chính 1.1–5.3; không tuyên bố đã triển khai những challenge đó. Tên repo có MCP, nhưng codelab truy cập được không yêu cầu viết MCP server; phần phân biệt MCP/A2A được giải thích trong báo cáo.
