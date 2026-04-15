# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** 67  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Nguyễn Việt Quang | Ingestion / Raw Owner | ___ |
| Nguyễn Thị Ngọc, Trương Quang Lộc | Cleaning & Quality Owner | ___ |
| Vũ Đức Minh | Embed & Idempotency Owner | ___ |
| Nguyễn Trọng Tiến | Monitoring / Docs Owner | nguyenvietquang.1601@gmail.com |

**Ngày nộp:** 2026-04-15  
**Repo:** https://github.com/TTNguyen0312/Team67-Day-08-09-10  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

Nguồn raw là file CSV mẫu `data/raw/policy_export_dirty.csv`, mô phỏng export "bẩn" từ hệ thống Knowledge Base nội bộ. File chứa 10 dòng chunk thuộc 4 tài liệu (`policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy`) với các lỗi: duplicate, chunk rỗng, `doc_id` lạ, ngày sai format, xung đột phiên bản HR (10 vs 12 ngày phép), và stale refund window (14 vs 7 ngày).

Pipeline chạy theo luồng: **Ingest → Clean → Validate (expectations) → Embed (Chroma) → Manifest → Freshness check**. Toàn bộ được quản lý qua `etl_pipeline.py` với `run_id` ghi trong dòng đầu log và manifest JSON.

Các run chính: `sprint1` (baseline), `sprint2` (thêm rule mới), `sprint3_dirty` (inject corruption, `--no-refund-fix --skip-validate`), `sprint3_clean` (pipeline chuẩn), `sprint3_fixed` (khôi phục sau inject).

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

```bash
python etl_pipeline.py run --run-id sprint3_clean
```

---

## 2. Cleaning & expectation (150–200 từ)

Baseline có 6 rule (allowlist `doc_id`, chuẩn hóa ngày, quarantine HR cũ, loại chunk rỗng, dedupe, fix refund 14→7) và 6 expectation (E1–E6). Nhóm đã mở rộng thêm **5 rule mới** và **6 expectation mới**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| Rule 7: Quarantine `exported_at` tương lai | quarantine=4 (sprint1) | quarantine=4 (không có dòng nào trong CSV mẫu có ngày tương lai, rule phòng ngừa) | `cleaning_rules.py` L102-111, commit `day10-sprint2` |
| Rule 8: Loại bỏ Audit Tags `[cleaned: ...]` | chunk gốc chứa tag `[cleaned: stale_refund_window]` sau fix refund | Tag bị xóa sạch khỏi `chunk_text` trong cleaned CSV | `cleaning_rules.py` L155, `eval_after_clean.csv` dòng 3 không còn tag |
| Rule 9: Loại bỏ ghi chú nội bộ `(ghi chú: ...)` | chunk_id 3 chứa "(ghi chú: bản sync cũ policy-v3 — lỗi migration)" | Ghi chú bị xóa khỏi text, `chunk_text` gọn hơn | `cleaning_rules.py` L156, `eval_after_clean.csv` dòng 3 |
| Rule 10: Chuẩn hóa dấu gạch ngang `—` → `-` | Dấu em-dash trong text gốc | Thay bằng dấu gạch ngang chuẩn | `cleaning_rules.py` L159 |
| Rule 11: Chuẩn hóa dấu câu và khoảng trắng | Khoảng trắng thừa trước dấu chấm/phẩy | Dấu câu sát từ cuối, loại bỏ dấu chấm dư | `cleaning_rules.py` L161-166 |
| E7: `chunk_max_length_1000` (warn) | long_chunks=0 | long_chunks=0 (CSV mẫu không có chunk >1000 ký tự) | `run_sprint3_clean.log` L13 |
| E8: `unique_chunk_id` (halt) | duplicate_chunk_ids=0 | duplicate_chunk_ids=0 | `run_sprint3_clean.log` L14 |
| E9: `no_html_tags_in_chunk_text` (halt) | — | html_contaminated_chunks=0 (kiểm tra sau clean) | `expectations.py` L147-161 |
| E10: `no_system_noise_in_chunk_text` (halt) | — | noise_contaminated_chunks=0 (audit tag & ghi chú đã bị xóa) | `expectations.py` L163-182 |
| E11: `exported_at_coverage_80pct` (warn) | coverage=100% | coverage=100% | `expectations.py` L184-199 |
| E12: `doc_id_diversity_min_3` (warn) | distinct_doc_ids=4 | distinct_doc_ids=4 | `expectations.py` L201-216 |

**Rule chính (baseline + mở rộng):**

- Baseline: allowlist doc_id, chuẩn hóa ngày, quarantine HR <2026, loại chunk rỗng, dedupe, fix refund 14→7
- Mở rộng: kiểm tra ngày tương lai, loại bỏ audit tag & ghi chú nội bộ, chuẩn hóa ký tự đặc biệt, chuẩn hóa dấu câu

**Ví dụ 1 lần expectation fail và cách xử lý:**

