# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

* Agent trả lời sai chính sách:

  > “Refund within **14 days**” thay vì **7 days**
* Hoặc câu trả lời đúng nhưng context chứa nhiều version conflict (7 ngày + 14 ngày)
* User nhận thông tin không nhất quán từ hệ thống

---

## Detection

Các tín hiệu phát hiện lỗi:

* **Eval retrieval**

  * `hits_forbidden > 0`
  * Context chứa chunk stale (14 ngày, 10 ngày)
* **Expectation (nếu bật validate)**

  * `refund_no_stale_14d_window`
  * `hr_leave_no_stale_10d_annual`
* **Freshness check**

  * Status: FAIL
  * `age_hours > sla_hours` (122h > 24h)
* **Metric pipeline**

  * cleaned_records tăng bất thường
  * quarantine_records giảm khi skip validation

---

## Diagnosis

| Bước | Việc làm                              | Kết quả mong đợi                                                               |
| ---- | ------------------------------------- | ------------------------------------------------------------------------------ |
| 1    | Kiểm tra `artifacts/manifests/*.json` | Xác định `run_id`, thời điểm ingest, phát hiện dữ liệu stale (age_hours lớn)   |
| 2    | Mở `artifacts/quarantine/*.csv`       | Kiểm tra các record bị loại (stale policy, doc_id lỗi, date lỗi)               |
| 3    | So sánh cleaned CSV giữa các run      | Phát hiện dữ liệu bẩn (refund 14 ngày, leave 10 ngày) tồn tại trong inject-bad |
| 4    | Chạy `python eval_retrieval.py`       | Xác nhận `hits_forbidden > 0`, context chứa stale chunk                        |
| 5    | Kiểm tra flags pipeline               | Xác nhận có sử dụng `--skip-validate` hoặc `--no-refund-fix`                   |

---

## Mitigation

* Rerun pipeline chuẩn:

  ```bash
  python etl_pipeline.py run
  ```
* Đảm bảo:

  * Validation được bật
  * Refund policy được fix (14 → 7 ngày)
* Rebuild vector store:

  * Upsert lại chunk sạch
  * Remove chunk stale
* Nếu hệ thống production:

  * Tạm thời hiển thị cảnh báo “data stale”
  * Disable agent trả lời các câu liên quan policy nhạy cảm

---

## Prevention

* Thêm expectation:

  * Reject mọi policy chứa “14 working days”
  * Reject policy HR 10 ngày nếu đã có version mới
* Thiết lập alert:

  * Khi `freshness_check = FAIL`
  * Khi `hits_forbidden > 0`
* Áp dụng SLA rõ ràng:

  * Dữ liệu phải được cập nhật < 24h
* Gán owner cho data contract:

  * Ai chịu trách nhiệm update policy
* (Nâng cao) Áp dụng guardrail:

  * Chỉ cho phép retrieval từ version mới nhất
  * Filter theo effective_date

