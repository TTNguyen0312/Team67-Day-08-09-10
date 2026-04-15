# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Trương Quang Lộc
**Vai trò:** Quality Owner
**Ngày nộp:** 15/4/2026
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào?

Tôi phụ trách module `quality/expectations.py`: tầng kiểm tra chất lượng sau khi dữ liệu đã được làm sạch.

Cụ thể, thêm 6 expectation mới (E9–E14) ngoài baseline sẵn có (E1–E8): 
- E9 kiểm tra không còn thẻ HTML trong `chunk_text`; 
- E10 kiểm tra không còn audit tag `[cleaned: ...]` và ghi chú nội bộ `(ghi chú: ...)`; 
- E11 kiểm tra tỷ lệ `exported_at` được điền đạt ≥ 80%; 
- E12 kiểm tra có ít nhất 3 `doc_id` khác nhau trong cleaned output; 
- E13 dùng pydantic v2 (`CleanedChunkSchema`) để validate toàn bộ schema theo `contracts/data_contract.yaml`. 

Kết nối với thành viên khác: expectations chạy sau khi Cleaning Owner xuất cleaned CSV, kết quả `halt/warn` quyết định pipeline có tiến vào bước embed hay không.

---

## 2. Một quyết định kỹ thuật

Khi thiết kế 6 expectation mới, tôi phải quyết định mỗi cái dùng severity `halt` hay `warn`. Quyết định dựa trên một tiêu chí cụ thể: nếu vi phạm expectation đó khiến RAG trả kết quả **sai về nội dung** thì dùng `halt`; nếu chỉ ảnh hưởng chất lượng retrieval hoặc khả năng quan sát thì dùng `warn`.

Ví dụ, E9 (`no_html_tags_in_chunk_text`) và E10 (`no_system_noise_in_chunk_text`) là `halt` vì HTML tag và ghi chú nội bộ nếu còn trong `chunk_text` sẽ làm lệch embedding và có thể khiến `contains_expected` pass sai do keyword nằm trong phần nhiễu. Ngược lại, E11 (`exported_at_coverage_80pct`) và E12 (`doc_id_diversity_min_3`) là `warn` vì pipeline vẫn có thể embed đúng, chỉ mất đi khả năng đo freshness chính xác hoặc cảnh báo coverage gap.

Riêng E13 (pydantic) chọn `halt` vì nó là lớp bảo vệ cuối cùng trước khi embed, nếu schema sai ở đây thì vector store sẽ nhận dữ liệu không hợp lệ mà các check trên không phát hiện được.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Trong Sprint 3, sau khi nhóm chạy `python etl_pipeline.py run --run-id sprint3_dirty --no-refund-fix --skip-validate`, tôi quan sát log expectation:

```
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
WARN: expectation failed but --skip-validate → tiếp tục embed
embed_prune_removed=1
```

Triệu chứng: E3 fail vì chunk `policy_refund_v4` vẫn chứa "14 ngày làm việc" khi pipeline bỏ refund fix. Do `--skip-validate`, pipeline vẫn embed chunk stale vào ChromaDB. Eval sau đó xác nhận retrieval bị ảnh hưởng:

```
q_refund_window: hits_forbidden=yes  (eval_after_dirty.csv)
```

Điều này chứng minh E3 (`refund_no_stale_14d_window`, severity `halt`) hoạt động đúng — nó phát hiện chính xác chunk vi phạm. Sau khi nhóm chạy lại pipeline chuẩn, E3 trở về `OK` và `embed_prune_removed=1` xác nhận chunk stale đã bị xóa khỏi collection.

---

## 4. Bằng chứng trước / sau

Hai dòng `q_refund_window` từ hai file eval, chứng minh rõ before/after:

**Before** (`eval_after_dirty.csv` — `run_id=sprint3_dirty`, inject `--no-refund-fix`):
```
q_refund_window,...,contains_expected=yes,hits_forbidden=yes
```

**After** (`eval_before_clean.csv` — `run_id=sprint3_fixed`, pipeline chuẩn):
```
q_refund_window,...,contains_expected=yes,hits_forbidden=no
```

`hits_forbidden` thay đổi từ `yes` → `no` sau khi pipeline clean lại, xác nhận cleaning rule fix refund và expectation E3 hoạt động đúng.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ mở rộng `CleanedChunkSchema` trong `expectations.py` để đọc danh sách `ALLOWED_DOC_IDS` trực tiếp từ `contracts/data_contract.yaml` thay vì hard-code trong `cleaning_rules.py`. Khi nhóm thêm tài liệu mới (ví dụ `access_control_sop`), chỉ cần cập nhật một chỗ trong contract, cả cleaning rule và pydantic validator đều tự động nhận — tránh mismatch giữa hai file.
