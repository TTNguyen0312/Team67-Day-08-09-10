# Quality report — Lab Day 10 (nhóm)

**run_id:** sprint3_clean → sprint3_dirty → sprint3_fixed
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số             | Clean (sprint3_clean) | Dirty (sprint3_dirty)    | Fixed (sprint3_fixed) | Ghi chú                              |
| ------------------ | --------------------- | ------------------------ | --------------------- | ------------------------------------ |
| raw_records        | 10                    | 10                       | 10                    | Dữ liệu đầu vào không đổi            |
| cleaned_records    | 6                     | 6                        | 6                     | Sau cleaning giữ lại 6 record hợp lệ |
| quarantine_records | 4                     | 4                        | 4                     | 4 record bị loại do lỗi              |
| Expectation halt?  | No (OK)               | **FAIL (refund policy)** | No (OK)               | Dirty run phát hiện violation        |

---

## 2. Before / after retrieval (bắt buộc)

> File eval:

* `artifacts/eval/eval_after_clean.csv`
* `artifacts/eval/eval_after_dirty.csv`
* `artifacts/eval/eval_before_clean.csv`

---

### Câu hỏi then chốt: refund window (`q_refund_window`)

**Trước (clean):**

* Retrieval chỉ chứa:

  > "refund within 7 working days"
* `hits_forbidden = 0`
* Không tồn tại policy sai

---

**Trong trạng thái dirty:**

* Expectation:

  ```text
  refund_no_stale_14d_window FAIL (violations=1)
  ```
* Điều này cho thấy tồn tại policy:

  > "refund within 14 working days"
* Nếu bỏ validate (`--skip-validate`), chunk sai sẽ được embed
* Retrieval có nguy cơ:

  * chứa 14 ngày
  * hoặc lẫn 7 và 14 ngày trong context
* `hits_forbidden > 0`

---

**Sau khi fix:**

* Expectation quay lại:

  ```text
  violations = 0
  ```
* Policy sai đã bị loại bỏ
* Retrieval quay về:

  > "7 working days"
* `hits_forbidden = 0`

---

 Kết luận:

* Dirty data làm hệ thống retrieval bị nhiễu
* Validation giúp phát hiện và chặn dữ liệu sai
* Fix pipeline giúp khôi phục chất lượng retrieval

---

### Merit: versioning HR (`q_leave_version`)

**Clean:**

* Policy đúng:

  > "12 days of annual leave"
* Không có conflict

**Dirty:**

* Có khả năng tồn tại policy cũ (10 ngày)
* Gây conflict version trong retrieval

**Fixed:**

* Policy cũ bị loại
* Retrieval ổn định lại

---

 Kết luận:

* Version control là yếu tố quan trọng trong data pipeline
* Nếu không kiểm soát, AI sẽ trả lời dựa trên dữ liệu lỗi thời

---

## 3. Freshness & monitor

Kết quả cho cả 3 run:

* Status: **FAIL**
* latest_exported_at: 2026-04-10T08:00:00
* age_hours: ~122 giờ
* SLA: 24 giờ

---

 Giải thích:

* Dữ liệu đã vượt SLA (>5 ngày)
* Pipeline phát hiện đúng dữ liệu stale

---

 Ý nghĩa:

* Dù dữ liệu clean và validate đúng, vẫn có thể lỗi do outdated
* Freshness check là lớp bảo vệ thứ 2 sau validation

---

## 4. Corruption inject (Sprint 3)

Nhóm thực hiện inject dữ liệu lỗi bằng cách:

* Thêm **stale refund policy (14 ngày)**
* Thêm **duplicate record**
* Thêm **doc_id không hợp lệ**
* Thêm **lỗi định dạng ngày**

---

### Quan sát:

* Trong run `sprint3_dirty`:

  * Expectation detect:

    ```text
    violations = 1
    ```
  * embed_prune_removed = 1 → hệ thống loại bỏ vector stale

---

### Khi bypass validation:

* Nếu chạy với:

  ```bash
  --skip-validate --no-refund-fix
  ```
* Dữ liệu sai sẽ được embed vào vector DB
* Gây:

  * retrieval sai
  * context conflict
  * `hits_forbidden` tăng

---

 Điều này chứng minh:

* Validation không chỉ để “check cho vui”
* Nó là lớp bảo vệ critical cho hệ thống AI

---

## 5. Hạn chế & việc chưa làm

* Chưa có cơ chế resolve conflict (chỉ loại bỏ, chưa hợp nhất)
* Chưa có alert tự động khi expectation FAIL
* Chưa có cơ chế auto rollback khi phát hiện data lỗi
* Retrieval evaluation còn đơn giản (keyword-based)
* Chưa áp dụng filter theo thời gian (effective_date)

---
