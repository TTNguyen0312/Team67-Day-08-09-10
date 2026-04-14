# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Vũ Đức Minh
**Vai trò trong nhóm:** Worker Owner
**Ngày nộp:** 14/04/2026
**Mã sinh viên:** 2A202600459

---

## 1. Tôi phụ trách phần nào?

Trong lab Day 09, tôi phụ trách triển khai toàn bộ các worker trong hệ thống multi-agent, bao gồm: `retrieval_worker`, `policy_tool_worker`, và `synthesis_worker`. Công việc chính của tôi là đảm bảo mỗi worker hoạt động độc lập, tuân thủ đúng `worker_contracts.yaml`, và có thể tích hợp vào pipeline chung mà không gây lỗi.

**Module/file tôi chịu trách nhiệm:**

* `workers/retrieval.py`
* `workers/policy_tool.py`
* `workers/synthesis.py`

**Functions tôi implement:**

* `retrieve_dense()`, `_get_collection()`
* `analyze_policy()`, `_call_mcp_tool()`
* `synthesize()`, `_estimate_confidence()`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Worker của tôi nhận input từ Supervisor và trả output chuẩn để Synthesis tổng hợp. Retrieval cung cấp evidence, Policy kiểm tra rule và exception, và Synthesis tạo câu trả lời cuối. Nếu worker của tôi sai contract, toàn bộ pipeline sẽ fail.

**Bằng chứng:**

* Output test độc lập:

  * Retrieval trả chunk từ `sla_p1_2026.txt`
  * Policy detect `flash_sale_exception`
  * Synthesis trả answer có `[1]`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? 

**Quyết định:**
Tôi quyết định implement fallback deterministic trong `synthesis_worker` thay vì phụ thuộc hoàn toàn vào LLM.

**Lý do:**

Ban đầu, `_call_llm()` fail (do API key hoặc môi trường), khiến worker trả về message:

> "Không đủ thông tin trong tài liệu nội bộ..."

Điều này vi phạm contract vì:

* Có `retrieved_chunks` nhưng không có citation `[1]`
* Không đảm bảo answer grounded

Các lựa chọn thay thế:

1. Bắt buộc LLM phải chạy → không ổn vì phụ thuộc external
2. Retry nhiều lần → tăng latency, không đảm bảo thành công
3. Fallback deterministic từ chunks → ổn định, đúng contract

Tôi chọn cách 3.

**Trade-off đã chấp nhận:**

* Answer fallback đơn giản, không tự nhiên như LLM
* Không summarize được nhiều chunk

**Bằng chứng từ code:**

```
if chunks and (not answer or "không đủ thông tin" in answer.lower()):
    top = chunks[0]
    answer = f"Theo tài liệu {top['source']}, {top['text']} [1]"
```

Kết quả:

* Output luôn có `[1]`
* Không còn fail DoD của synthesis worker

---

## 3. Tôi đã sửa một lỗi gì?
**Lỗi:** Retrieval trả về `0 chunks`

**Symptom:**
Khi chạy `python workers/retrieval.py`, output:

```
Retrieved: 0 chunks
Sources: []
```

Pipeline không có evidence → synthesis luôn abstain.

**Root cause:**
File index chỉ đọc file và in log:

```
print(f'Indexed: {fname}')
```

nhưng không có `col.add(...)`, nên ChromaDB collection rỗng.

**Cách sửa:**

* Tạo embedding bằng `SentenceTransformer`
* Thêm dữ liệu vào ChromaDB bằng:

```
col.add(ids, documents, embeddings, metadatas)
```

**Bằng chứng trước/sau:**

**Trước:**

```
Retrieved: 0 chunks
Sources: []
```

**Sau:**

```
Retrieved: 3 chunks
[0.0808] sla_p1_2026.txt: SLA TICKET - ...
```

Sau khi fix:

* Retrieval hoạt động
* Policy có context
* Synthesis tạo được answer grounded

---

## 4. Tôi tự đánh giá đóng góp của mình 
**Tôi làm tốt nhất ở điểm nào?**
Tôi hiểu rõ contract giữa các worker và đảm bảo output của từng worker khớp schema. Đặc biệt là xử lý fallback trong synthesis để hệ thống không phụ thuộc hoàn toàn vào LLM.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Ban đầu tôi debug sai hướng (nghĩ lỗi retrieval logic), trong khi vấn đề thực sự nằm ở bước indexing.

**Nhóm phụ thuộc vào tôi ở đâu?**
Toàn bộ pipeline phụ thuộc vào worker:

* Retrieval sai → không có evidence
* Policy sai → rule sai
* Synthesis sai → answer fail

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc vào:

* Supervisor routing đúng
* MCP server trả dữ liệu đúng format

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? 

Tôi sẽ implement chunking cho retrieval thay vì mỗi file là 1 document.

Lý do: trong trace hiện tại có nhiều chunk score `0.000`, cho thấy retrieval chưa chính xác. Nếu chia nhỏ tài liệu (~300–500 tokens), hệ thống sẽ retrieve đúng phần liên quan hơn và cải thiện chất lượng answer của synthesis.

---


