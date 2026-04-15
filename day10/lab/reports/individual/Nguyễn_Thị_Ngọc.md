# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Thị Ngọc  
**Vai trò:** Cleaning & Quality Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài:** ~550 từ

---

## 1. Tôi phụ trách phần nào? (120 từ)

Trong dự án này, tôi chịu trách nhiệm chính về tầng **Transform** và **Quality Assurance**. Cụ thể:
- **Module `transform/cleaning_rules.py`**: Tôi đã thiết kế và triển khai 5 quy tắc làm sạch dữ liệu mới để loại bỏ nhiễu hệ thống, xử lý PII (email/số điện thoại), và chuẩn hóa văn bản tiếng Việt. Đặc biệt, tôi đã tối ưu hóa hàm `clean_rows` để nhận cấu hình động từ Data Contract thay vì hard-code, giúp đạt hạng **Distinction**.


- **Báo cáo nhóm `reports/group_report.md`**: Tôi đã trực tiếp soạn thảo Mục 2 (Cleaning & expectation) và Mục 3 (Before / after ảnh hưởng retrieval), tổng hợp bảng `metric_impact` để chứng minh các quy tắc làm sạch không phải là trivial.
- **Quality Evidence**: Tôi thực hiện kịch bản Inject Corruption ở Sprint 3 để lấy bằng chứng Before/After, chứng minh hiệu quả của các quy tắc làm sạch đối với chất lượng Retrieval.

**Bằng chứng (commit / comment trong code):**

- File `transform/cleaning_rules.py`: Các rule 7-11 kèm docstring chi tiết.

- File `reports/group_report.md`: Nội dung Mục 2 và Mục 3, bảng so sánh định lượng.

---

## 2. Một quyết định kỹ thuật (150 từ)

Một quyết định kỹ thuật quan trọng tôi đã thực hiện là **tách biệt logic xử lý ghi chú nội bộ (`internal_note_removal`) và tag hệ thống (`audit_tag_removal`)** trong quy trình làm sạch. 

Khi quan sát dữ liệu thực tế tại dòng 3 của file `cleaned_2026-04-15T09-01Z.csv`, tôi thấy các đoạn như `(ghi chú: bản sync cũ...)` và `[cleaned: stale_refund_window]` xuất hiện đan xen. Thay vì dùng một Regex chung phức tạp, tôi quyết định dùng hai Regex riêng biệt (`_INTERNAL_NOTE_PATTERN` và `_AUDIT_TAG_PATTERN`). 

Quyết định này giúp mã nguồn dễ bảo trì hơn và cho phép chúng ta kiểm soát chính xác mức độ "nhiễu" cần loại bỏ. Kết quả là văn bản đầu ra hoàn toàn sạch sẽ, chỉ chứa nội dung nghiệp vụ, giúp mô hình Embedding không bị phân tâm bởi các thông tin kỹ thuật dư thừa, từ đó tăng độ chính xác của kết quả tìm kiếm (RAG).

---

## 3. Một lỗi hoặc anomaly đã xử lý (130 từ)

**Sự cố:** Khi triển khai quy tắc kiểm tra ngày tương lai (`future_date_check`), tôi gặp lỗi `TypeError: can't compare offset-naive and offset-aware datetimes`. 
**Nguyên nhân:** Dữ liệu đầu vào `exported_at` đôi khi có ký tự `Z` (UTC aware), trong khi `datetime.now()` mặc định trả về naive datetime. 
**Xử lý:** Tôi đã cập nhật hàm `clean_rows` để xử lý triệt để định dạng ISO 8601. Tôi sử dụng `.replace("Z", "+00:00")` và kiểm tra nếu `dt.tzinfo` là `None` thì sẽ gán mặc định là `timezone.utc`. 
**Kết quả:** Quy tắc hoạt động ổn định trên mọi môi trường múi giờ, đảm bảo không có bản ghi nào có ngày xuất phát từ "tương lai" lọt vào hệ thống, bảo vệ tính toàn vẹn của dữ liệu (Data Integrity).

---

## 4. Bằng chứng trước / sau (100 từ)

Tôi đã thực hiện so sánh kết quả chạy pipeline giữa hai kịch bản:
- **Trước khi fix (Inject lỗi)**: Sử dụng flag `--no-refund-fix`. Kết quả retrieval cho câu hỏi hoàn tiền trả về chunk "14 ngày làm việc". Log ghi nhận `hits_forbidden=true`.
- **Sau khi fix (Run chuẩn)**: Pipeline tự động chuyển 14 ngày thành 7 ngày và xóa ghi chú nhiễu.
- **Dòng log thực tế (run_distinction_v1.log):**