# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `data/raw/policy_export_dirty.csv` — Export CSV từ hệ thống KB nội bộ (chứa chunk đã tách sẵn cho 4 doc_id: `policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy`) | Đọc file CSV qua `csv.DictReader`; pipeline đọc từ đường dẫn cấu hình (`--raw`). Có thể thay bằng API / DB export. | **1)** Duplicate chunk_text (dòng 2–3 giống nhau). **2)** Chunk rỗng + thiếu `effective_date` (dòng 6). **3)** `doc_id` không thuộc allowlist — `legacy_catalog_xyz_zzz` (dòng 10). **4)** Định dạng ngày không ISO — `dd/mm/yyyy` (dòng 11). **5)** Xung đột version HR: bản cũ 2025 ghi "10 ngày phép năm" vs bản 2026 ghi "12 ngày" (dòng 8 vs 9). **6)** Stale refund window: chunk policy-v3 cũ ghi "14 ngày làm việc" thay vì 7 ngày (dòng 4). | `raw_records` (tổng dòng ingest), `quarantine_records` (số dòng bị loại), `cleaned_records` (số dòng hợp lệ sau clean). Alert khi `quarantine_records / raw_records > 50%` hoặc khi expectation severity=halt fail. |
| `data/docs/*.txt` — 5 tài liệu gốc canonical (policy_refund_v4, sla_p1_2026, it_helpdesk_faq, hr_leave_policy, access_control_sop) kế thừa từ Day 09 | Đọc trực tiếp từ filesystem; được dùng làm nguồn tham chiếu canonical cho contract — không đi qua pipeline CSV mà được dùng khi cần rebuild index hoặc so sánh nội dung. | **1)** File bị thiếu / đổi tên → embed fail do không tìm thấy source. **2)** Nội dung bị cập nhật nhưng CSV export chưa sync → drift giữa canonical và index. **3)** File `access_control_sop.txt` chưa có trong allowlist → nếu thêm phải đồng bộ `cleaning_rules.py` + `data_contract.yaml`. | Freshness check: so sánh `latest_exported_at` trong manifest với SLA (mặc định 24h). Alert khi `freshness_check=FAIL`. |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | ID ổn định sinh từ `sha256(doc_id + chunk_text + seq)[:16]`, dạng `{doc_id}_{seq}_{hash}`. Dùng làm key upsert trong Chroma — đảm bảo idempotent. |
| doc_id | string | Có | Khóa logic tài liệu nguồn. Chỉ chấp nhận giá trị trong allowlist: `policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy`. Giá trị ngoài allowlist → quarantine. |
| chunk_text | string | Có | Nội dung chunk sau khi đã clean (fix stale refund 14→7 ngày, strip whitespace). Constraint: `min_length >= 8`. Chunk rỗng → quarantine ở bước clean. |
| effective_date | date (YYYY-MM-DD) | Có | Ngày hiệu lực sau chuẩn hóa ISO. Hỗ trợ parse từ `dd/mm/yyyy`. Record rỗng hoặc không parse được → quarantine. HR policy có `effective_date < 2026-01-01` → quarantine (bản cũ). |
| exported_at | datetime (ISO 8601) | Có | Timestamp export từ hệ nguồn. Dùng tính freshness SLA. |

---

## 3. Quy tắc quarantine vs drop

Record bị quarantine (không drop) — lưu vào `artifacts/quarantine/quarantine_{run_id}.csv` kèm cột `reason`:

| Reason | Mô tả | Hành động |
|--------|-------|----------|
| `unknown_doc_id` | `doc_id` không thuộc allowlist | Quarantine. Cần kiểm tra xem đây là doc mới cần thêm vào allowlist hay là lỗi export. |
| `missing_effective_date` | `effective_date` rỗng sau chuẩn hóa | Quarantine. Yêu cầu hệ nguồn bổ sung ngày. |
| `invalid_effective_date_format` | Không parse được `effective_date` (không phải ISO hay dd/mm/yyyy) | Quarantine. Cần Data Owner review format mới. |
| `stale_hr_policy_effective_date` | HR policy có `effective_date < 2026-01-01` (bản cũ conflict version) | Quarantine. Bản HR 2025 ghi "10 ngày phép" đã hết hiệu lực — chỉ giữ bản 2026 ("12 ngày phép"). |
| `missing_chunk_text` | `chunk_text` rỗng | Quarantine. Record không có nội dung → không thể embed. |
| `duplicate_chunk_text` | Trùng nội dung `chunk_text` (normalized) với chunk đã xử lý | Quarantine. Giữ bản xuất hiện trước (dedup). |

**Ai approve merge lại?** Data Owner (Cleaning / Quality Owner) review file quarantine CSV sau mỗi run. Nếu xác nhận record hợp lệ → cập nhật rule / allowlist rồi rerun pipeline. Không merge thủ công vào cleaned CSV.

---

## 4. Phiên bản & canonical

**Source of truth cho policy refund:** `data/docs/policy_refund_v4.txt` — phiên bản v4 với cửa sổ hoàn tiền **7 ngày làm việc**.

- Chunk nào trong CSV export chứa "14 ngày làm việc" là bản sync cũ từ policy-v3 (lỗi migration) → pipeline tự động fix thành "7 ngày làm việc" và gắn tag `[cleaned: stale_refund_window]`.
- Nếu `--no-refund-fix` được truyền → giữ nguyên "14 ngày" (dùng cho inject corruption Sprint 3).

**Source of truth cho HR leave policy:** `data/docs/hr_leave_policy.txt` — chính sách 2026 với **12 ngày phép năm** cho nhân viên < 3 năm kinh nghiệm.

- Bản HR 2025 (10 ngày phép năm, `effective_date < 2026-01-01`) → quarantine tự động.

**Đồng bộ contract:** mọi thay đổi `allowed_doc_ids` trong code (`cleaning_rules.py`) phải cập nhật song song trong `contracts/data_contract.yaml`.
