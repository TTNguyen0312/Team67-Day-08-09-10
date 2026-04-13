# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyen Thi Ngoc  
**Vai trò trong nhóm:** Documentation Owner (hỗ trợ Eval)  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab Day 08, mình tập trung vào **tài liệu hoá + tổng hợp bằng chứng đánh giá** để nhóm giải thích được “vì sao đúng/sai” (không chỉ demo chạy được). Các việc mình làm gắn trực tiếp với artifact trong repo:

- Hoàn thiện `docs/architecture.md`: mô tả kiến trúc end-to-end và chốt quyết định chunking (chunk_size=400, overlap=80) + baseline/variant.
- Duy trì `docs/tuning-log.md`: ghi giả thuyết từ các câu yếu (q09/q06), config variant, và trade-off theo từng câu để team chốt hướng tune tiếp.
- Tổng hợp `reports/group_report.md`: gom ý từ báo cáo cá nhân thành “team contribution” và “shared lessons”.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, mình hiểu rõ hơn cách debug RAG theo “3 tầng”: **indexing → retrieval → generation** thay vì chỉ nhìn câu trả lời cuối. Scorecard buộc mình tách vấn đề thành 4 metric: **Context Recall** (retrieve đúng evidence?), **Faithfulness** (có bịa ngoài evidence?), **Answer Relevance** (trả lời đúng trọng tâm?), và **Completeness** (đủ điều kiện/ngoại lệ?). Mình nhận ra một hệ có thể grounded nhưng vẫn thiếu ý nếu top-k quá ít; ngược lại, retrieve sai thì prompt hay cũng không cứu được. Vì vậy các tham số “funnel” như top_k_search/top_k_select và việc bật rerank cần được xem như quyết định thiết kế, không phải tinh chỉnh phụ.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm mình ngạc nhiên là thay đổi “nghe có vẻ đúng” vẫn có thể gây **regression**. Nhóm bật retrieval stack (hybrid + rerank + query expansion) để bắt keyword/mã lỗi tốt hơn, nhưng tuning-log ghi nhận metric tổng thể giảm và đặc biệt **q09 (ERR-403-AUTH) vẫn Recall=0**. Khó nhất là truy ngược nguyên nhân: có thể do BM25 không match vì corpus không có chuỗi/mapping mã lỗi, reranker cho điểm gần như đồng đều nên không cải thiện ranking, hoặc query expansion tạo nhiễu làm lệch top-k. Bài học của mình là phải ghi lại quan sát theo từng câu (per-question) và giữ A/B rule, nếu không rất dễ “tuning theo cảm giác”.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q09 (ERR-403-AUTH / Insufficient Context)

**Phân tích:**

Trong `docs/tuning-log.md` của nhóm, q09 là câu yếu nhất của baseline vì **Context Recall = 0/5**: truy vấn chứa mã lỗi “ERR-403-AUTH” nhưng dense retrieval không mang về đúng evidence (thường chỉ ra các đoạn access-control chung chung). Khi thiếu evidence, baseline chỉ có hai lựa chọn: **abstain** (an toàn) hoặc trả lời theo “model knowledge” (dễ bị coi là hallucination nếu không có trích dẫn).

Nhóm kỳ vọng variant “hybrid + rerank” sẽ cải thiện vì BM25 bắt exact keyword, còn rerank đẩy chunk đúng lên top. Tuy nhiên tuning-log ghi nhận variant vẫn **không fix được q09** (recall vẫn 0) và reranker cho điểm gần như đồng đều giữa các candidate, nên không thực sự thay đổi chất lượng evidence. Mình rút ra đây là “retrieval–data mismatch”: nếu corpus không chứa mapping/định nghĩa cho mã lỗi nội bộ, thì đổi strategy/weights chỉ giúp rất ít. Trong trường hợp này, abstain rõ ràng vẫn là lựa chọn đúng để tránh bị phạt hallucination, nhưng về lâu dài cần “fix bằng data” (bổ sung tài liệu tham chiếu mã lỗi) hoặc “fix bằng policy” (rule-based: gặp pattern mã lỗi mà không có evidence thì trả lời theo template + hướng dẫn escalation).

Nếu có thêm thời gian, mình sẽ giữ A/B rule và thử một bước nhỏ: tăng `top_k_search` trước rerank để tăng cơ hội bắt đúng term; nếu vẫn không cải thiện, kết luận chính xác là “thiếu dữ liệu” thay vì tiếp tục tuning tham số.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Mình sẽ làm 2 việc cụ thể. (1) Theo A/B rule, chỉ đổi **một biến** trong funnel: tăng `top_k_search` (10 → 15) trước rerank để xem recall/completeness có cải thiện ổn định không. (2) Với failure mode kiểu q09, ưu tiên “fix bằng data”: bổ sung tài liệu tham chiếu mã lỗi (error code reference) hoặc quy ước trả lời (template abstain + hướng dẫn escalation) khi corpus không có evidence, để tránh hallucination trong grading.

