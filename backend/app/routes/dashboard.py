from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..services.questions import questions_for

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def level_for(avg):
    if avg is None:
        return "Not assessed"
    if avg < 1.5:
        return "Beginner"
    if avg < 2.5:
        return "Exploring"
    if avg < 3.5:
        return "Practitioner"
    return "Leader"


def _evaluate_member(dm: models.Membership, db: Session):
    assigned = questions_for(dm.job_role, dm.seniority)
    if not assigned:
        return False, [], []
    assigned_ids = {q["id"] for q in assigned}
    rows = db.query(models.Response).filter_by(membership_id=dm.id).all()
    answered_ids = {r.question_id for r in rows}
    if not assigned_ids.issubset(answered_ids):
        return False, [], []
    scores = [r.score for r in rows if r.score is not None and r.question_id in assigned_ids]
    flags = [f for r in rows if r.question_id in assigned_ids for f in (r.flags or [])]
    return True, scores, flags


@router.get("")
def org_dashboard(org_id: int, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    if m.role != "admin":
        raise HTTPException(403, "Admins only")
    if m.org_id != org_id:
        raise HTTPException(403, "Access denied to this organization")

    org = db.get(models.Organization, org_id)
    if not org:
        raise HTTPException(404, "Organization not found")

    members = db.query(models.Membership).filter_by(org_id=org_id).all()
    departments = []
    all_flags = {}
    for dept in org.departments:
        dept_members = [x for x in members if x.department_id == dept.id]
        dept_scores = []
        dept_flags = []
        responded = 0
        for dm in dept_members:
            complete, m_scores, m_flags = _evaluate_member(dm, db)
            if complete:
                responded += 1
                dept_scores.extend(m_scores)
                dept_flags.extend(m_flags)

        if responded >= 5:
            avg = sum(dept_scores) / len(dept_scores) if dept_scores else None
            level = level_for(avg)
            for f in dept_flags:
                all_flags[f] = all_flags.get(f, 0) + 1
        else:
            avg = None
            level = "Not assessed"

        departments.append({
            "department": dept.name,
            "employees": len(dept_members),
            "responded": responded,
            "average_score": round(avg, 2) if avg is not None else None,
            "level": level,
        })

    return {
        "organization": org.name,
        "departments": departments,
        "top_risks": sorted(all_flags.items(), key=lambda kv: -kv[1])[:5],
    }
