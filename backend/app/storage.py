from __future__ import annotations
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Iterator
from uuid import uuid4


_MIGRATION_LOCK = Lock()


class RecordNotFoundError(LookupError):
    pass


class VersionConflictError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def private_root() -> Path:
    project_root = Path(__file__).resolve().parents[2]
    configured = Path(os.getenv("YIDUO_PRIVATE_DIR", "private_data"))
    root = configured if configured.is_absolute() else project_root / configured
    return root.resolve()


class AppStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or private_root()).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.upload_root = self.safe_child("uploads")
        self.upload_root.mkdir(parents=True, exist_ok=True)
        self.database_path = self.safe_child("yiduo.db")
        with _MIGRATION_LOCK:
            self._migrate()

    def safe_child(self, *parts: str) -> Path:
        candidate = self.root.joinpath(*parts).resolve()
        candidate.relative_to(self.root)
        return candidate

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _migrate(self) -> None:
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {
                row["version"]
                for row in connection.execute("SELECT version FROM schema_migrations")
            }
            if 1 not in applied:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS lesson_drafts (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        grade INTEGER NOT NULL,
                        topic TEXT NOT NULL,
                        status TEXT NOT NULL CHECK(status IN ('pending_review', 'approved')),
                        version INTEGER NOT NULL CHECK(version >= 1),
                        teacher_note TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS lesson_draft_items (
                        id TEXT PRIMARY KEY,
                        draft_id TEXT NOT NULL REFERENCES lesson_drafts(id) ON DELETE CASCADE,
                        position INTEGER NOT NULL CHECK(position >= 0),
                        problem_id TEXT NOT NULL,
                        problem_revision_id TEXT NOT NULL,
                        relation TEXT NOT NULL,
                        teacher_prompt TEXT NOT NULL,
                        teaching_note TEXT NOT NULL,
                        problem_snapshot_json TEXT NOT NULL,
                        UNIQUE(draft_id, position),
                        UNIQUE(draft_id, problem_id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_draft_items_draft ON lesson_draft_items(draft_id, position);
                    CREATE TABLE IF NOT EXISTS photo_records (
                        id TEXT PRIMARY KEY,
                        original_name TEXT NOT NULL,
                        stored_name TEXT NOT NULL UNIQUE,
                        content_type TEXT NOT NULL,
                        byte_size INTEGER NOT NULL CHECK(byte_size > 0),
                        width INTEGER NOT NULL CHECK(width > 0),
                        height INTEGER NOT NULL CHECK(height > 0),
                        sha256 TEXT NOT NULL,
                        status TEXT NOT NULL CHECK(status IN ('awaiting_transcription', 'ready')),
                        transcript TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    """
                )
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (1, utc_now()),
                )
            if 2 not in applied:
                connection.execute(
                    "ALTER TABLE lesson_drafts ADD COLUMN plan_snapshot_json TEXT"
                )
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (2, utc_now()),
                )
            if 3 not in applied:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS after_class_feedback (
                        id TEXT PRIMARY KEY,
                        student_name TEXT NOT NULL,
                        grade INTEGER NOT NULL,
                        topic TEXT NOT NULL,
                        lesson_date TEXT NOT NULL,
                        actual_content TEXT NOT NULL,
                        observations_json TEXT NOT NULL,
                        teacher_advice TEXT NOT NULL,
                        homework_json TEXT NOT NULL,
                        class_reminder TEXT NOT NULL DEFAULT '',
                        photo_ids_json TEXT NOT NULL DEFAULT '[]',
                        status TEXT NOT NULL CHECK(status IN ('draft', 'approved')),
                        version INTEGER NOT NULL CHECK(version >= 1),
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_feedback_updated ON after_class_feedback(updated_at DESC);
                    """
                )
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (3, utc_now()),
                )

            connection.execute(
                "CREATE TABLE IF NOT EXISTS feedback_ai_proposals ("
                "id TEXT PRIMARY KEY, feedback_id TEXT NOT NULL REFERENCES after_class_feedback(id) ON DELETE CASCADE, "
                "source_version INTEGER NOT NULL, audience TEXT NOT NULL, body_json TEXT NOT NULL, accepted INTEGER NOT NULL)"
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_feedback_ai ON feedback_ai_proposals(feedback_id, accepted)")

    def save_feedback_proposal(self, feedback_id, expected_version, audience, body):
        proposal_id = str(uuid4())
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._feedback_version(connection, feedback_id, expected_version)
            connection.execute(
                "INSERT INTO feedback_ai_proposals VALUES (?, ?, ?, ?, ?, 0)",
                (proposal_id, feedback_id, expected_version, audience, json.dumps(body, ensure_ascii=False)),
            )
        return proposal_id

    @staticmethod
    def _feedback_version(connection, feedback_id, expected_version):
        row = connection.execute("SELECT version FROM after_class_feedback WHERE id = ?", (feedback_id,)).fetchone()
        if row is None:
            raise RecordNotFoundError("feedback not found")
        if row["version"] != expected_version:
            raise VersionConflictError("课堂记录已变化，请重新打开后再操作。")

    def adopt_feedback_proposal(self, feedback_id, expected_version, proposal_id, audience):
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._feedback_version(connection, feedback_id, expected_version)
            if proposal_id is not None:
                row = connection.execute(
                    "SELECT * FROM feedback_ai_proposals WHERE id = ? AND feedback_id = ? AND audience = ?",
                    (proposal_id, feedback_id, audience),
                ).fetchone()
                if row is None:
                    raise RecordNotFoundError("润色建议不存在")
                if row["source_version"] != expected_version or row["accepted"]:
                    raise VersionConflictError("润色建议已过期，请重新生成。")
            connection.execute(
                "DELETE FROM feedback_ai_proposals WHERE feedback_id = ? AND audience = ? AND accepted = 1",
                (feedback_id, audience),
            )
            if proposal_id is not None:
                connection.execute("UPDATE feedback_ai_proposals SET accepted = 1 WHERE id = ?", (proposal_id,))
            connection.execute(
                "UPDATE after_class_feedback SET status = 'draft', version = version + 1, updated_at = ? WHERE id = ?",
                (utc_now(), feedback_id),
            )
        return self.get_feedback(feedback_id)

    def create_draft(
        self,
        *,
        title: str,
        grade: int,
        topic: str,
        items: list[dict[str, Any]],
        plan_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        draft_id = str(uuid4())
        now = utc_now()
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO lesson_drafts "
                "(id, title, grade, topic, status, version, teacher_note, created_at, updated_at, "
                "plan_snapshot_json) VALUES (?, ?, ?, ?, 'pending_review', 1, '', ?, ?, ?)",
                (
                    draft_id,
                    title,
                    grade,
                    topic,
                    now,
                    now,
                    json.dumps(plan_snapshot, ensure_ascii=False, separators=(",", ":"))
                    if plan_snapshot else None,
                ),
            )
            self._replace_items(connection, draft_id, items, existing_ids=set())
        return self.get_draft(draft_id)

    def list_drafts(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT d.*, COUNT(i.id) AS item_count "
                "FROM lesson_drafts d JOIN lesson_draft_items i ON i.draft_id = d.id "
                "GROUP BY d.id ORDER BY d.updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_draft(self, draft_id: str) -> dict[str, Any]:
        with self.connect() as connection:
            draft = connection.execute(
                "SELECT d.*, COUNT(i.id) AS item_count "
                "FROM lesson_drafts d LEFT JOIN lesson_draft_items i ON i.draft_id = d.id "
                "WHERE d.id = ? GROUP BY d.id",
                (draft_id,),
            ).fetchone()
            if draft is None:
                raise RecordNotFoundError(f"draft not found: {draft_id}")
            items = connection.execute(
                "SELECT * FROM lesson_draft_items WHERE draft_id = ? ORDER BY position",
                (draft_id,),
            ).fetchall()
        result = dict(draft)
        result["plan_snapshot"] = (
            json.loads(result["plan_snapshot_json"])
            if result.get("plan_snapshot_json") else None
        )
        result["items"] = [
            {
                **dict(item),
                "problem_snapshot": json.loads(item["problem_snapshot_json"]),
            }
            for item in items
        ]
        return result

    def update_draft(
        self,
        *,
        draft_id: str,
        expected_version: int,
        title: str,
        teacher_note: str,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        now = utc_now()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT version FROM lesson_drafts WHERE id = ?",
                (draft_id,),
            ).fetchone()
            if current is None:
                raise RecordNotFoundError(f"draft not found: {draft_id}")
            if current["version"] != expected_version:
                raise VersionConflictError(
                    f"draft version changed: expected {expected_version}, current {current['version']}"
                )
            existing_ids = {
                row["id"]
                for row in connection.execute(
                    "SELECT id FROM lesson_draft_items WHERE draft_id = ?",
                    (draft_id,),
                )
            }
            connection.execute(
                "UPDATE lesson_drafts SET title = ?, teacher_note = ?, "
                "status = 'pending_review', version = version + 1, updated_at = ? WHERE id = ?",
                (title, teacher_note, now, draft_id),
            )
            connection.execute("DELETE FROM lesson_draft_items WHERE draft_id = ?", (draft_id,))
            self._replace_items(connection, draft_id, items, existing_ids=existing_ids)
        return self.get_draft(draft_id)

    def review_draft(
        self,
        *,
        draft_id: str,
        expected_version: int,
        status: str,
    ) -> dict[str, Any]:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT version FROM lesson_drafts WHERE id = ?",
                (draft_id,),
            ).fetchone()
            if current is None:
                raise RecordNotFoundError(f"draft not found: {draft_id}")
            if current["version"] != expected_version:
                raise VersionConflictError(
                    f"draft version changed: expected {expected_version}, current {current['version']}"
                )
            connection.execute(
                "UPDATE lesson_drafts SET status = ?, version = version + 1, updated_at = ? WHERE id = ?",
                (status, utc_now(), draft_id),
            )
        return self.get_draft(draft_id)

    def delete_draft(self, draft_id: str) -> None:
        with self.connect() as connection:
            result = connection.execute("DELETE FROM lesson_drafts WHERE id = ?", (draft_id,))
            if result.rowcount == 0:
                raise RecordNotFoundError(f"draft not found: {draft_id}")

    def _replace_items(
        self,
        connection: sqlite3.Connection,
        draft_id: str,
        items: list[dict[str, Any]],
        *,
        existing_ids: set[str],
    ) -> None:
        for position, item in enumerate(items):
            item_id = item.get("id")
            if item_id not in existing_ids:
                item_id = str(uuid4())
            connection.execute(
                "INSERT INTO lesson_draft_items "
                "(id, draft_id, position, problem_id, problem_revision_id, relation, "
                "teacher_prompt, teaching_note, problem_snapshot_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item_id,
                    draft_id,
                    position,
                    item["problem_id"],
                    item["problem_revision_id"],
                    item["relation"],
                    item["teacher_prompt"],
                    item["teaching_note"],
                    json.dumps(item["problem_snapshot"], ensure_ascii=False, separators=(",", ":")),
                ),
            )

    def create_photo(
        self,
        *,
        original_name: str,
        stored_name: str,
        byte_size: int,
        width: int,
        height: int,
        sha256: str,
    ) -> dict[str, Any]:
        photo_id = str(uuid4())
        now = utc_now()
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO photo_records "
                "(id, original_name, stored_name, content_type, byte_size, width, height, "
                "sha256, status, transcript, created_at, updated_at) "
                "VALUES (?, ?, ?, 'image/png', ?, ?, ?, ?, 'awaiting_transcription', '', ?, ?)",
                (photo_id, original_name, stored_name, byte_size, width, height, sha256, now, now),
            )
        return self.get_photo(photo_id)

    def list_photos(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM photo_records ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_photo(self, photo_id: str) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM photo_records WHERE id = ?",
                (photo_id,),
            ).fetchone()
        if row is None:
            raise RecordNotFoundError(f"photo not found: {photo_id}")
        return dict(row)

    def update_transcript(self, photo_id: str, transcript: str) -> dict[str, Any]:
        with self.connect() as connection:
            result = connection.execute(
                "UPDATE photo_records SET transcript = ?, status = 'ready', updated_at = ? WHERE id = ?",
                (transcript, utc_now(), photo_id),
            )
            if result.rowcount == 0:
                raise RecordNotFoundError(f"photo not found: {photo_id}")
        return self.get_photo(photo_id)

    def delete_photo(self, photo_id: str) -> Path:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT stored_name FROM photo_records WHERE id = ?",
                (photo_id,),
            ).fetchone()
            if row is None:
                raise RecordNotFoundError(f"photo not found: {photo_id}")
            connection.execute("DELETE FROM photo_records WHERE id = ?", (photo_id,))
        path = self.safe_child("uploads", row["stored_name"])
        return path

    def photo_is_used(self, photo_id: str) -> bool:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT photo_ids_json FROM after_class_feedback"
            ).fetchall()
        return any(photo_id in json.loads(row["photo_ids_json"]) for row in rows)

    def create_feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        feedback_id = str(uuid4())
        now = utc_now()
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO after_class_feedback "
                "(id, student_name, grade, topic, lesson_date, actual_content, observations_json, "
                "teacher_advice, homework_json, class_reminder, photo_ids_json, status, version, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', 1, ?, ?)",
                (
                    feedback_id,
                    payload["student_name"],
                    payload["grade"],
                    payload["topic"],
                    payload["lesson_date"],
                    payload["actual_content"],
                    json.dumps(payload["observations"], ensure_ascii=False, separators=(",", ":")),
                    payload["teacher_advice"],
                    json.dumps(payload["homework"], ensure_ascii=False, separators=(",", ":")),
                    payload["class_reminder"],
                    json.dumps(payload["photo_ids"], ensure_ascii=False, separators=(",", ":")),
                    now,
                    now,
                ),
            )
        return self.get_feedback(feedback_id)

    def list_feedback(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, student_name, grade, topic, lesson_date, status, version, created_at, updated_at "
                "FROM after_class_feedback ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_feedback(self, feedback_id: str) -> dict[str, Any]:
        with self.connect() as connection:
            connection.execute("BEGIN")
            row = connection.execute(
                "SELECT * FROM after_class_feedback WHERE id = ?", (feedback_id,)
            ).fetchone()
            reports = connection.execute(
                "SELECT audience, body_json FROM feedback_ai_proposals WHERE feedback_id = ? AND accepted = 1",
                (feedback_id,),
            ).fetchall()
        if row is None:
            raise RecordNotFoundError(f"feedback not found: {feedback_id}")
        result = dict(row)
        result["observations"] = json.loads(result.pop("observations_json"))
        result["homework"] = json.loads(result.pop("homework_json"))
        result["photo_ids"] = json.loads(result.pop("photo_ids_json"))
        result["ai_reports"] = {item["audience"]: json.loads(item["body_json"]) for item in reports}
        return result

    def update_feedback(
        self,
        feedback_id: str,
        expected_version: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT version FROM after_class_feedback WHERE id = ?", (feedback_id,)
            ).fetchone()
            if current is None:
                raise RecordNotFoundError(f"feedback not found: {feedback_id}")
            if current["version"] != expected_version:
                raise VersionConflictError(
                    f"feedback version changed: expected {expected_version}, current {current['version']}"
                )
            connection.execute(
                "UPDATE after_class_feedback SET student_name = ?, grade = ?, topic = ?, lesson_date = ?, "
                "actual_content = ?, observations_json = ?, teacher_advice = ?, homework_json = ?, "
                "class_reminder = ?, photo_ids_json = ?, status = 'draft', version = version + 1, "
                "updated_at = ? WHERE id = ?",
                (
                    payload["student_name"], payload["grade"], payload["topic"], payload["lesson_date"],
                    payload["actual_content"],
                    json.dumps(payload["observations"], ensure_ascii=False, separators=(",", ":")),
                    payload["teacher_advice"],
                    json.dumps(payload["homework"], ensure_ascii=False, separators=(",", ":")),
                    payload["class_reminder"],
                    json.dumps(payload["photo_ids"], ensure_ascii=False, separators=(",", ":")),
                    utc_now(), feedback_id,
                ),
            )
            connection.execute("DELETE FROM feedback_ai_proposals WHERE feedback_id = ?", (feedback_id,))
        return self.get_feedback(feedback_id)

    def review_feedback(
        self, feedback_id: str, expected_version: int, status: str
    ) -> dict[str, Any]:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT version FROM after_class_feedback WHERE id = ?", (feedback_id,)
            ).fetchone()
            if current is None:
                raise RecordNotFoundError(f"feedback not found: {feedback_id}")
            if current["version"] != expected_version:
                raise VersionConflictError(
                    f"feedback version changed: expected {expected_version}, current {current['version']}"
                )
            connection.execute(
                "UPDATE after_class_feedback SET status = ?, version = version + 1, updated_at = ? "
                "WHERE id = ?", (status, utc_now(), feedback_id)
            )
        return self.get_feedback(feedback_id)

    def delete_feedback(self, feedback_id: str) -> None:
        with self.connect() as connection:
            result = connection.execute(
                "DELETE FROM after_class_feedback WHERE id = ?", (feedback_id,)
            )
            if result.rowcount == 0:
                raise RecordNotFoundError(f"feedback not found: {feedback_id}")
