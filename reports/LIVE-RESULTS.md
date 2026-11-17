# Kết quả chạy Gemini thật — Day 9

Ngày kiểm tra: 17/11/2026, Asia/Bangkok. Model: `gemini-3.1-flash-lite`.

**Kết quả: 6/6 demo thực tế, 4/4 kiểm tra A2A thực tế và 61/61 test hồi quy offline đạt.**

Các script live dùng API Google thật bằng key người dùng cung cấp; không chèn model fixture. Provider Gemini trực tiếp được dùng theo yêu cầu của người dùng, thay cho OpenRouter trong codelab gốc.

| Demo | Trạng thái | Thời gian thực thi quan sát | Output |
| --- | --- | --- | --- |
| stage1 | PASS | 5.103 giây | [Output](live-outputs/stage1.txt) |
| stage2 | PASS | 6.596 giây | [Output](live-outputs/stage2.txt) |
| exercise2 | PASS | 10.351 giây | [Output](live-outputs/exercise2.txt) |
| stage3 | PASS | 7.417 giây | [Output](live-outputs/stage3.txt) |
| stage4 | PASS | 34.689 giây | [Output](live-outputs/stage4.txt) |
| exercise4 | PASS | 29.444 giây | [Output](live-outputs/exercise4.txt) |

| Kiểm tra A2A | Trạng thái |
| --- | --- |
| full_chain | PASS |
| tax_shutdown | PASS |
| dynamic_rediscovery | PASS |
| shorter_tax_prompt | PASS |

Cùng câu hỏi Tax: prompt gốc trả **690 từ**, prompt đã sửa trả **145 từ**, **4 bullet**. Đây là kết quả phiên đã chạy, không bảo đảm mọi câu hỏi đều có cùng độ dài.

Luồng đầy đủ giữ trace/context: Customer depth 0, Law depth 1, Tax và Compliance depth 2. Đã dừng Tax, nhận phần trả lời còn lại, rồi đăng ký Tax tại cổng mới và xác minh request kế tiếp tìm được endpoint mới.

Khi chạy thật, đã phát hiện và sửa adapter làm mất `thought_signature` ở lượt tool-result. Adapter giữ nguyên metadata Google trả về; test hồi quy kiểm tra cả hai lượt request.

Bằng chứng:

- [Kết nối API thật](gemini-connection.json).
- [Các entry point thật](live-codelab.json).
- [Trace, shutdown/recovery và so sánh prompt thật](live-a2a.json).
- [Tổng hợp trạng thái](validation-summary.json).
- [61 test offline](test-output.txt): file `verification.json` chỉ mô tả lượt hồi quy offline, không thay thế báo cáo live.

Bộ test do bài làm bổ sung, không phải bộ chấm chính thức. Các kiểm tra xác minh hành vi chương trình, chưa phải đánh giá độ chính xác pháp luật bằng ground truth. Key chỉ lưu trong `.env` local và bị loại khỏi Git/ZIP.
