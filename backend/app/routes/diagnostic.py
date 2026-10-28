import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..services.questions import questions_for, load_questions
from ..services.scoring import score_open_answer

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])


class AnswerIn(BaseModel):
    question_id: str
    answer: str


class SubmitIn(BaseModel):
    answers: list[AnswerIn]
class RetryIn(BaseModel):
    question_id: str

@router.get("/questions")
def get_questions(m: models.Membership = Depends(current_membership)):
    qs = questions_for(m.job_role, m.seniority)
    # don't leak scoring points to the client
    return [
        {k: v for k, v in q.items() if k != "points"} | (
            {"options": [o["text"] for o in q["options"]]} if q["type"] == "mcq" else {}
        )
        for q in qs
    ]

def mask_pii(text:str)->str:
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]', text)
    text = re.sub(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', '[REDACTED_PHONE]', text)
    return text
@router.post("/submit")
def submit(body: SubmitIn, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    bank = {q["id"]: q for q in load_questions()}
    assigned = questions_for(m.job_role, m.seniority)
    assigned_ids = {q["id"] for q in assigned}
    submitted_ids = {a.question_id for a in body.answers}
    if len(submitted_ids) != len(body.answers):
        raise HTTPException(400, "Duplicate question IDs in submission")
    if set(submitted_ids) != assigned_ids:
        raise HTTPException(400, "Submitted questions do not match assigned questions")
    db.query(models.Response).filter_by(membership_id=m.id).delete()
    for a in body.answers:
        q = bank.get(a.question_id)
        if not q:
            raise HTTPException(400, f"Unknown question {a.question_id}")
        resp = models.Response(membership_id=m.id, question_id=q["id"], answer=a.answer)
        if q["type"] == "mcq":
            option = next((o for o in q["options"] if o["text"] == a.answer), None)
            if option is None:
                raise HTTPException(400, f"Invalid option for {q['id']}")
            resp.score = option["points"]
        else:
            sanitized=mask_pii(a.answer)
            resp.answer=sanitized
            result = score_open_answer(q["text"], sanitized)
            resp.score = result["score"]
            resp.reason = result["reason"]
            resp.flags = result["flags"]
        db.add(resp)
    db.commit()
    return {"saved": len(body.answers)}

@router.post("/retry")
def retry_scoring(body: RetryIn, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    resp = db.query(models.Response).filter_by(membership_id=m.id, question_id=body.question_id).first()
    if not resp:
        raise HTTPException(404, "Response not found")
    if resp.score is not None:
        return {"status": "already_scored", "score": resp.score}
    bank = {q["id"]: q for q in load_questions()}
    q = bank.get(resp.question_id)
    if not q or q["type"] == "mcq":
        raise HTTPException(400, "Only open-ended questions can be rescored")
    result = score_open_answer(q["text"], resp.answer, is_retry=True)
    resp.score = result["score"]
    resp.reason = result["reason"]
    resp.flags = result["flags"]
    db.commit()
    return {"status": "scored" if resp.score is not None else "failed", "score": resp.score}