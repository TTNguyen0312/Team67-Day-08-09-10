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

### 6) Team contribution (from individual reports)
- **Tech Lead — Nguyen Trong Tien**
  - Triển khai và nối end-to-end: `index.py` (preprocess/chunk/embed/store), hỗ trợ review `rag_answer.py`, và triển khai `eval.py` (LLM-as-Judge + tách prompt).
  - Nhấn mạnh failure mode: reranker không fine-tune domain → điểm gần như đồng đều, dễ gây regression; thêm/điều chỉnh “abstain” cần kiểm soát để không làm mất completeness.
- **Retrieval Owner — Truong Quang Loc**
  - Implement/điều chỉnh retrieval pipeline trong `rag_answer.py` (dense/hybrid) và `transform_query()`.
  - Rút ra bài học: ưu tiên sửa indexing/chunking/coverage trước khi tăng độ phức tạp retrieval; lỗi chunking có thể làm “không tìm thấy” dù đổi strategy.
- **Evaluation Owner — Nguyen Viet Quang (lead), Nguyen Thi Ngoc (support)**
  - Chạy scorecard theo 4 metrics và dùng kết quả để trace lỗi theo tầng (indexing/retrieval/generation), đặc biệt tập trung vào các câu yếu như q09/q06.
  - Đề xuất cải tiến theo A/B rule (đổi 1 biến/lần) và bổ sung dữ liệu/contract cho các query dạng “mã lỗi”.
- **Documentation Owner — Nguyen Thi Ngoc, Vu Duc Minh**
  - Duy trì `docs/architecture.md` và `docs/tuning-log.md`: ghi giả thuyết, thay đổi config, và quan sát per-question để tránh kết luận cảm tính.
  - Tổng hợp insight: “thêm cơ chế không đồng nghĩa tốt hơn”; cần đo và mô tả trade-off rõ ràng.

### 7) Cross-check: shared lessons (synthesized)
- **Indexing/Chunking matters**: alias/ghi chú hoặc phần “không nằm trong section” nếu bị rơi sẽ làm retrieval thất bại dù tune weights/strategy.
- **Rerank is not free**: reranker generic có thể cho điểm gần như uniform → xáo trộn thứ tự và gây regression.
- **Keyword/mã lỗi cần dữ liệu phù hợp**: nếu corpus không chứa chuỗi/mapping của mã lỗi, hybrid/BM25 khó “cứu”; nên bổ sung reference doc hoặc rule-based abstain rõ ràng.

