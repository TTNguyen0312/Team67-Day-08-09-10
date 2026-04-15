"""
Expectation suite đơn giản (không bắt buộc Great Expectations).

Sinh viên có thể thay bằng GE / pydantic / custom — miễn là có halt có kiểm soát.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class ExpectationResult:
    name: str
    passed: bool
    severity: str  # "warn" | "halt"
    detail: str


def run_expectations(cleaned_rows: List[Dict[str, Any]]) -> Tuple[List[ExpectationResult], bool]:
    """
    Trả về (results, should_halt).

    should_halt = True nếu có bất kỳ expectation severity halt nào fail.
    """
    results: List[ExpectationResult] = []

    # E1: có ít nhất 1 dòng sau clean
    ok = len(cleaned_rows) >= 1
    results.append(
        ExpectationResult(
            "min_one_row",
            ok,
            "halt",
            f"cleaned_rows={len(cleaned_rows)}",
        )
    )

    # E2: không doc_id rỗng
    bad_doc = [r for r in cleaned_rows if not (r.get("doc_id") or "").strip()]
    ok2 = len(bad_doc) == 0
    results.append(
        ExpectationResult(
            "no_empty_doc_id",
            ok2,
            "halt",
            f"empty_doc_id_count={len(bad_doc)}",
        )
    )

    # E3: policy refund không được chứa cửa sổ sai 14 ngày (sau khi đã fix)
    bad_refund = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "policy_refund_v4"
        and "14 ngày làm việc" in (r.get("chunk_text") or "")
    ]
    ok3 = len(bad_refund) == 0
    results.append(
        ExpectationResult(
            "refund_no_stale_14d_window",
            ok3,
            "halt",
            f"violations={len(bad_refund)}",
        )
    )

    # E4: chunk_text đủ dài
    short = [r for r in cleaned_rows if len((r.get("chunk_text") or "")) < 8]
    ok4 = len(short) == 0
    results.append(
        ExpectationResult(
            "chunk_min_length_8",
            ok4,
            "warn",
            f"short_chunks={len(short)}",
        )
    )

    # E5: effective_date đúng định dạng ISO sau clean (phát hiện parser lỏng)
    iso_bad = [
        r
        for r in cleaned_rows
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", (r.get("effective_date") or "").strip())
    ]
    ok5 = len(iso_bad) == 0
    results.append(
        ExpectationResult(
            "effective_date_iso_yyyy_mm_dd",
            ok5,
            "halt",
            f"non_iso_rows={len(iso_bad)}",
        )
    )

    # E6: không còn marker phép năm cũ 10 ngày trên doc HR (conflict version sau clean)
    bad_hr_annual = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "hr_leave_policy"
        and "10 ngày phép năm" in (r.get("chunk_text") or "")
    ]
    ok6 = len(bad_hr_annual) == 0
    results.append(
        ExpectationResult(
            "hr_leave_no_stale_10d_annual",
            ok6,
            "halt",
            f"violations={len(bad_hr_annual)}",
        )
    )

    # E7: chunk_text không quá dài (> 1000 ký tự làm loãng ngữ cảnh RAG)
    # Severity: warn — chunk dài không sai về mặt dữ liệu, nhưng làm giảm chất lượng retrieval.
    # Metric impact: long_chunks tăng khi inject chunk mô tả rất dài vào Sprint 3.
    long = [r for r in cleaned_rows if len((r.get("chunk_text") or "")) > 1000]
    ok7 = len(long) == 0
    results.append(
        ExpectationResult(
            "chunk_max_length_1000",
            ok7,
            "warn",
            f"long_chunks={len(long)}",
        )
    )

    # E8: chunk_id phải duy nhất trong toàn bộ tập cleaned
    # Severity: halt — chunk_id trùng khiến Chroma upsert ghi đè vector sai,
    # phá vỡ tính idempotent của embed và gây lỗi retrieval không thể phát hiện.
    # Metric impact: duplicate_chunk_ids > 0 khi cleaning_rules sinh ra cùng hash
    # (ví dụ hai dòng giống hệt nhau lọt qua dedup do bug, hoặc inject Sprint 3 thêm bản sao).
    all_ids = [r.get("chunk_id", "") for r in cleaned_rows]
    duplicate_ids = len(all_ids) - len(set(all_ids))
    ok8 = duplicate_ids == 0
    results.append(
        ExpectationResult(
            "unique_chunk_id",
            ok8,
            "halt",
            f"duplicate_chunk_ids={duplicate_ids}",
        )
    )

    # E9: không còn thẻ HTML trong chunk_text sau clean
    # Severity: halt — HTML tags (<b>...</b>, <p>...</p>, v.v.) thay đổi ngữ nghĩa embedding
    # và có thể rò rỉ cấu trúc markup vào RAG context, gây câu trả lời không nhất quán.
    # Metric impact: html_contaminated_chunks > 0 khi inject chunk có HTML mà Rule 8 bị tắt.
    _html_re = re.compile(r"<[^>]+>")
    html_dirty = [r for r in cleaned_rows if _html_re.search(r.get("chunk_text") or "")]
    ok9 = len(html_dirty) == 0
    results.append(
        ExpectationResult(
            "no_html_tags_in_chunk_text",
            ok9,
            "halt",
            f"html_contaminated_chunks={len(html_dirty)}",
        )
    )

    # E10: không còn audit tag hệ thống hoặc ghi chú nội bộ trong chunk_text sau clean
    # Severity: halt — "[cleaned: ...]" và "(ghi chú: ...)" là nhiễu hệ thống không thuộc
    # nội dung policy; nếu còn tồn tại sau clean, RAG sẽ trả về context bị nhiễu và
    # eval `contains_expected` có thể pass sai do keywords nằm trong phần ghi chú.
    # Metric impact: noise_contaminated_chunks > 0 khi Rules 9–10 bị bỏ qua trong inject.
    _audit_re = re.compile(r"\[cleaned:")
    _note_re = re.compile(r"\(ghi chú:")
    noise_dirty = [
        r for r in cleaned_rows
        if _audit_re.search(r.get("chunk_text") or "") or _note_re.search(r.get("chunk_text") or "")
    ]
    ok10 = len(noise_dirty) == 0
    results.append(
        ExpectationResult(
            "no_system_noise_in_chunk_text",
            ok10,
            "halt",
            f"noise_contaminated_chunks={len(noise_dirty)}",
        )
    )

    # E11: tỷ lệ exported_at được điền phải đạt ≥ 80%
    # Severity: warn — trường exported_at là watermark freshness; nếu thiếu, freshness_check
    # fallback về run_timestamp (thời điểm pipeline chạy), che khuất độ trễ thực tế của dữ liệu.
    # Metric impact: missing_exported_at_rate tăng khi source export bỏ cột hoặc inject
    # thêm dòng không có timestamp → freshness SLA không còn phản ánh đúng data lag.
    missing_ts = [r for r in cleaned_rows if not (r.get("exported_at") or "").strip()]
    coverage_rate = 1.0 - (len(missing_ts) / len(cleaned_rows)) if cleaned_rows else 0.0
    ok11 = coverage_rate >= 0.80
    results.append(
        ExpectationResult(
            "exported_at_coverage_80pct",
            ok11,
            "warn",
            f"missing_exported_at={len(missing_ts)} coverage={round(coverage_rate * 100, 1)}%",
        )
    )

    # E12: ít nhất 3 doc_id khác nhau trong cleaned output
    # Severity: warn — nếu một nguồn tài liệu bị quarantine hoàn toàn (ví dụ toàn bộ chunk
    # sla_p1_2026 hoặc it_helpdesk_faq bị reject do corrupt), RAG mất knowledge base đó
    # nhưng pipeline vẫn exit 0. Expectation này phát hiện "blind spot" về coverage sớm.
    # Metric impact: distinct_doc_ids giảm xuống < 3 khi inject Sprint 3 corrupt một loại doc_id
    # về future_exported_at hoặc unknown_doc_id → toàn bộ source đó bị quarantine.
    distinct_docs = len({r.get("doc_id", "") for r in cleaned_rows if r.get("doc_id")})
    ok12 = distinct_docs >= 3
    results.append(
        ExpectationResult(
            "doc_id_diversity_min_3",
            ok12,
            "warn",
            f"distinct_doc_ids={distinct_docs}",
        )
    )

    halt = any(not r.passed and r.severity == "halt" for r in results)
    return results, halt


if __name__ == "__main__":
    dummy = [
        {"chunk_id": "id_1", "doc_id": "policy_refund_v4", "chunk_text": "Hoàn tiền trong 7 ngày làm việc.", "effective_date": "2026-01-01"},
        {"chunk_id": "id_2", "doc_id": "hr_leave_policy",  "chunk_text": "Nhân viên có 12 ngày phép năm.", "effective_date": "2026-03-01"},
    ]
    results, halt = run_expectations(dummy)
    count = 1
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"{count}. [{r.severity.upper()}] [{status.upper()}] {r.name}: - {r.detail}")
        count += 1
    print(f"\nshould_halt = {halt}")