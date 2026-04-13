"""
Generate logs/grading_run.json from data/grading_questions.json.

Usage:
  python generate_grading_log.py
"""

import json
from datetime import datetime
from pathlib import Path

from rag_answer import rag_answer


LAB_DIR = Path(__file__).parent
IN_PATH = LAB_DIR / "data" / "grading_questions.json"
OUT_PATH = LAB_DIR / "logs" / "grading_run.json"


def main() -> None:
    if not IN_PATH.exists():
        raise FileNotFoundError(
            f"Missing {IN_PATH}. Put grading_questions.json into lab/data/ then rerun."
        )

    questions = json.loads(IN_PATH.read_text(encoding="utf-8"))
    log_rows = []

    for q in questions:
        qid = q.get("id", "")
        question = q.get("question", "")
        result = rag_answer(
            question,
            retrieval_mode="hybrid",
            use_rerank=True,
            use_query_transform=True,
            transform_strategy="expansion",
            verbose=False,
        )
        log_rows.append(
            {
                "id": qid,
                "question": question,
                "answer": result["answer"],
                "sources": result["sources"],
                "chunks_retrieved": len(result.get("chunks_used", [])),
                "retrieval_mode": result.get("config", {}).get("retrieval_mode", "unknown"),
                "timestamp": datetime.now().isoformat(),
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(log_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(log_rows)} rows)")


if __name__ == "__main__":
    main()

"""
Generate logs/grading_run.json from data/grading_questions.json

Usage:
  python generate_grading_log.py

Notes:
  - Expects: data/grading_questions.json (public at grading time)
  - Writes: logs/grading_run.json
"""

import json
from datetime import datetime
from pathlib import Path

from rag_answer import rag_answer


LAB_DIR = Path(__file__).parent
GRADING_QUESTIONS_PATH = LAB_DIR / "data" / "grading_questions.json"
OUT_PATH = LAB_DIR / "logs" / "grading_run.json"


def main() -> None:
    if not GRADING_QUESTIONS_PATH.exists():
        raise FileNotFoundError(
            f"Missing {GRADING_QUESTIONS_PATH}. Put grading_questions.json into data/ then rerun."
        )

    questions = json.loads(GRADING_QUESTIONS_PATH.read_text(encoding="utf-8"))

    log = []
    for q in questions:
        result = rag_answer(
            q["question"],
            retrieval_mode="hybrid",
            use_rerank=True,
            use_query_transform=True,
            transform_strategy="expansion",
            verbose=False,
        )
        log.append(
            {
                "id": q.get("id", ""),
                "question": q["question"],
                "answer": result["answer"],
                "sources": result["sources"],
                "chunks_retrieved": len(result.get("chunks_used", [])),
                "retrieval_mode": result.get("config", {}).get("retrieval_mode", "unknown"),
                "timestamp": datetime.now().isoformat(),
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(log)} rows)")


if __name__ == "__main__":
    main()

