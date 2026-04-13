# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyen Thi Ngoc  - 2A202600405
**Vai trò trong nhóm:** Evaluation, Documentation Owner 
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab Day 08, mình đảm nhận vai trò **Documentation Owner**, tập trung vào việc chuẩn hóa kiến trúc hệ thống và xây dựng khung đánh giá kỹ thuật. Các đóng góp cụ thể của mình bao gồm:

- **Chủ trì xây dựng toàn bộ [architecture.md](file:///d:/ChuongTrinhHocTheoTungNgay/Day8_13Apr26/67Nop13Apr/Team67-Day-08-09-10-main/day08/lab/docs/architecture.md)**: Đây là tài liệu "xương sống" của dự án. Mình đã trực tiếp thiết kế và viết chi tiết các phần:
    - **Indexing Pipeline**: Chốt tham số chunking (size=400, overlap=80) và định nghĩa bộ metadata (department, effective_date...) để phục vụ lọc dữ liệu và trích dẫn.
    - **Retrieval & Generation Strategy**: Xây dựng bảng so sánh Baseline vs Variant, định nghĩa Grounded Prompt Template và quy tắc "Abstain policy" để chống hallucination.
    - **Failure Mode Checklist**: Thiết kế bảng tra cứu lỗi 5 tầng (Index/Chunk/Retrieve/Gen/Token) giúp team debug nhanh.
    - **Trực quan hóa**: Vẽ sơ đồ Mermaid mô tả luồng xử lý từ Query đến Citation.
- **Chủ trì soạn thảo toàn bộ [group_report.md](file:///d:/ChuongTrinhHocTheoTungNgay/Day8_13Apr26/67Nop13Apr/Team67-Day-08-09-10-main/day08/lab/reports/group_report.md)**: Mình chịu trách nhiệm chính trong việc "đúc kết" toàn bộ quá trình làm việc của nhóm vào một báo cáo thống nhất:
    - **Tổng hợp Team Contribution**: Phân loại và tóm tắt đóng góp của từng thành viên (Tech Lead, Retrieval Owners, Evaluation Owners) để làm nổi bật sự phối hợp trong pipeline.
    - **Đúc kết Shared Lessons**: Từ các quan sát riêng lẻ, mình đã tổng hợp thành 3 bài học kinh nghiệm cốt lõi của nhóm về Indexing, Rerank và Keyword matching.
    - **Xây dựng mục Future Improvements**: Dựa trên các failure modes (như q09, q06), mình đã đề xuất 4 hướng cải tiến cụ thể về data policy và tuning funnel cho các sprint tiếp theo.
    - **Đảm bảo tính nhất quán**: Đối chiếu số liệu giữa scorecard và nội dung phân tích để báo cáo có tính thuyết phục cao.
- **Phối hợp Evaluation**: Chạy scorecard và trace lỗi per-question (đặc biệt là q09/q06) để cung cấp dữ liệu đầu vào cho tài liệu kiến trúc.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, mình hiểu rõ hơn cách debug RAG theo cấu trúc "funnel" (phễu) mà mình đã mô tả trong tài liệu kiến trúc: **Indexing → Retrieval → Generation**. Việc xây dựng **Failure Mode Checklist** giúp mình nhận ra rằng mỗi tầng đều có rủi ro riêng: lỗi có thể đến từ việc chunking cắt sai "Ghi chú" quan trọng, hoặc do Reranker xáo trộn thứ tự các chunk đúng. 

Hệ thống chấm điểm 4 metrics (Faithfulness, Relevance, Recall, Completeness) thực chất là công cụ để mình trace ngược lại phễu này. Mình hiểu sâu sắc rằng một hệ thống RAG tốt không chỉ là có LLM mạnh, mà là sự phối hợp nhịp nhàng giữa chất lượng dữ liệu (indexing), chiến thuật lọc (retrieval) và khả năng tuân thủ ngữ cảnh (grounding). Đặc biệt, việc bật/tắt các tham số như `top_k_search` hay `rerank` cần được xem như các quyết định thiết kế kỹ thuật, không phải là việc tinh chỉnh ngẫu nhiên.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm mình ngạc nhiên nhất là việc thêm các cơ chế phức tạp như **Hybrid Search + Rerank + Query Expansion** vẫn có thể gây ra **regression** (giảm chất lượng) so với baseline đơn giản. Khi viết [tuning-log.md](file:///d:/ChuongTrinhHocTheoTungNgay/Day8_13Apr26/67Nop13Apr/Team67-Day-08-09-10-main/day08/lab/docs/tuning-log.md), mình thấy rất rõ trường hợp q09: dù đã dùng BM25 để bắt keyword nhưng Recall vẫn bằng 0. 

Khó khăn lớn nhất của mình là phải "mổ xẻ" nguyên nhân: do BM25 không khớp (mismatch) dữ liệu, hay do Reranker cho điểm quá đồng đều (~0.016) làm loãng thông tin. Bài học đắt giá nhất mình rút ra là phải duy trì tính kỷ luật trong tài liệu hóa (log lại từng thay đổi theo A/B rule). Nếu không có sự quan sát per-question, team rất dễ bị lạc vào vòng lặp "tinh chỉnh theo cảm tính" mà không hiểu thực sự tại sao hệ thống lại tệ đi khi mình cố làm nó tốt hơn.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q09 (ERR-403-AUTH / Insufficient Context)

**Phân tích:**

Trong [tuning-log.md](file:///d:/ChuongTrinhHocTheoTungNgay/Day8_13Apr26/67Nop13Apr/Team67-Day-08-09-10-main/day08/lab/docs/tuning-log.md), q09 là "failure mode" điển hình nhất với **Context Recall = 0/5** ở cả baseline và variant. Truy vấn chứa mã lỗi đặc thù "ERR-403-AUTH", nhưng dense retrieval hoàn toàn thất bại vì không tìm thấy sự tương đồng về ngữ nghĩa trong không gian vector.

Nhóm đã kỳ vọng variant **Hybrid (Dense + BM25)** sẽ giải quyết được nhờ khả năng bắt exact keyword của BM25. Tuy nhiên, kết quả vẫn là Recall = 0. Qua debug kỹ thuật, mình nhận ra nguyên nhân sâu xa là **"retrieval–data mismatch"**: trong tài liệu [access_control_sop.txt](file:///d:/ChuongTrinhHocTheoTungNgay/Day8_13Apr26/67Nop13Apr/Team67-Day-08-09-10-main/day08/lab/data/docs/access_control_sop.txt) chỉ chứa các cụm từ như "403 Forbidden" hoặc "Unauthorized", hoàn toàn thiếu chuỗi ký tự "ERR-403-AUTH". Do đó, BM25 không có "target" để khớp, còn Reranker thì đưa ra điểm số gần như đồng đều (uniform scores ~0.016) cho mọi candidate vì không có đoạn văn nào thực sự chứa bằng chứng.

Từ đây, mình rút ra bài học quan trọng: Khi đối mặt với mã lỗi hoặc thuật ngữ nội bộ, việc tinh chỉnh thuật toán retrieval (như thay đổi weights hay thêm rerank) sẽ vô ích nếu **corpus thiếu dữ liệu mapping**. Giải pháp đúng đắn phải là "fix bằng data" (bổ sung tài liệu tham chiếu mã lỗi) hoặc "fix bằng policy" (thiết lập rule-based để model chủ động abstain kèm hướng dẫn escalation khi gặp pattern mã lỗi mà không có evidence).

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Mình sẽ làm 2 việc cụ thể. (1) Theo A/B rule, chỉ đổi **một biến** trong funnel: tăng `top_k_search` (10 → 15) trước rerank để xem recall/completeness có cải thiện ổn định không. (2) Với failure mode kiểu q09, ưu tiên “fix bằng data”: bổ sung tài liệu tham chiếu mã lỗi (error code reference) hoặc quy ước trả lời (template abstain + hướng dẫn escalation) khi corpus không có evidence, để tránh hallucination trong grading.

