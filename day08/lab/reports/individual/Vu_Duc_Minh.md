# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Vũ Đức Minh
**Mã học viên** 2A202600459
**Lớp** E403
**Vai trò trong nhóm:** Documentation Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

Tôi là **Documentation Owner** của nhóm, chủ yếu làm việc trong Sprint 4. Nhiệm vụ chính của tôi là:

1. **Chịu trách nhiệm tài liệu Pipeline**: Duy trì tuning-log.md ghi lại chi tiết mỗi thay đổi config, giả thuyết, kết quả eval.
2. **Phân tích Error Tree**: Ghi lại nguyên nhân sâu của từng lỗi (indexing/retrieval/generation) từ scorecard để hướng dẫn Sprint tiếp theo.
3. **Tổng hợp Scorecard**: So sánh baseline (Sprint 2: dense) vs Variant 1 (Sprint 3: hybrid+rerank) để xác định variant nào tốt hơn.
4. **Kết nối giữa các Sprint**: Kiểm tra kết quả mỗi sprint để sprint sau không phải làm lại, tạo tính liên tục.


---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

**Evaluation Loop & Error Analysis:** Trước đây tôi chỉ nhìn accuracy chung, nhưng qua lab này tôi hiểu phải **phân tích per-question** để tìm pattern. Ví dụ: q09 (ERR-403-AUTH) Recall=0 ở cả baseline và variant cho dù variant dùng hybrid search - đây là proof rằng lỗi không phải retrieval strategy mà **vấn đề semantic matching với error code exact**. Điều này khiến tôi nhận ra đánh giá chất lượng phải combine metric định lượng (Recall, Faithfulness) + định tính (xem error ở tầng nào: indexing/retrieval/generation).

**Retrieval Strategy Trade-off:** Ban đầu tôi nghĩ hybrid always better, nhưng tuning log cho thấy variant 1 gây regression trên 5/10 câu. Reranker không fine-tune domain khiến uniform scores, query expansion tạo noise. Bây giờ tôi hiểu: just adding complexity ≠ improvement. Phải measure carefully từng component.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhieu thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

**Giả thuyết ban đầu:** Variant 1 (hybrid + rerank) sẽ fix q09 (ERR-403-AUTH, Recall=0) vì BM25 catch exact error code, reranker sắp xếp top.

**Thực tế:** q09 Recall vẫn 0/5. Rất ngạc nhiên! Root cause: reranker scores tất cả chunks ~0.016 (uniform), không phân biệt. BM25 không match vì trong doc chỉ có "401 Unauthorized", "403 Forbidden" mà không có exact "ERR-403-AUTH" string - nó là error code internal

**Thách thức lớn:** Phải debug scoreboard để hiểu tại sao Variant 1 gây regression trên q07, q08, q10. Mất thời gian nhất phần này. Nhận ra rằng:
- Reranker weights để dense=0.6, sparse=0.4 không phù hợp domain documents
- Query expansion strategy "expansion" tạo thêm noise không cần thiết
- Giả thuyết "more mechanisms = better" là sai với RAG

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** "Escalation trong sự cố P1 diễn ra như thế nào?" (q06)

**Phân tích:**

**Baseline (Dense Retrieval):** Faithfulness=4/5, Context Recall=2/5. Model trả lời partial - ghi được "Ticket P1 escalate lên Senior Engineer" nhưng không đầy đủ chi tiết. Lỗi chính ở **retrieval**: dense search lấy được section 4 (access escalation) không phải P1 escalation section.

**Variant 1 (Hybrid + Rerank):** Faithfulness=5/5 (tốt hơn), nhưng Recall vẫn 2/5 (không cải thiện), Completeness 5→4 (giảm). **Hybrid không fix được vấn đề.** Dù có BM25 + dense, reranker vẫn sắp xếp P1 escalation section không lên top. Nguyên nhân: Reranker fine-tuned generic docs, không hiểu domain-specific "P1 escalation" vs "access escalation" là khác nhau.

**Kết luận:** q06 phản ánh limitation của retrieval tuning - cần metadata (tag: "P1-escalation") hoặc domain-specific reranker, không phải chỉ thay đổi strategy.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

1. **Fine-tune reranker trên domain data**: Scorecard cho thấy variant 1 reranker scores uniform (~0.016). Tôi sẽ fine-tune reranker với 10 sample question + ground truth chunks từ SLA/Policy docs để reranker học phân biệt relevant vs irrelevant chunks.

2. **Thêm metadata tags**: q06 (Escalation) và q09 (ERR-403-AUTH) đều có Recall thấp. Tôi sẽ tag từng chunk: "category: P1-escalation", "error_code: 403" để retrieval filter chính xác trước, sau đó rerank. Đây là structured retrieval approach dễ implement hơn training.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
