"""The project risk register the briefing, the change triage and the investigation share.

The briefing adds expected risks; the triage and the investigation link signals and notices to
them. Status only moves forward on its own; a person can set any status. Each change is kept in
the risk's history with who made it and from which event or run.
"""

from __future__ import annotations

from typing import Any

from .storage import Store, digest, utcnow

STATUSES = ("EXPECTED", "SIGNAL_DETECTED", "OCCURRED", "RESPONDING", "CLOSED")
STATUS_LABEL = {"EXPECTED": "예상됨", "SIGNAL_DETECTED": "신호 감지", "OCCURRED": "발생",
                "RESPONDING": "대응 중", "CLOSED": "종결"}
ACTOR_LABEL = {"briefing": "등록 시 브리핑", "triage": "변화 자동 추리기", "investigation": "사후 조사 에이전트",
               "person": "사람"}


def _row_id(project_id: str, risk_id: str) -> str:
    return digest({"project_id": project_id, "risk_id": risk_id})[:32]


def list_risks(db: Store, project_id: str) -> list[dict[str, Any]]:
    rows = [row["data"] for row in db.list_json("risks", project_id, 200)]
    return sorted(rows, key=lambda row: (int(row.get("rank") or 99), str(row.get("risk_id"))))


def get_risk(db: Store, project_id: str, risk_id: str) -> dict[str, Any] | None:
    row = db.get_json("risks", _row_id(project_id, risk_id), project_id)
    return row["data"] if row else None


def _save(db: Store, project_id: str, risk: dict[str, Any]) -> None:
    row_id = _row_id(project_id, risk["risk_id"])
    existing = db.get_json("risks", row_id, project_id)
    db.put_json("risks", row_id, risk, project_id=project_id,
                created_at=existing["created_at"] if existing else utcnow())


def register_expected(db: Store, project_id: str, version_id: str, risks: list[dict[str, Any]],
                      actor: str = "briefing", note: str = "") -> list[dict[str, Any]]:
    """Replace the expected risks of a baseline; risks already linked to a signal are kept as they are."""
    current = {row["risk_id"]: row for row in list_risks(db, project_id)}
    for risk_id, row in current.items():
        if row.get("version_id") != version_id and row.get("status") == "EXPECTED":
            db_row = db.get_json("risks", _row_id(project_id, risk_id), project_id)
            if db_row:
                with db.transaction() as conn:
                    conn.execute("DELETE FROM risks WHERE id=?", (db_row["id"],))
    saved = []
    for item in risks:
        previous = current.get(item["risk_id"])
        if previous and previous.get("status") != "EXPECTED":
            saved.append(previous)
            continue
        risk = {**item, "version_id": version_id, "status": "EXPECTED", "links": [],
                "history": [{"at": utcnow(), "status": "EXPECTED", "actor": actor,
                             "note": note or "기준 일정 등록 때 예상한 위험"}]}
        _save(db, project_id, risk)
        saved.append(risk)
    return saved


def link(db: Store, project_id: str, risk_id: str, status: str, actor: str, note: str,
         event_id: str | None = None, run_id: str | None = None, quote: str = "") -> dict[str, Any] | None:
    """Record that a signal or notice shares this risk's cause; the status moves forward only."""
    risk = get_risk(db, project_id, risk_id)
    if not risk or status not in STATUSES:
        return None
    entry = {"at": utcnow(), "actor": actor, "event_id": event_id, "run_id": run_id, "note": note, "quote": quote}
    links = [row for row in risk.get("links") or []
             if not (row.get("event_id") == event_id and row.get("actor") == actor)]
    risk["links"] = links + [{**entry, "status": status}]
    moved = STATUSES.index(status) > STATUSES.index(risk.get("status") or "EXPECTED")
    if moved:
        risk["status"] = status
    risk.setdefault("history", []).append({**entry, "status": risk["status"], "moved": moved})
    _save(db, project_id, risk)
    return risk


def set_status(db: Store, project_id: str, risk_id: str, status: str, note: str) -> dict[str, Any] | None:
    """A person sets any status, forward or back."""
    risk = get_risk(db, project_id, risk_id)
    if not risk or status not in STATUSES:
        return None
    risk["status"] = status
    risk.setdefault("history", []).append({"at": utcnow(), "status": status, "actor": "person", "note": note,
                                           "moved": True})
    _save(db, project_id, risk)
    return risk


def advance_linked(db: Store, project_id: str, event_id: str, status: str, actor: str, note: str,
                   run_id: str | None = None) -> list[str]:
    """Move every risk already linked to an event forward (after a person's confirmation or a commit)."""
    moved = []
    for risk in list_risks(db, project_id):
        if any(row.get("event_id") == event_id for row in risk.get("links") or []):
            if link(db, project_id, risk["risk_id"], status, actor, note, event_id=event_id, run_id=run_id):
                moved.append(risk["risk_id"])
    return moved


def model_view(db: Store, project_id: str) -> list[dict[str, Any]]:
    """What an agent reads before judging a new signal: the cause and scope, not status or history."""
    return [{**{key: risk.get(key) for key in ("risk_id", "title", "cause", "task_ids", "item_ids")},
             **({"linked_cause": {key: risk["linked_cause"].get(key) for key in ("text", "case_ids")}}
                if risk.get("linked_cause") else {})}
            for risk in list_risks(db, project_id) if risk.get("status") != "CLOSED"]
