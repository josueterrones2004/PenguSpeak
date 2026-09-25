import sqlite3

DB_PATH = "penguspeak.db"
DEFAULT_VOICE = "edge_jorge"


# ============================================================
# CACHÉ EN RAM
# ============================================================

voice_cache = {}
nickname_cache = {}


# ============================================================
# INICIALIZACIÓN
# ============================================================

def init_database():
    with sqlite3.connect(
        DB_PATH
    ) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                voice_id TEXT NOT NULL DEFAULT 'edge_jorge',
                nickname TEXT
            )
            """
        )

        rows = connection.execute(
            """
            SELECT
                user_id,
                voice_id,
                nickname
            FROM users
            """
        ).fetchall()

        connection.commit()

    voice_cache.clear()
    nickname_cache.clear()

    for (
        user_id,
        voice_id,
        nickname,
    ) in rows:
        voice_cache[
            user_id
        ] = voice_id

        nickname_cache[
            user_id
        ] = nickname

    print(
        "[DB] Caché cargada: "
        f"{len(rows)} usuarios"
    )


# ============================================================
# OBTENER VOZ
# ============================================================

def get_user_voice(
    user_id,
    valid_voices,
):
    voice_id = voice_cache.get(
        user_id,
        DEFAULT_VOICE,
    )

    if voice_id not in valid_voices:
        return DEFAULT_VOICE

    return voice_id


# ============================================================
# CAMBIAR VOZ
# ============================================================

def set_user_voice(
    user_id,
    voice_id,
):
    with sqlite3.connect(
        DB_PATH
    ) as connection:
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

    voice_cache[
        user_id
    ] = voice_id

    nickname_cache.setdefault(
        user_id,
        None,
    )


# ============================================================
# OBTENER APODO
# ============================================================

def get_nickname(
    user_id,
):
    return nickname_cache.get(
        user_id
    )


# ============================================================
# CAMBIAR APODO
# ============================================================

def set_nickname(
    user_id,
    nickname,
):
    with sqlite3.connect(
        DB_PATH
    ) as connection:
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

    nickname_cache[
        user_id
    ] = nickname

    voice_cache.setdefault(
        user_id,
        DEFAULT_VOICE,
    )


# ============================================================
# QUITAR APODO
# ============================================================

def remove_nickname(
    user_id,
):
    with sqlite3.connect(
        DB_PATH
    ) as connection:
        connection.execute(
            """
            UPDATE users
            SET nickname = NULL
            WHERE user_id = ?
            """,
            (
                user_id,
            ),
        )

        connection.commit()

    nickname_cache[
        user_id
    ] = None