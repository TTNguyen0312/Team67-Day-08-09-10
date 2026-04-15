# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Trọng Tiến - 2A202600228  
**Vai trò:** Eval / Quality / Docs Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
- `artifacts/eval/eval_after_clean.csv - eval_after_dirty.csv - eval_before_clean.csv`: Kết quả chạy eval_retrieval trong 3 trường hợp.
- `artifacts/eval/grading_run.jsonl`: Kết quả grading 3 câu (gq_d10_01/02/03): tất cả `contains_expected=true`, `hits_forbidden=false`.
- `quality/expectations.py`: Bộ 13 expectation (E1–E12 custom + **E13 pydantic schema validation bonus**), phân loại severity `warn` / `halt`. Quality check cho phần này của Lộc.
- `transform/cleaning_rules.py`: 11 cleaning rule (baseline 6 + mở rộng 5: `future_date_check`, `audit_tag_removal`, `internal_note_removal`, `dash_normalization`, `punctuation_cleanup`). Quality check cho phần này của Ngọc
- `reports/group_report.md`: Tổng hợp báo cáo nhóm, bảng metric_impact, commit bằng chứng E13.

**Kết nối với thành viên khác:**

Tôi nhận source code cleaning_rules.py và expectations.py từ Ngọc / Lộc sau Sprint 2, thực hiện quality check, thêm expectation số 13, chạy `eval_retrieval.py` và `grading_run.py` để xác nhận retrieval quality trên tập `official_run_v1`, sau đó bàn giao `grading_run.jsonl` cho nhóm và hoàn thiện `group_report.md`.

**Bằng chứng (commit / comment trong code):**


- Commit `add: eval file` (8c7d847): Đã chạy eval_retrieval.py và commit các file data sau eval đã chạy.
- Commit `add: grading run file` (b709351): Đã chạy grading run và thêm grading_run.jsonl vào repo.
- Commit `add: pipeline_architecture and quality_report (4a0fdb2): Hoàn thiện pipeline_architecture.csv and quality_report.csv
---

## 2. Một quyết định kỹ thuật (100–150 từ)

Trong quá trình quality check `quality/expectations.py` của Ngọc, tôi nhận thấy bộ E1–E10 chỉ kiểm tra tính đúng/sai của từng chunk riêng lẻ mà bỏ qua hai rủi ro ở cấp **tập dữ liệu**:
-  `exported_at` bị thiếu hàng loạt sẽ làm freshness_check fallback về run timestamp, che khuất data lag thực tế; 
- nếu toàn bộ một nguồn tài liệu bị quarantine, RAG mất luôn knowledge base đó nhưng pipeline vẫn exit 0 mà không cảnh báo.

Tôi quyết định hướng dẫn Ngọc bổ sung thêm **E11** và **E12** để vá hai blind spot này:

- **E11 `exported_at_coverage_80pct`** (`quality/expectations.py` L227–L242, severity `warn`): tính `coverage_rate = 1 - missing_ts / total`; fail nếu < 80%. Trong `official_run_v1`, `coverage=100.0%`, đảm bảo tất cả 6 dòng đều có timestamp.
- **E12 `doc_id_diversity_min_3`** (`quality/expectations.py` L244–L259, severity `warn`): đếm `distinct_doc_ids`; fail nếu < 3. Kết quả `distinct_doc_ids=4`, đảm bảo đủ coverage 4 nguồn tài liệu.

Severity `warn` (không phải `halt`) là quyết định có chủ đích: thiếu timestamp hay mất một nguồn không nên dừng pipeline, nhưng cần ghi nhận để Ops team xử lý.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** Khi chạy `eval_retrieval.py` trên dataset dirty (trước khi clean), câu hỏi `q_refund_window` trả về `hits_forbidden=yes`.

**Phát hiện:** Tôi đọc `artifacts/eval/eval_after_dirty.csv` dòng 2:

```
q_refund_window,...,top1_preview="...14 ngày làm việc kể từ xác nhận đơn...",contains_expected=yes,hits_forbidden=yes
```

Chroma đang trả về chunk `policy_refund_v4` chứa stale refund window 14 ngày, do Rule 6 (refund fix 14→7) chưa được áp dụng. Đây không phải bug của `eval_retrieval.py` mà là bug *dữ liệu*: forbidden keyword `"14 ngày"` lọt qua vì embed chạy trước khi cleaning rules được bổ sung đầy đủ.

**Xử lý:** Tôi xác nhận `hits_forbidden=yes` là hợp lý, do eval script phát hiện đúng vấn đề. Kết quả này là bằng chứng trực tiếp rằng pipeline phải clean *trước* khi thực hiện embed. Sau khi Cleaning Owner chạy lại với đầy đủ 11 rules và embed lại, `eval_after_clean.csv` xác nhận `hits_forbidden=no` với `top1_preview="7 ngày làm việc"`.

---

## 4. Bằng chứng trước / sau (80–120 từ)

**Run ID:** `official_run_v1`

**So sánh eval câu `q_refund_window`:**

| Field | `eval_after_dirty.csv` | `eval_after_clean.csv` |
|---|---|---|
| `top1_preview` | "...14 ngày làm việc..." | "...7 ngày làm việc..." |
| `contains_expected` | yes | yes |
| `hits_forbidden` | **yes** | **no** |

**Grading run (`artifacts/eval/grading_run.jsonl`):**

```json
{"id":"gq_d10_01","contains_expected":true,"hits_forbidden":false,"top_k_used":5}
{"id":"gq_d10_02","contains_expected":true,"hits_forbidden":false,"top_k_used":5}
{"id":"gq_d10_03","contains_expected":true,"hits_forbidden":false,"top1_doc_matches":true,"top_k_used":5}
```

3/3 câu grading `contains_expected=true`, `hits_forbidden=false`. Câu `gq_d10_03` đạt `top1_doc_matches=true`.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ thêm **LLM-based scoring** vào `grading_run.py`: thay vì chỉ keyword match, gọi Claude API để đánh giá câu trả lời agent theo `grading_criteria` trong `grading_questions.json`. Đây là bước chuyển từ *retrieval eval* (đo chunk ranking) sang *end-to-end eval* (đo chất lượng trả lời thực tế), nhằm phát hiện được các trường hợp chunk đúng nhưng agent vẫn trả lời sai.
