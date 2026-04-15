# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Vũ Đức Minh
**Mã học viên:** 2A202600459
**Vai trò:** Embed & Idempotency Owner
**Ngày nộp:** 2026-04-15

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

Trong Lab Day 10, tôi đảm nhận vai trò **Embed & Idempotency Owner**, chịu trách nhiệm quản lý việc đưa dữ liệu đã clean vào vector store (ChromaDB) và đảm bảo quá trình này **idempotent** (chạy nhiều lần không gây trùng lặp hoặc dữ liệu rác).

Tôi làm việc chủ yếu với pipeline `etl_pipeline.py`, đặc biệt là các bước `embed_upsert` và `embed_prune`. Tôi phối hợp với thành viên phụ trách cleaning để đảm bảo chỉ dữ liệu hợp lệ được đưa vào embedding.

**Bằng chứng:**

* `embed_upsert count=6 collection=day10_kb`
* `embed_prune_removed=1` (trong run dirty và fixed)

Điều này cho thấy hệ thống đã loại bỏ vector cũ khi dữ liệu thay đổi.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Một quyết định quan trọng tôi thực hiện là sử dụng **chiến lược idempotent embedding thông qua upsert + prune**.

Cụ thể:

* `embed_upsert`: cập nhật hoặc thêm mới vector theo `chunk_id`
* `embed_prune`: xóa các vector không còn tồn tại trong cleaned dataset

Điều này giúp đảm bảo:

* Không có duplicate vector khi pipeline chạy lại
* Vector store luôn phản ánh đúng trạng thái dữ liệu mới nhất

Ví dụ trong log:

```text
embed_prune_removed=1
embed_upsert count=6
```

Điều này cho thấy khi dữ liệu dirty được xử lý lại, hệ thống đã loại bỏ vector stale và cập nhật lại vector đúng.

Nếu không có idempotency, vector DB có thể chứa cả dữ liệu cũ (14 ngày) và mới (7 ngày), gây nhiễu retrieval.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Một anomaly tôi quan sát được là **vector stale tồn tại khi dữ liệu thay đổi**.

Triệu chứng:

* Dữ liệu dirty chứa refund policy “14 ngày”
* Nếu không prune, vector cũ vẫn tồn tại trong DB

Detection:

* Trong run `sprint3_dirty`:

```text
refund_no_stale_14d_window FAIL (violations=1)
embed_prune_removed=1
```

Nguyên nhân:

* Dữ liệu raw chứa policy sai
* Nếu không có cơ chế prune, vector DB sẽ giữ cả dữ liệu cũ và mới

Cách xử lý:

* Áp dụng `embed_prune` để loại bỏ vector không còn trong cleaned dataset
* Đảm bảo mỗi lần run, vector DB chỉ chứa dữ liệu hợp lệ

Sau khi fix (`sprint3_fixed`), vector store được đồng bộ lại hoàn toàn với dữ liệu sạch.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Trong run `sprint3_clean`:

* `embed_upsert count=6`
* Không có prune → dữ liệu sạch, không cần loại bỏ

Trong run `sprint3_dirty`:

* `refund violation = 1`
* `embed_prune_removed=1`

→ Cho thấy hệ thống đã phát hiện và loại bỏ vector stale

Trong run `sprint3_fixed`:

* `embed_prune_removed=1`
* `violations = 0`

→ Vector DB được đồng bộ lại với dữ liệu sạch

Điều này chứng minh rằng cơ chế idempotency hoạt động đúng và giúp tránh nhiễu trong retrieval.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm thời gian, tôi sẽ cải tiến bằng cách:

* Thêm versioning theo `effective_date` để ưu tiên dữ liệu mới nhất
* Log chi tiết hơn các vector bị prune (trace theo doc_id)
* Kết hợp semantic filtering để giảm ảnh hưởng của dữ liệu gần giống nhưng sai

---
