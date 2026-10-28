import json

from . import llm


def score_open_answer(question_text: str, answer: str) -> dict:
    try:
        raw=llm.score_answer(question_text, answer).replace("```json", "").replace("```", "").strip()
        data=json.loads(raw)
        return {"score": data.get("score"), "reason": data.get("reason"), "flags": data.get("flags", [])}
    except Exception:
        return {"score": None, "reason": "Error scoring answer", "flags": []}