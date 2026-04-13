"""
Prompt templates for LLM-as-Judge evaluation
===================================================================
Tập trung tất cả judge prompts ở đây để dễ chỉnh sửa và A/B test prompt.
Viết bằng tiếng Việt để LLM chấm ổn định hơn với nội dung tiếng Việt.
"""


def build_answer_relevance_prompt(query: str, answer: str) -> str:
    """
    Answer Relevance judge prompt.
    Đánh giá: câu trả lời có trả lời đúng câu hỏi người dùng không?

    Args:
        query: Câu hỏi gốc của người dùng
        answer: Câu trả lời của RAG pipeline cần chấm

    Returns:
        Prompt string sẵn sàng gửi cho LLM judge
    """
    return f"""Bạn là một chuyên gia đánh giá hệ thống RAG. Nhiệm vụ của bạn là chấm điểm mức độ liên quan của câu trả lời so với câu hỏi.

Chỉ đánh giá xem câu trả lời có đúng trọng tâm câu hỏi không — không đánh giá tính chính xác của thông tin.

Lưu ý đặc biệt: Nếu câu trả lời là "Không tìm thấy thông tin trong tài liệu hiện có." hoặc tương tự,
đây là hành vi abstain đúng đắn khi không có đủ thông tin — chấm điểm 5 nếu câu hỏi thực sự không có trong tài liệu,
chấm điểm 1 nếu câu hỏi rõ ràng có thể trả lời được từ context nhưng model lại abstain.

Thang điểm (1-5):
  5 = Câu trả lời trả lời trực tiếp và đầy đủ câu hỏi, HOẶC abstain đúng khi không có thông tin
  4 = Phần lớn đúng trọng tâm, thiếu một khía cạnh nhỏ của câu hỏi
  3 = Có liên quan nhưng chưa đúng trọng tâm chính
  2 = Chỉ liên quan một phần, phần lớn lạc đề
  1 = Không trả lời câu hỏi, HOẶC abstain sai khi context có đủ thông tin để trả lời

Câu hỏi:
{query}

Câu trả lời cần chấm:
{answer}

Chỉ trả về JSON hợp lệ, không có markdown, không giải thích ngoài JSON:
{{"score": <số nguyên 1-5>, "reason": "<một câu giải thích ngắn gọn bằng tiếng Việt>"}}"""


def build_context_recall_prompt(query: str, context_str: str, expected_sources: list) -> str:
    """
    Context Recall judge prompt.
    Đánh giá: retrieved context có chứa đủ thông tin để trả lời câu hỏi không?

    Args:
        query: Câu hỏi gốc của người dùng
        context_str: Toàn bộ retrieved chunks đã được format thành chuỗi
        expected_sources: Danh sách tên file/source cần có trong retrieved chunks

    Returns:
        Prompt string sẵn sàng gửi cho LLM judge
    """
    sources_str = ", ".join(expected_sources) if expected_sources else "không xác định"
    return f"""Bạn là một chuyên gia đánh giá hệ thống RAG. Nhiệm vụ của bạn là chấm điểm mức độ đầy đủ của context được retrieve so với câu hỏi.
Các nguồn tài liệu cần có: {sources_str}

Thang điểm (1-5):
  5 = Context chứa đầy đủ thông tin cần thiết để trả lời câu hỏi
  4 = Context gần đủ, thiếu một chi tiết nhỏ
  3 = Context chứa một phần thông tin cần thiết, thiếu một số nội dung quan trọng
  2 = Context phần lớn không đủ, thiếu thông tin chủ yếu
  1 = Context gần như không có thông tin liên quan đến câu hỏi

Câu hỏi:
{query}

Context đã retrieve:
{context_str}

Chỉ trả về JSON hợp lệ, không có markdown, không giải thích ngoài JSON:
{{"score": <số nguyên 1-5>, "reason": "<một câu giải thích ngắn gọn bằng tiếng Việt>"}}"""


def build_completeness_prompt(query: str, answer: str, expected_answer: str) -> str:
    """
    Completeness judge prompt.
    Đánh giá: answer có bao phủ đủ các điểm quan trọng trong expected_answer không?

    Args:
        query: Câu hỏi gốc của người dùng
        answer: Câu trả lời của RAG pipeline cần chấm
        expected_answer: Câu trả lời mẫu (ground truth)

    Returns:
        Prompt string sẵn sàng gửi cho LLM judge
    """
    return f"""Bạn là một chuyên gia đánh giá hệ thống RAG. Nhiệm vụ của bạn là so sánh câu trả lời của model với câu trả lời mẫu và chấm điểm mức độ đầy đủ.

Không trừ điểm vì cách diễn đạt khác nhau — chỉ trừ điểm khi thiếu thông tin quan trọng.

Thang điểm (1-5):
  5 = Câu trả lời bao gồm đủ tất cả các điểm quan trọng trong câu trả lời mẫu
  4 = Thiếu một chi tiết nhỏ
  3 = Thiếu một số thông tin quan trọng
  2 = Thiếu nhiều thông tin quan trọng
  1 = Thiếu phần lớn nội dung cốt lõi

Câu hỏi:
{query}

Câu trả lời mẫu (ground truth):
{expected_answer}

Câu trả lời cần chấm:
{answer}

Chỉ trả về JSON hợp lệ, không có markdown, không giải thích ngoài JSON:
{{"score": <số nguyên 1-5>, "reason": "<một câu giải thích ngắn gọn bằng tiếng Việt>", "missing_points": ["<điểm thiếu 1>", "<điểm thiếu 2>"]}}"""


def build_faithfulness_prompt(answer: str, context_str: str) -> str:
    """
    Faithfulness judge prompt.
    Đánh giá: câu trả lời có bám đúng retrieved context không?

    Args:
        answer: Câu trả lời của RAG pipeline cần chấm
        context_str: Toàn bộ retrieved chunks đã được format thành chuỗi

    Returns:
        Prompt string sẵn sàng gửi cho LLM judge
    """
    return f"""Bạn là một chuyên gia đánh giá hệ thống RAG. Nhiệm vụ của bạn là chấm điểm mức độ bám sát context của câu trả lời.

Chỉ dựa vào context được cung cấp để đánh giá — không dùng kiến thức bên ngoài.

Lưu ý đặc biệt: Nếu câu trả lời là "Không tìm thấy thông tin trong tài liệu hiện có." hoặc tương tự,
đây là hành vi abstain — KHÔNG phải hallucination. Chấm điểm 5 vì model không bịa thêm thông tin.

Thang điểm (1-5):
  5 = Mọi thông tin trong câu trả lời đều có căn cứ trực tiếp từ context, HOẶC model abstain đúng
  4 = Gần như hoàn toàn bám context, một chi tiết nhỏ chưa chắc chắn
  3 = Phần lớn bám context, một số thông tin có thể từ kiến thức của model
  2 = Nhiều thông tin không có trong context
  1 = Câu trả lời phần lớn bịa đặt hoặc mâu thuẫn với context

Context đã retrieve:
{context_str}

Câu trả lời cần chấm:
{answer}

Chỉ trả về JSON hợp lệ, không có markdown, không giải thích ngoài JSON:
{{"score": <số nguyên 1-5>, "reason": "<một câu giải thích ngắn gọn bằng tiếng Việt>"}}"""
