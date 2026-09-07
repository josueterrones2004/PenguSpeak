import sqlite3

DB_PATH = "penguspeak.db"
DEFAULT_VOICE = "edge_jorge"


def init_database():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                voice_id TEXT NOT NULL DEFAULT 'edge_jorge',
                nickname TEXT
            )
            """
        )

        connection.commit()


def get_user_voice(user_id, valid_voices):
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            """
            SELECT voice_id
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if not row:
        return DEFAULT_VOICE

    voice_id = row[0]

    if voice_id not in valid_voices:
        return DEFAULT_VOICE

    return voice_id


def set_user_voice(user_id, voice_id):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO users (
                user_id,
                voice_id
            )
            VALUES (?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                voice_id = excluded.voice_id
            """,
            (
                user_id,
                voice_id,
            ),
        )

        connection.commit()


def get_nickname(user_id):
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            """
            SELECT nickname
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if not row:
        return None

    return row[0]


def set_nickname(user_id, nickname):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO users (
                user_id,
                nickname
            )
            VALUES (?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                nickname = excluded.nickname
            """,
            (
                user_id,
                nickname,
            ),
        )

        connection.commit()


def remove_nickname(user_id):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            UPDATE users
            SET nickname = NULL
            WHERE user_id = ?
            """,
            (user_id,),
        )

        connection.commit()
