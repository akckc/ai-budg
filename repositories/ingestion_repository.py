from db import get_db


def record_ingestion_run(filename: str, inserted_count: int, skipped_count: int) -> dict:
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO ingestion_runs (filename, inserted_count, skipped_count)
            VALUES (?, ?, ?)
            """,
            (filename, inserted_count, skipped_count),
        )

        row = conn.execute(
            """
            SELECT id, filename, inserted_count, skipped_count, timestamp
            FROM ingestion_runs
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        return {
            "id": row[0],
            "filename": row[1],
            "inserted_count": row[2],
            "skipped_count": row[3],
            "timestamp": row[4],
        }
    finally:
        conn.close()


def get_ingestion_history(limit: int = 100) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, filename, inserted_count, skipped_count, timestamp
            FROM ingestion_runs
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [
            {
                "id": r[0],
                "filename": r[1],
                "inserted_count": r[2],
                "skipped_count": r[3],
                "timestamp": r[4],
            }
            for r in rows
        ]
    finally:
        conn.close()
