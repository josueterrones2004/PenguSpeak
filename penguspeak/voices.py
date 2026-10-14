"""Catálogos independientes de Edge TTS y Azure Speech."""

# Identificadores existentes: se conservan para no invalidar preferencias.
_EDGE_ROWS = [
    ('jorge','Jorge','male','México','🇲🇽','es-MX-JorgeNeural'),
    ('alvaro','Álvaro','male','España','🇪🇸','es-ES-AlvaroNeural'),
    ('tomas','Tomas','male','Argentina','🇦🇷','es-AR-TomasNeural'),
    ('marcelo','Marcelo','male','Bolivia','🇧🇴','es-BO-MarceloNeural'),
    ('lorenzo','Lorenzo','male','Chile','🇨🇱','es-CL-LorenzoNeural'),
    ('juan','Juan','male','Costa Rica','🇨🇷','es-CR-JuanNeural'),
    ('manuel','Manuel','male','Cuba','🇨🇺','es-CU-ManuelNeural'),
    ('emilio','Emilio','male','República Dominicana','🇩🇴','es-DO-EmilioNeural'),
    ('andres','Andres','male','Guatemala','🇬🇹','es-GT-AndresNeural'),
    ('federico','Federico','male','Nicaragua','🇳🇮','es-NI-FedericoNeural'),
    ('roberto','Roberto','male','Panamá','🇵🇦','es-PA-RobertoNeural'),
    ('alex_peru','Alex','male','Perú','🇵🇪','es-PE-AlexNeural'),
    ('victor','Victor','male','Puerto Rico','🇵🇷','es-PR-VictorNeural'),
    ('dalia','Dalia','female','México','🇲🇽','es-MX-DaliaNeural'),
    ('sofia','Sofia','female','Bolivia','🇧🇴','es-BO-SofiaNeural'),
    ('catalina','Catalina','female','Chile','🇨🇱','es-CL-CatalinaNeural'),
    ('ramona','Ramona','female','República Dominicana','🇩🇴','es-DO-RamonaNeural'),
    ('marta','Marta','female','Guatemala','🇬🇹','es-GT-MartaNeural'),
    ('karla','Karla','female','Honduras','🇭🇳','es-HN-KarlaNeural'),
    ('yolanda','Yolanda','female','Nicaragua','🇳🇮','es-NI-YolandaNeural'),
    ('margarita','Margarita','female','Panamá','🇵🇦','es-PA-MargaritaNeural'),
    ('camila','Camila','female','Perú','🇵🇪','es-PE-CamilaNeural'),
]

EDGE_VOICES = {}
AZURE_VOICES = {}

for slug, name, gender, country, flag, voice in _EDGE_ROWS:
    edge_id = f'edge_{slug}'
    azure_id = f'azure_{slug}'
    folder = 'male' if gender == 'male' else 'female'
    common = {
        'name': name,
        'gender': gender,
        'country': country,
        'flag': flag,
        'voice': voice,
    }
    EDGE_VOICES[edge_id] = {
        **common,
        'engine': 'edge',
        'demo': f'demos/{folder}/{edge_id}.mp3',
    }
    AZURE_VOICES[azure_id] = {
        **common,
        'engine': 'azure',
        'demo': f'demos/{folder}/{azure_id}.mp3',
    }

# El catálogo de Azure es candidato hasta verificarlo contra el recurso
# Azure Speech y generar los MP3 de demostración correspondientes.
VOICES = {**EDGE_VOICES, **AZURE_VOICES}
DEFAULT_EDGE_VOICE = 'edge_jorge'
DEFAULT_AZURE_VOICE = 'azure_jorge'
DEFAULT_VOICE = DEFAULT_EDGE_VOICE


def get_default_voice(engine='edge'):
    if engine == 'edge':
        return DEFAULT_EDGE_VOICE
    if engine == 'azure':
        return DEFAULT_AZURE_VOICE
    raise ValueError(f'Motor TTS desconocido: {engine}')


def get_engine_voices(engine='edge'):
    if engine == 'edge':
        return EDGE_VOICES
    if engine == 'azure':
        return AZURE_VOICES
    raise ValueError(f'Motor TTS desconocido: {engine}')


def get_voice_label(voice_id):
    data = VOICES[voice_id]
    return f'{data["flag"]} {data["name"]} · {data["country"]}'


def get_gender_voices(gender, engine='edge'):
    return [
        (voice_id, data)
        for voice_id, data in get_engine_voices(engine).items()
        if data['gender'] == gender
    ]


def get_equivalent_voice(voice_id, engine):
    """Busca la misma voz en otro motor, sin cambiar preferencias."""
    target = f'{engine}_{voice_id.split("_", 1)[-1]}'
    return target if target in get_engine_voices(engine) else get_default_voice(engine)
