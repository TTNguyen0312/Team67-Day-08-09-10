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
- **Variant**: hybrid retrieval (dense + BM25 sparse với RRF) + rerank + query expansion; chi tiết tại `docs/tuning-log.md`.

### 4) Evaluation summary (evidence)
Xem:
- `results/scorecard_baseline.md`
- `results/scorecard_variant.md`
- `results/ab_comparison.csv`

Kết luận ngắn:
- Variant cải thiện **faithfulness/relevance**.
- Trade-off: **completeness** giảm ở một số câu → hướng tune tiếp là điều chỉnh funnel (tăng top_k_search trước rerank hoặc tăng top_k_select), vẫn tuân thủ A/B rule.

### 5) Team contribution (fill in)
- **Tech Lead**: __________________
- **Retrieval Owner**: __________________
- **Eval Owner**: __________________
- **Documentation Owner**: __________________

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

Nhận xét ngắn:
- Variant cải thiện mạnh ở **faithfulness/relevance** (giảm nguy cơ “trả lời không đúng trọng tâm”).
- Trade-off: **completeness** giảm ở một số câu → hướng tune tiếp là điều chỉnh funnel (tăng top_k_search trước rerank hoặc tăng top_k_select) nhưng vẫn giữ A/B rule.

### 5) What we would improve next
- Tuning funnel: thử tăng `top_k_search` (ví dụ 15) trước rerank, giữ `top_k_select=3` để tăng coverage mà vẫn kiểm soát context length.
- Chuẩn hoá query transform (expansion/decomposition) theo loại câu hỏi để tránh mở rộng “lạc hướng”.

### 6) Team contribution (fill in)
- **Tech Lead**: __________________ (phần đã làm + quyết định kỹ thuật)
- **Retrieval Owner**: __________________
- **Eval Owner**: __________________
- **Documentation Owner**: __________________