Khi chạy `sprint3_dirty` với `--no-refund-fix --skip-validate`, expectation `refund_no_stale_14d_window` **FAIL** (violations=1) vì chunk refund vẫn chứa "14 ngày làm việc". Log ghi: `WARN: expectation failed but --skip-validate → tiếp tục embed`. Sau khi chạy lại pipeline chuẩn (`sprint3_fixed`), expectation pass trở lại (violations=0).

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

**Kịch bản inject:**

Sprint 3 inject corruption bằng cách chạy pipeline **không fix refund** và **bỏ qua validation**:

```bash
# Inject dữ liệu xấu
python etl_pipeline.py run --run-id sprint3_dirty --no-refund-fix --skip-validate
python eval_retrieval.py --out artifacts/eval/eval_after_dirty.csv

# Khôi phục pipeline chuẩn
python etl_pipeline.py run --run-id sprint3_fixed
python eval_retrieval.py --out artifacts/eval/eval_before_clean.csv
```

**Kết quả định lượng (từ CSV eval):**

| question_id | Chỉ số | Sau inject (dirty) | Sau fix (clean) | Nhận xét |
|-------------|--------|--------------------|-----------------|---------| 
| `q_refund_window` | `contains_expected` | yes | yes | Cả hai đều tìm thấy "7 ngày" |
| `q_refund_window` | `hits_forbidden` | **yes** ❌ | **no** ✅ | Inject: top-k vẫn chứa chunk "14 ngày làm việc" (stale). Fix: chunk stale đã bị sửa |
| `q_p1_sla` | `contains_expected` | yes | yes | Không bị ảnh hưởng bởi inject |
| `q_lockout` | `contains_expected` | yes | yes | Không bị ảnh hưởng |
| `q_leave_version` | `contains_expected` | yes | yes | HR chunk đúng |
| `q_leave_version` | `hits_forbidden` | no | no | Bản HR cũ (10 ngày phép) đã bị quarantine ở cả 2 kịch bản |
| `q_leave_version` | `top1_doc_expected` | yes | yes | Top-1 đúng là `hr_leave_policy` |

**Phân tích:** Câu hỏi then chốt `q_refund_window` cho thấy rõ tác động: khi inject (skip refund fix), `hits_forbidden=yes` vì chunk stale "14 ngày làm việc" vẫn nằm trong top-k context. Sau khi fix, `hits_forbidden=no` — pipeline đã loại bỏ thông tin sai.

Chứng cứ file: `artifacts/eval/eval_after_dirty.csv` (inject) vs `artifacts/eval/eval_before_clean.csv` (fix).

---

## 4. Freshness & monitoring (100–150 từ)

SLA freshness được cấu hình 24 giờ trong `contracts/data_contract.yaml` (`freshness.sla_hours: 24`). Pipeline đo freshness tại điểm **publish** (sau embed) bằng cách so sánh `latest_exported_at` trong manifest với thời điểm hiện tại.

Kết quả trên dữ liệu mẫu:

| Run | Freshness | Chi tiết |
|-----|-----------|---------|
| `sprint1` | **FAIL** | `exported_at=2026-04-10`, age=120h > SLA 24h |
| `sprint3_clean` | **FAIL** | `exported_at=2026-04-10`, age=122h > SLA 24h |

FAIL là **hợp lý** vì file CSV mẫu có `exported_at` là `2026-04-10T08:00:00` (cách thời điểm chạy khoảng 5 ngày). Trong thực tế, cần hệ nguồn export dữ liệu mới hơn hoặc điều chỉnh SLA phù hợp.

Lệnh kiểm tra freshness độc lập:

```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint3_clean.json
```

---

## 5. Liên hệ Day 09 (50–100 từ)

Pipeline Day 10 sử dụng collection Chroma riêng (`day10_kb`) thay vì dùng chung collection Day 09. Lý do: Day 10 tập trung vào **tầng dữ liệu** — ingest, clean, validate, và embed từ export CSV (có lỗi). Dữ liệu được xử lý qua pipeline ETL trước khi embed, trong khi Day 09 đọc trực tiếp từ `data/docs/*.txt`.

Hai collection chia sẻ cùng 4 tài liệu nguồn canonical (`data/docs/`), nhưng Day 10 feed từ CSV export còn Day 09 feed từ plain text. Nếu muốn tích hợp, có thể chỉ agent Day 09 sang collection `day10_kb` sau khi pipeline pass.

---

## 6. Rủi ro còn lại & việc chưa làm

- **Freshness luôn FAIL trên dataset mẫu** — cần dữ liệu export mới hơn hoặc cơ chế cập nhật `exported_at` tự động trong pipeline thực tế.
- **Rule 7 (future date)** không có tác động đo được trên CSV mẫu hiện tại (không dòng nào có ngày tương lai). Cần inject test riêng để chứng minh.
- **Chưa tích hợp Great Expectations / pydantic** — expectation suite hiện tại dùng custom code đơn giản.
- **Freshness chỉ đo 1 boundary (publish)** — chưa đo boundary ingest riêng (bonus +1 điểm).
- **Chưa có LLM-judge eval** — chỉ dùng keyword-based retrieval eval.
- **`access_control_sop.txt`** chưa được thêm vào allowlist và pipeline.
