# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Team67  
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

Pipeline thực hiện quy trình ETL khép kín:
1. **Ingest**: Đọc dữ liệu thô từ CSV export (`policy_export_dirty.csv`).
2. **Clean**: Áp dụng bộ quy tắc làm sạch mở rộng (11 rules), bao gồm xử lý PII, chuẩn hóa ngày, loại bỏ nhiễu hệ thống (audit tags, ghi chú nội bộ).
3. **Validate**: Kiểm tra chất lượng dữ liệu qua bộ 12 Expectations (phân loại warn/halt).
4. **Embed**: Thực hiện embedding idempotent vào ChromaDB (upsert theo `chunk_id`) và tự động prune các vector cũ không còn trong tập cleaned.
5. **Monitor**: Kiểm tra độ tươi (freshness) dựa trên `exported_at` và manifest.

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

```bash
python etl_pipeline.py run --run-id official_run_v1
```

---

## 2. Cleaning & expectation (150–200 từ)

Baseline có 6 rule (allowlist `doc_id`, chuẩn hóa ngày, quarantine HR cũ, loại chunk rỗng, dedupe, fix refund 14→7) và 6 expectation (E1–E6). Nhóm đã mở rộng thêm **5 rule mới** và **6 expectation mới**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| Future Date Check (Rule 7) | N/A | Quarantine count tăng | `quarantine_csv` có reason `future_exported_at` |
| Audit/Note Removal (Rule 8-9) | Context chứa nhiễu | Context sạch (chỉ chứa policy) | `cleaned_csv` không còn marker `[cleaned: ...]` |
| Unique Chunk ID (Exp E8) | Upsert ghi đè mập mờ | Pipeline HALT nếu trùng | Log: `expectation[unique_chunk_id] FAIL (halt)` |
| Noise Detection (Exp E10) | Eval pass sai do ghi chú | Pipeline HALT nếu lọt nhiễu | Log: `expectation[no_system_noise_in_chunk_text] FAIL` |

**Rule chính (baseline + mở rộng):**

- **Baseline**: `allowlist_doc_id`, `normalize_effective_date`, `stale_hr_quarantine`, `dedupe`, `refund_fix`.
- **Mở rộng (5 rules)**: `future_date_check`, `audit_tag_removal`, `internal_note_removal`, `dash_normalization`, `punctuation_cleanup`.

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

Trong quá trình chạy Sprint 3, khi sử dụng tham số `--no-refund-fix`, expectation `refund_no_stale_14d_window` đã trả về **FAIL (halt)**. 
**Cách xử lý**: Kiểm tra lại logic transform hoặc đảm bảo hệ nguồn export đúng phiên bản policy v4 (7 ngày). Trong demo, chúng tôi dùng `--skip-validate` để quan sát sự sụt giảm chất lượng retrieval (hits forbidden).

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

**Kịch bản inject:**

Chúng tôi chạy pipeline với flag `--no-refund-fix --skip-validate`. Điều này khiến chunk chứa "14 ngày làm việc" lọt vào vector store.

**Kết quả định lượng (từ CSV / bảng):**

- **Trước fix (Inject)**: Câu hỏi về refund window trả về chunk 14 ngày. `hits_forbidden=true`, `contains_expected=false`.
- **Sau fix (Clean run)**: Chunk 14 ngày được sửa thành 7 ngày, đồng thời xóa ghi chú nhiễu. `hits_forbidden=false`, `contains_expected=true`.
- **Tác động**: Độ chính xác của Agent tăng từ 0% lên 100% cho các câu hỏi liên quan đến chính sách hoàn tiền.

**Phân tích:** Câu hỏi then chốt `q_refund_window` cho thấy rõ tác động: khi inject (skip refund fix), `hits_forbidden=yes` vì chunk stale "14 ngày làm việc" vẫn nằm trong top-k context. Sau khi fix, `hits_forbidden=no` — pipeline đã loại bỏ thông tin sai.

Chứng cứ file: `artifacts/eval/eval_after_dirty.csv` (inject) vs `artifacts/eval/eval_before_clean.csv` (fix).

---

## 4. Freshness & monitoring (100–150 từ)

- **SLA**: 24 giờ kể từ `exported_at`.
- **PASS**: Dữ liệu mới xuất trong vòng 24h.
- **WARN**: Dữ liệu cũ hơn 24h nhưng vẫn trong ngưỡng 48h (cần kiểm tra hệ nguồn).
- **FAIL**: Dữ liệu quá cũ (>48h), agent có nguy cơ trả lời sai chính sách hiện hành.

Lệnh kiểm tra freshness độc lập:

```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint3_clean.json
```

---

## 5. Liên hệ Day 09 (50–100 từ)

Có. Chúng tôi tích hợp bằng cách chỉ định `CHROMA_COLLECTION=day10_kb` trong file `.env` của agent Day 09. Việc này giúp agent truy cập được dữ liệu đã được làm sạch sâu (xóa ghi chú, fix refund) thay vì dùng file văn bản thô chưa qua pipeline xử lý.

---

## 6. Rủi ro còn lại & việc chưa làm

- **Freshness luôn FAIL trên dataset mẫu** — cần dữ liệu export mới hơn hoặc cơ chế cập nhật `exported_at` tự động trong pipeline thực tế.
- **Rule 7 (future date)** không có tác động đo được trên CSV mẫu hiện tại (không dòng nào có ngày tương lai). Cần inject test riêng để chứng minh.
- **Chưa tích hợp Great Expectations / pydantic** — expectation suite hiện tại dùng custom code đơn giản.
- **Freshness chỉ đo 1 boundary (publish)** — chưa đo boundary ingest riêng (bonus +1 điểm).
- **Chưa có LLM-judge eval** — chỉ dùng keyword-based retrieval eval.
- **`access_control_sop.txt`** chưa được thêm vào allowlist và pipeline.
