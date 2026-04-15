# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Việt Quang  
**Vai trò:** Ingestion / Raw Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `docs/data_contract.md` — Điền đầy đủ 4 mục: source map (2 nguồn), schema cleaned (5 cột), quy tắc quarantine (6 reason), phiên bản và canonical (policy refund v4, HR leave 2026).
- `contracts/data_contract.yaml` — Bổ sung `owner_team: "Team67"` và `alert_channel: "#team67-data-alerts"`.
- `artifacts/logs/run_sprint1.log` — Chạy pipeline lần đầu với `run_id=sprint1`, xác nhận log đầy đủ các trường bắt buộc.
- `artifacts/manifests/manifest_sprint1.json` — Manifest JSON cho lần chạy đầu tiên.

**Kết nối với thành viên khác:**

Tôi chạy pipeline Sprint 1 để tạo baseline (log, manifest, cleaned/quarantine CSV), làm nền tảng cho Cleaning & Quality Owner thêm rule mới ở Sprint 2 và Embed Owner kiểm tra idempotency.

**Bằng chứng (commit / comment trong code):**

Branch `sprint1`, commit `sprint 1` — thay đổi 5 file: `data_contract.md`, `data_contract.yaml`, `cleaned_sprint1.csv`, `manifest_sprint1.json`, `quarantine_sprint1.csv`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Khi điền `data_contract.md`, tôi quyết định ghi rõ **quy tắc quarantine thay vì drop**. Lý do: trong data engineering, record không hợp lệ cần được lưu riêng (quarantine) để Data Owner review sau, không nên xóa mất (drop).

Ví dụ cụ thể: chunk HR bản 2025 ghi "10 ngày phép năm" (`effective_date=2025-01-01`) bị quarantine với reason `stale_hr_policy_effective_date`. Nếu drop thì không ai biết có dữ liệu cũ lọt vào export. Nhờ quarantine, nhóm phát hiện rằng hệ nguồn vẫn export bản HR đã hết hiệu lực — cần báo cho team quản lý KB xóa version cũ.

Tôi cũng quyết định ghi nhận `freshness_check=FAIL` là **hợp lý** trong contract (vì CSV mẫu có `exported_at=2026-04-10`, cách ngày chạy khoảng 5 ngày, vượt SLA 24h). Điều này giúp Sprint 4 giải thích chính xác trong runbook.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** Khi chạy pipeline nhiều lần với cùng `run_id=sprint1`, file log `run_sprint1.log` bị **append trùng** — log phình lên 65 dòng (4 lần chạy x 16 dòng) thay vì 16 dòng sạch. Điều này gây khó khăn khi đọc log để kiểm tra kết quả.

**Phát hiện:** Tôi mở `artifacts/logs/run_sprint1.log` và thấy cùng block `run_id=sprint1 ... PIPELINE_OK` lặp lại 4 lần. Nguyên nhân: hàm `_log()` trong `etl_pipeline.py` dùng mode **append** (`"a"`) nên mỗi lần chạy cùng `run_id` sẽ ghi thêm vào file cũ thay vì ghi đè.

**Fix:** Tôi dọn lại file log, chỉ giữ 1 lần chạy cuối cùng (16 dòng) và commit bản sạch. Đây là bài học: pipeline nên có cơ chế **overwrite hoặc rotate log** theo `run_id` để tránh dữ liệu log bị trùng lặp khi rerun.

---

## 4. Bằng chứng trước / sau (80–120 từ)

**Run ID:** `sprint1`

**Trước (raw):** File `data/raw/policy_export_dirty.csv` có 10 dòng với 6 loại lỗi (duplicate, rỗng, doc_id lạ, ngày sai format, HR cũ, refund lệch).

**Sau (cleaned):** File `artifacts/cleaned/cleaned_sprint1.csv` chỉ còn 6 dòng sạch. Trích log `run_sprint1.log`:

```
run_id=sprint1
raw_records=10
cleaned_records=6
quarantine_records=4
```

File quarantine `artifacts/quarantine/quarantine_sprint1.csv` ghi rõ 4 dòng bị loại với reason: `duplicate_chunk_text`, `missing_effective_date`, `stale_hr_policy_effective_date`, `unknown_doc_id`. Tất cả 6 expectation baseline đều **OK**, pipeline exit 0.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ **tích hợp pydantic model** để validate schema cleaned thay vì chỉ dùng expectation custom. Cụ thể: tạo class `CleanedChunk(BaseModel)` với field type validation (`chunk_id: str`, `effective_date: date`, `exported_at: datetime`) — mỗi record qua model trước khi vào cleaned CSV. Điều này giúp phát hiện lỗi schema sớm hơn (ở bước clean thay vì bước expectation) và đạt điều kiện **Distinction** (+2 bonus).
