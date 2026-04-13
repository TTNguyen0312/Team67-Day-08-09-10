## Group Report — Day 08 (RAG Pipeline)

### 1) Problem & goal
Nhóm xây trợ lý nội bộ cho CS + IT Helpdesk, trả lời câu hỏi về policy/SLA/quy trình cấp quyền/FAQ bằng RAG grounded: **retrieve chứng cứ** từ tài liệu nội bộ, **trả lời ngắn gọn có trích nguồn**, và **abstain** khi không đủ dữ liệu để tránh hallucination.

### 2) System design (high level)
- **Indexing (`index.py`)**: preprocess → chunk theo heading/paragraph + overlap → embed → lưu ChromaDB.
- **Retrieval & Answer (`rag_answer.py`)**: query → (query transform) → retrieve (dense/sparse/hybrid) → (rerank) → build grounded prompt → LLM → answer + sources.
- **Evaluation (`eval.py`)**: chạy test set 10 câu, chấm 4 metrics (faithfulness, relevance, context recall, completeness), so sánh baseline vs variant và xuất scorecard.

### 3) Key decisions
- **Chunking**: chunk ~400 tokens, overlap ~80 tokens, ưu tiên ranh giới tự nhiên theo section/paragraph để giảm cắt giữa điều khoản.
- **Baseline**: dense retrieval (top_k_search=10, top_k_select=3).
- **Variant (tuning)**: thử hybrid retrieval (dense + BM25 sparse với RRF), kết hợp rerank và query expansion để tăng khả năng bắt alias/keyword; ghi chi tiết trong `docs/tuning-log.md`.

### 4) Evaluation summary (evidence)
Kết quả chi tiết xem:
- `results/scorecard_baseline.md`
- `results/scorecard_variant.md`
- `results/ab_comparison.csv`
- `docs/tuning-log.md` (ghi nhận quan sát theo từng câu + kết luận tuning)

Nhận xét ngắn:
- Variant nhắm tới việc tăng khả năng bắt **keyword/alias/mã lỗi** bằng hybrid + rerank + query expansion.
- Kết quả cho thấy có **trade-off**: một số metric/câu cải thiện, nhưng cũng có câu bị regression; nhóm dùng scorecard + tuning-log để quyết định hướng tune tiếp theo A/B rule.

### 5) What we would improve next
- Tuning funnel: thử tăng `top_k_search` (ví dụ 15) trước rerank, giữ `top_k_select=3` để tăng coverage mà vẫn kiểm soát context length.
- Chuẩn hoá query transform (expansion/decomposition) theo loại câu hỏi để tránh mở rộng “lạc hướng”.
- Bổ sung dữ liệu có cấu trúc (nếu cần): ví dụ bảng tham chiếu mã lỗi/keyword nội bộ để tăng recall cho các câu kiểu “error code”.

### 6) Team contribution (fill in)
- **Tech Lead**: __________________ (phần đã làm + quyết định kỹ thuật)
- **Retrieval Owner**: __________________
- **Eval Owner**: __________________
- **Documentation Owner**: Nguyen Thi Ngoc__________________

