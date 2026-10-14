import sqlite3
DB_PATH = "penguspeak.db"
DEFAULT_EDGE_VOICE = "edge_jorge"
DEFAULT_AZURE_VOICE = "azure_jorge"
# Compatibilidad con el código anterior.
DEFAULT_VOICE = DEFAULT_EDGE_VOICE
# ============================================================
# CACHÉ EN RAM
# ============================================================
voice_cache = {}
edge_voice_cache = {}
azure_voice_cache = {}
nickname_cache = {}
# ============================================================
# INICIALIZACIÓN Y MIGRACIÓN
# ============================================================
def init_database():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                voice_id TEXT NOT NULL DEFAULT 'edge_jorge',
                nickname TEXT,
                edge_voice_id TEXT,
                azure_voice_id TEXT
            )
            """
        )
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }
        if "edge_voice_id" not in columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN edge_voice_id TEXT"
            )
        if "azure_voice_id" not in columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN azure_voice_id TEXT"
            )
        # La voz antigua se convierte en la preferencia Edge.
        # Solo se migran registros que aún no tengan esa preferencia.
        connection.execute(
            """
            UPDATE users
            SET edge_voice_id = COALESCE(
                NULLIF(edge_voice_id, ''),
                voice_id,
                ?
            )
            WHERE edge_voice_id IS NULL
               OR edge_voice_id = ''
            """,
            (DEFAULT_EDGE_VOICE,),
        )
        # Los usuarios sin preferencia Azure reciben una voz inicial.
        connection.execute(
            """
            UPDATE users
            SET azure_voice_id = ?
            WHERE azure_voice_id IS NULL
               OR azure_voice_id = ''
            """,
            (DEFAULT_AZURE_VOICE,),
        )
        # Una única voz lógica para Edge y Azure. Conservamos las columnas
        # antiguas para compatibilidad con los componentes de audio.
        connection.execute("""
            UPDATE users
            SET azure_voice_id = 'azure_' || SUBSTR(edge_voice_id, 6)
            WHERE edge_voice_id LIKE 'edge_%'
        """)

        rows = connection.execute(
            """
            SELECT
                user_id,
                voice_id,
                nickname,
                edge_voice_id,
                azure_voice_id
            FROM users
            """
        ).fetchall()
        connection.commit()
    voice_cache.clear()
    edge_voice_cache.clear()
    azure_voice_cache.clear()
    nickname_cache.clear()
    for (
        user_id,
        voice_id,
        nickname,
        edge_voice_id,
        azure_voice_id,
    ) in rows:
        voice_cache[user_id] = voice_id
        edge_voice_cache[user_id] = (
            edge_voice_id or DEFAULT_EDGE_VOICE
        )
        azure_voice_cache[user_id] = (
            azure_voice_id or DEFAULT_AZURE_VOICE
        )
        nickname_cache[user_id] = nickname
    print(
        "[DB] Caché cargada: "
        f"{len(rows)} usuarios | "
        "preferencias Edge/Azure disponibles"
    )
# ============================================================
# UTILIDADES
# ============================================================
def normalize_engine(engine):
    normalized = str(engine or "edge").strip().lower()
    if normalized not in ("edge", "azure"):
        raise ValueError(
            f"Proveedor de voz desconocido: {engine}"
        )
    return normalized
def get_default_voice(engine):
    engine = normalize_engine(engine)
    if engine == "azure":
        return DEFAULT_AZURE_VOICE
    return DEFAULT_EDGE_VOICE
def get_engine_voice_cache(engine):
    engine = normalize_engine(engine)
    if engine == "azure":
        return azure_voice_cache
    return edge_voice_cache
def get_user_voice_preference(user_id, engine="edge"):
    engine = normalize_engine(engine)
    cache = get_engine_voice_cache(engine)
    return cache.get(
        user_id,
        get_default_voice(engine),
    )
# ============================================================
# OBTENER VOZ
# ============================================================
def get_user_voice(
    user_id,
    valid_voices,
    engine="edge",
):
    """
    Devuelve la voz del usuario para el proveedor solicitado.
    Compatible con las llamadas antiguas:
        get_user_voice(user_id, VOICES)
    Nuevas llamadas:
        get_user_voice(user_id, VOICES, engine="azure")
    """
    engine = normalize_engine(engine)
    voice_id = get_user_voice_preference(user_id, engine)
    default_voice = get_default_voice(engine)
    if voice_id not in valid_voices:
        return default_voice
    voice_data = valid_voices[voice_id]
    if (
        isinstance(voice_data, dict)
        and voice_data.get("engine", engine) != engine
    ):
        return default_voice
    return voice_id
# ============================================================
# CAMBIAR VOZ
# ============================================================
def set_user_voice(
    user_id,
    voice_id,
    engine="edge",
):
    """
    Guarda una preferencia sin modificar la del otro motor.
    La llamada antigua:
        set_user_voice(user_id, voice_id)
    continúa guardando la voz Edge.
    """
    engine = normalize_engine(engine)
    if engine == "edge":
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute(
                """
                INSERT INTO users (
                    user_id,
                    voice_id,
                    edge_voice_id
                )
                VALUES (?, ?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET
                    voice_id = excluded.voice_id,
                    edge_voice_id = excluded.edge_voice_id
                """,
                (
                    user_id,
                    voice_id,
                    voice_id,
                ),
            )
            connection.commit()
        edge_voice_cache[user_id] = voice_id
        voice_cache[user_id] = voice_id
    else:
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute(
                """
                INSERT INTO users (
                    user_id,
                    azure_voice_id
                )
                VALUES (?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET
                    azure_voice_id = excluded.azure_voice_id
                """,
                (
                    user_id,
                    voice_id,
                ),
            )
            connection.commit()
        azure_voice_cache[user_id] = voice_id
        voice_cache.setdefault(
            user_id,
            DEFAULT_EDGE_VOICE,
        )
        edge_voice_cache.setdefault(
            user_id,
            DEFAULT_EDGE_VOICE,
        )
    nickname_cache.setdefault(user_id, None)
# ============================================================
# OBTENER AMBAS PREFERENCIAS
# ============================================================
def get_user_voice_preferences(user_id):
    return {
        "edge": get_user_voice_preference(
            user_id,
            "edge",
        ),
        "azure": get_user_voice_preference(
            user_id,
            "azure",
        ),
    }
# ============================================================
# OBTENER APODO
# ============================================================
def get_nickname(user_id):
    return nickname_cache.get(user_id)
# ============================================================
# CAMBIAR APODO
# ============================================================
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
    nickname_cache[user_id] = nickname
    voice_cache.setdefault(
        user_id,
        DEFAULT_EDGE_VOICE,
    )
    edge_voice_cache.setdefault(
        user_id,
        DEFAULT_EDGE_VOICE,
    )
    azure_voice_cache.setdefault(
        user_id,
        DEFAULT_AZURE_VOICE,
    )
# ============================================================
# QUITAR APODO
# ============================================================
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
    nickname_cache[user_id] = None

def set_unified_voice(user_id, voice_id):
    """Una preferencia de voz, reflejada en los identificadores de ambos motores."""
    from penguspeak.voices import EDGE_VOICES, get_equivalent_voice
    if voice_id not in EDGE_VOICES:
        raise ValueError('Voz no válida')
    azure_id = get_equivalent_voice(voice_id, 'azure')
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute('''
            INSERT INTO users (user_id, voice_id, edge_voice_id, azure_voice_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                voice_id=excluded.voice_id,
                edge_voice_id=excluded.edge_voice_id,
                azure_voice_id=excluded.azure_voice_id
        ''', (user_id, voice_id, voice_id, azure_id))
    voice_cache[user_id] = voice_id
    edge_voice_cache[user_id] = voice_id
    azure_voice_cache[user_id] = azure_id


def reset_user_preferences(user_id, remove_alias=True):
    """Restablece la voz y, opcionalmente, el apodo de un usuario."""
    with sqlite3.connect(DB_PATH) as connection:
        if remove_alias:
            connection.execute('''
                INSERT INTO users (user_id, voice_id, edge_voice_id, azure_voice_id, nickname)
                VALUES (?, ?, ?, ?, NULL)
                ON CONFLICT(user_id) DO UPDATE SET
                    voice_id=excluded.voice_id,
                    edge_voice_id=excluded.edge_voice_id,
                    azure_voice_id=excluded.azure_voice_id,
                    nickname=NULL
            ''', (user_id, DEFAULT_EDGE_VOICE, DEFAULT_EDGE_VOICE, DEFAULT_AZURE_VOICE))
            nickname_cache[user_id] = None
        else:
            connection.execute('''
                INSERT INTO users (user_id, voice_id, edge_voice_id, azure_voice_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    voice_id=excluded.voice_id,
                    edge_voice_id=excluded.edge_voice_id,
                    azure_voice_id=excluded.azure_voice_id
            ''', (user_id, DEFAULT_EDGE_VOICE, DEFAULT_EDGE_VOICE, DEFAULT_AZURE_VOICE))
    voice_cache[user_id] = DEFAULT_EDGE_VOICE
    edge_voice_cache[user_id] = DEFAULT_EDGE_VOICE
    azure_voice_cache[user_id] = DEFAULT_AZURE_VOICE
