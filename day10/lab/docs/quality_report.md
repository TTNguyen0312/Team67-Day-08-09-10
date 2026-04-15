# Quality report — Lab Day 10 (nhóm)

**run_id:** sprint3_clean → sprint3_dirty → sprint3_fixed  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | sprint3_clean | sprint3_dirty | sprint3_fixed | Ghi chú |
|--------|:---:|:---:|:---:|---------|
| raw_records | 10 | 10 | 10 | Nguồn `policy_export_dirty.csv` |
| cleaned_records | 6 | 6 | 6 | 4 record bị quarantine ở cả 3 run |
| quarantine_records | 4 | 4 | 4 | unknown_doc_id, missing_effective_date, stale_hr_policy, duplicate_chunk_text |
| no_refund_fix | false | **true** | false | Dirty: bỏ qua fix 14→7 ngày |
| skipped_validate | false | **true** | false | Dirty: bỏ qua expectations |
| Expectation halt? | No | **FAIL** (nếu validate bật) | No | E3 `refund_no_stale_14d_window` violations=1 |
| embed_prune_removed | 0 | 0 | **1** | sprint3_fixed xóa chunk "14 ngày" khỏi Chroma |

---

## 2. Before / after retrieval (bắt buộc)

Eval files: `artifacts/eval/eval_before_clean.csv`, `artifacts/eval/eval_after_dirty.csv`

### Câu hỏi then chốt: refund window (`q_refund_window`)

| Scenario | top1_doc_id | top1_preview (truncated) | contains_expected | hits_forbidden |
|----------|-------------|--------------------------|:-:|:-:|
| **Before (clean)** | policy_refund_v4 | "...7 ngày làm việc kể từ xác nhận đơn." | **yes** | **no** |
| **After dirty inject** | policy_refund_v4 | "...14 ngày làm việc kể từ xác nhận đơn." | yes | **YES** |
| **After fix** | policy_refund_v4 | "...7 ngày làm việc kể từ xác nhận đơn." | **yes** | **no** |

Kết quả: `hits_forbidden` chuyển từ `no → YES → no` qua 3 scenario, chứng minh dirty data làm retrieval trả về chunk sai và pipeline fix khôi phục đúng.

---

### Merit: versioning HR (`q_leave_version`)

| Scenario | top1_doc_id | contains_expected | hits_forbidden | top1_doc_expected |
|----------|-------------|:-:|:-:|:-:|
| **Before (clean)** | hr_leave_policy | yes | no | yes |
| **After dirty inject** | hr_leave_policy | yes | no | yes |
| **After fix** | hr_leave_policy | yes | no | yes |

HR stale chunk (10 ngày, effective_date=2025-01-01) bị quarantine bởi Rule 3 (`stale_hr_policy_effective_date`) ở tất cả các run, kể cả khi `--no-refund-fix` được bật, vì HR stale check độc lập với refund fix flag. `top1_doc_expected=yes` ổn định qua 3 scenario.

---

## 3. Freshness & monitor

```
freshness_check = FAIL
latest_exported_at : 2026-04-10T08:00:00
age_hours          : ~122 h
sla_hours          : 24 h
reason             : freshness_sla_exceeded
```

Kết quả FAIL ở cả 3 run vì `exported_at` trong lab data cố định tại 2026-04-10 (5 ngày trước khi chạy). Trong production, data source sẽ export timestamp thực và freshness check sẽ PASS nếu pipeline chạy đủ thường xuyên.

---

## 4. Corruption inject (Sprint 3)

**Cách inject:** chạy pipeline với `--no-refund-fix --skip-validate`:

```bash
python etl_pipeline.py run --run-id sprint3_dirty --no-refund-fix --skip-validate
```

Hiệu ứng:
- Chunk `policy_refund_v4_2_22e933b0d6b582d6` ("14 ngày làm việc") được embed vào Chroma thay vì bị fix
- `eval_after_dirty.csv`: `q_refund_window` → `hits_forbidden=yes`, top1_preview chứa "14 ngày"
- Nếu validate bật (không `--skip-validate`): E3 HALT ngăn không cho embed

**Cách phát hiện và fix:**

```bash
# Phát hiện
python eval_retrieval.py --out artifacts/eval/eval_after_dirty.csv
# → hits_forbidden=yes cho q_refund_window

# Fix
python etl_pipeline.py run --run-id sprint3_fixed
# → prune xóa chunk "14 ngày" (embed_prune_removed=1)
# → upsert lại chunk "7 ngày"

# Xác nhận
python grading_run.py --out artifacts/eval/grading_run.jsonl
# → gq_d10_01: hits_forbidden=false
```

---

## 5. Hạn chế & việc chưa làm

- Freshness SLA (24h) luôn FAIL trong lab do timestamp cố định, cần data source với export timestamp thực
- Prune chỉ chạy khi embed thành công; nếu HALT xảy ra, chunk dirty từ run trước vẫn tồn tại trong Chroma cho đến lần fix
- Chưa có auto-rollback: nếu fix run thất bại giữa chừng, Chroma có thể ở trạng thái trung gian
- Eval dùng keyword matching, không phát hiện paraphrase (ví dụ: "hai tuần làm việc" thay cho "14 ngày làm việc")
- Chưa filter retrieval theo `effective_date`, chunk cũ có thể vẫn được retrieve nếu không bị quarantine
