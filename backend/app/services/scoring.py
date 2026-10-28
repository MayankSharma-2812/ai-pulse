import json

from . import llm


def score_open_answer(question_text: str, answer: str, is_retry: bool = False) -> dict:
    try:
        if not is_retry and "timeout" in answer.lower():
            raise TimeoutError("Simulated AI provider timeout")
        raw = llm.score_answer(question_text, answer).replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        return {"score": data.get("score"), "reason": data.get("reason"), "flags": data.get("flags", [])}
    except Exception:
        return {"score": None, "reason": "Error scoring answer", "flags": []}