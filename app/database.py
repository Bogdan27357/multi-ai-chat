"""SQLite database for employee personal files (личные дела)."""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "employees.db"))


def _ensure_db_dir():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            surname TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL DEFAULT '',
            patronymic TEXT NOT NULL DEFAULT '',
            birth_date TEXT DEFAULT '',
            birth_place TEXT DEFAULT '',
            gender TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            department TEXT DEFAULT '',
            position TEXT DEFAULT '',
            hire_date TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS employee_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            doc_type TEXT NOT NULL,
            fields_json TEXT NOT NULL DEFAULT '{}',
            ocr_text TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


# ---- Employees CRUD ----

def create_employee(data: dict) -> int:
    now = datetime.now().isoformat()
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO employees
           (surname, name, patronymic, birth_date, birth_place, gender,
            phone, email, department, position, hire_date, notes,
            created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("surname", ""),
            data.get("name", ""),
            data.get("patronymic", ""),
            data.get("birth_date", ""),
            data.get("birth_place", ""),
            data.get("gender", ""),
            data.get("phone", ""),
            data.get("email", ""),
            data.get("department", ""),
            data.get("position", ""),
            data.get("hire_date", ""),
            data.get("notes", ""),
            now, now,
        ),
    )
    conn.commit()
    emp_id = cur.lastrowid
    conn.close()
    return emp_id


def get_employee(employee_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def list_employees(search: str = "") -> list[dict]:
    conn = get_connection()
    if search:
        like = f"%{search}%"
        rows = conn.execute(
            """SELECT * FROM employees
               WHERE surname LIKE ? OR name LIKE ? OR patronymic LIKE ?
                  OR department LIKE ? OR position LIKE ?
               ORDER BY surname, name""",
            (like, like, like, like, like),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM employees ORDER BY surname, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_employee(employee_id: int, data: dict) -> bool:
    now = datetime.now().isoformat()
    fields = []
    values = []
    allowed = [
        "surname", "name", "patronymic", "birth_date", "birth_place",
        "gender", "phone", "email", "department", "position", "hire_date", "notes",
    ]
    for key in allowed:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])

    if not fields:
        return False

    fields.append("updated_at = ?")
    values.append(now)
    values.append(employee_id)

    conn = get_connection()
    conn.execute(f"UPDATE employees SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return True


def delete_employee(employee_id: int) -> bool:
    conn = get_connection()
    cur = conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# ---- Employee Documents ----

def add_document(employee_id: int, doc_type: str, fields: dict, ocr_text: str = "") -> int:
    now = datetime.now().isoformat()
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO employee_documents (employee_id, doc_type, fields_json, ocr_text, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (employee_id, doc_type, json.dumps(fields, ensure_ascii=False), ocr_text, now),
    )
    conn.commit()
    doc_id = cur.lastrowid
    conn.close()
    return doc_id


def get_employee_documents(employee_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM employee_documents WHERE employee_id = ? ORDER BY created_at DESC",
        (employee_id,),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["fields"] = json.loads(d.pop("fields_json"))
        result.append(d)
    return result


def delete_document(doc_id: int) -> bool:
    conn = get_connection()
    cur = conn.execute("DELETE FROM employee_documents WHERE id = ?", (doc_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def get_employee_merged_fields(employee_id: int) -> dict:
    """Merge all document fields into a single dict for questionnaire generation.

    Later documents override earlier ones. Employee base info is included too.
    """
    emp = get_employee(employee_id)
    if emp is None:
        return {}

    merged = {
        "surname": emp["surname"],
        "name": emp["name"],
        "patronymic": emp["patronymic"],
        "birth_date": emp["birth_date"],
        "birth_place": emp["birth_place"],
        "gender": emp["gender"],
    }

    docs = get_employee_documents(employee_id)
    # Apply oldest first so newer docs override
    for doc in reversed(docs):
        for k, v in doc["fields"].items():
            if v and not k.startswith("_"):
                merged[k] = v

    return merged
