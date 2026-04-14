# Báo Cáo Cá Nhân — Lab Day 09

**Họ và tên:** Nguyễn Việt Quang
**Vai trò:** Trace & Docs Owner
**Ngày nộp:** 14/04/2026

---

## 1. Phần tôi phụ trách

Đảm nhận vai trò **Trace & Docs Owner** trong Sprint 4, nhiệm vụ của tôi là biến những log chạy (Execution) thô của luồng Multi-Agent thành điểm số và tài liệu chuẩn xác. Cụ thể tôi đã làm:
- **Module `eval_trace.py`:** Tôi chịu trách nhiệm chạy, tùy chỉnh và debug toàn bộ file script này. Tôi đã tiến hành vá lỗi chạy file, config biến Day08 Baseline (`day08_baseline` mock data ở dòng 254) để hệ thống xuất ra được báo cáo chéo giữa 2 ngày `eval_report.json` và tệp JSONL dùng cho Grading.
- **Hoàn thiện Document:** Tôi tham gia phân tách mảng JSON để nhặt tay các trace logs, tạo báo cáo hoàn chỉnh cho kiến trúc (`system_architecture.md`) và đối chiếu so sánh (`single_vs_multi_comparison.md`). Nhờ đó, tính minh bạch về việc routing bằng keyword của code được diễn giải rõ ràng qua số liệu.

## 2. 1 Quyết định kỹ thuật: Chuẩn hóa Contract của mảng `mcp_tools_used` trong Evaluation Log

**Quyết định đề xuất:** Dưới vai trò Trace Owner, tôi có thẩm quyền về format log xuất ra của Pipeline. Tôi đã chốt cấu trúc Contract Data trả về tại hàm `run_grading_questions()` (trong file `eval_trace.py` dòng 128) để ép mảng `mcp_tools_used` chỉ lấy trường ID Tên Tool (Dạng chuỗi danh sách List[String] phẳng) thay vì lấy toàn bộ Object Input/Output phức tạp.
```python
"mcp_tools_used": [t.get("tool") for t in result.get("mcp_tools_used", [])]
```

**Lý do (Trade-off):** 
Việc chứa toàn bộ Output của Database hoặc String nội dung từ MCP Tool vào Trace Log của hàm Grading sẽ khiến dung lượng File JSONL phình to và rất khó đọc cho khâu chấm điểm. Tôi đánh đổi việc "giảm chi tiết Tool I/O ở log tổng" để lấy "Độ đọc gọn gàng, sạch sẽ". Khâu chi tiết của I/O tôi vẫn cho lưu đầy đủ ở File JSON riêng lẻ trong thư mục `artifacts/traces/`, không thất thoát dữ liệu.
**Bằng chứng từ trace:** Khi mở `grading_run.jsonl`, các câu query có tool (như gq09) xuất ra sạch sẽ: `"mcp_tools_used": ["search_kb", "get_ticket_info"]`, chính xác, dễ hiểu.

## 3. 1 Lỗi đã sửa: Mắc nghẽn `UnicodeDecodeError` khi chạy Script chấm điểm

**Mô tả lỗi:** 
Ở bước cuối cùng của Sprint 4, khi tôi chạy lệnh sinh log chấm thi: `python eval_trace.py --grading`, chương trình thường xuyên bị crash đứt gãy hệ thống với thông báo `UnicodeDecodeError: 'cp1252' codec can't decode byte ...` tại các lệnh `json.load`. Nguyên nhân là môi trường Terminal Windows mặc định ép giải mã bằng `cp1252`, trong khi nội dung câu trả lời có chứa emoji hoặc dấu ngoặc kép Tiếng Việt (UTF-8).

**Cách sửa và Bằng chứng khắc phục:**
Tôi trực tiếp tìm đến các dòng chứa lệnh `open()` trong `eval_trace.py` (dòng 40 hàm `run_test_questions`, dòng 102 hàm `run_grading_questions`, dòng 188 hàm `analyze_traces`) và ép cơ chế encoding:
```python
with open(questions_file, encoding="utf-8") as f:
```
**Bằng chứng Trước/Sau:**
- *Trước:* Terminal văng Exception lỗi, tệp ` grading_run.jsonl` mới được in lỡ cỡ 2 câu thì bị hủy, khiến điểm rớt về 0.
- *Sau khắc phục:* Tệp `artifacts/grading_run.jsonl` được viết trơn tru đầy đủ 10 dòng JSONL liền mạch, in đầy đủ các ký tự tiếng Việt với `latency_ms` cho từng câu rõ ràng mà không bị văng tiến trình.

## 4. Tự đánh giá điểm mạnh / yếu

- **Làm tốt gì:** Quản lý tốt rủi ro của khâu "chuyển giao và xuất báo cáo" cuối cùng. Chạy hệ thống đo mét khối Metrics xuất sắc. Không để JSON file bị lỗi định dạng. Documentation viết chi tiết với dẫn chứng trực tiếp từ từng dòng run log một.
- **Làm chưa tốt gì (Yếu):** Tôi không nắm chắc thiết kế LLM Prompt bên trong nhánh `synthesis_worker` cũng như ít thao tác tạo Schema cho MCP Tool, khiến hiểu biết về việc Vector Embedding mới chỉ ở mức nhìn số liệu trả ra.
- **Sự phụ thuộc của nhóm:** Team phụ thuộc rất lớn vào kỹ năng chạy Tool gỡ rối hệ điều hành Windows của tôi, vì khi vấp file JSON không build, cả nhóm cũng không thể Submit bài thực hành được.

## 5. 1 Cải tiến cụ thể nếu có 2h thêm

Từ việc quan sát trace file nội bộ như `artifacts/traces/run_20260414_172152.json`, tôi thấy Node Supervisor vẫn đang định tuyến (route) một số câu hỏi có nội dung chính sách vào luồng `default route` chỉ vì câu lệnh chưa gõ đúng các Keyword tĩnh (hard-code).
**Cải tiến:** Nếu có 2 tiếng, tôi sẽ đập bỏ mảng Array Regex ở file `graph.py` và cấu hình LLM OpenAI tích hợp API "Structured Output JSON Schema" vào Node Supervisor. LLM đóng vai trò Intent Classifier độc lập để chọn luồng (`route: policy_tool` hay `retrieval`) một cách thông minh với ngữ nghĩa con người hơn. Việc tốn một ít chi phí Token là đáng để đổi lấy bộ định tuyến với tỷ lệ Miss-Routing bằng 0%.
