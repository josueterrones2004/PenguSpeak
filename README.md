# PenguSpeak

PenguSpeak es un bot de texto a voz para Discord enfocado en voces en español.

Puede leer los mensajes de los usuarios dentro de canales de voz, manejar menciones y respuestas de forma natural, recordar preferencias de voz y apodos, y leer texto contenido en imágenes mediante OCR.

## Características

- Lectura automática de mensajes mediante TTS
- Mensajes TTS individuales
- Selección de voz por usuario
- 22 voces en español mediante Edge TTS
- Catálogo separado de voces masculinas y femeninas
- Demos de voz reproducibles dentro de Discord
- Preferencias persistentes mediante SQLite
- Apodos personalizados
- Manejo de menciones y respuestas
- OCR para leer texto dentro de imágenes
- Cola de reproducción global por servidor
- Sistema de salto de mensajes por usuario
- Desconexión automática por inactividad
- Compatible con Linux
- Compatible con Android mediante Termux + Debian

## Comandos

### TTS

- `/tts iniciar`  
  Empieza a leer automáticamente tus mensajes.

- `/tts detener`  
  Deja de leer automáticamente tus mensajes.

- `/tts decir texto:<texto>`  
  Añade un único mensaje a la cola de voz.

- `/tts saltar`  
  Salta tu mensaje actual o elimina tu próximo mensaje de la cola.

### Voces

- `/voz actual`  
  Muestra la voz que tienes seleccionada actualmente.

- `/voces hombres`  
  Muestra las voces masculinas disponibles junto con sus demos.

- `/voces mujeres`  
  Muestra las voces femeninas disponibles junto con sus demos.

### Apodos

- `/apodo poner nombre:<nombre>`  
  Establece el nombre que el bot dirá al leer tus mensajes.

- `/apodo quitar`  
  Elimina tu apodo personalizado.

- `/apodo actual`  
  Muestra tu apodo actual.

## Voces disponibles

PenguSpeak incluye actualmente 22 voces en español mediante Edge TTS.

Entre los países representados se encuentran:

- México
- España
- Argentina
- Bolivia
- Chile
- Costa Rica
- Cuba
- República Dominicana
- Guatemala
- Honduras
- Nicaragua
- Panamá
- Perú
- Puerto Rico

## Requisitos

### Python

Se recomienda Python 3.12 o superior.

Instala las dependencias de Python con:

```bash
pip install -r requirements.txt
```

### Dependencias del sistema

PenguSpeak también necesita:

- FFmpeg
- Tesseract OCR
- Datos de idioma español para Tesseract

#### Arch Linux / CachyOS

```bash
sudo pacman -S ffmpeg tesseract tesseract-data-spa
```

#### Debian / Ubuntu

```bash
sudo apt install ffmpeg tesseract-ocr tesseract-ocr-spa
```

## Configuración del bot de Discord

Crea una aplicación en el Discord Developer Portal y añade un bot.

Activa:

- **Message Content Intent**

El bot necesita permisos para:

- Ver canales
- Enviar mensajes
- Conectarse a canales de voz
- Hablar
- Usar comandos de aplicación

## Configuración

Copia el archivo de ejemplo:

```bash
cp .env.example .env
```

Después edita `.env` y añade el token de tu bot:

```env
DISCORD_TOKEN=tu_token_de_discord_aqui
```

> [!WARNING]
> Nunca publiques tu token real de Discord ni subas el archivo `.env` al repositorio.

## Ejecutar PenguSpeak

Ejecuta:

```bash
python bot.py
```

Si utilizas el entorno virtual del proyecto:

```bash
.venv/bin/python bot.py
```

## Android

PenguSpeak también puede ejecutarse en Android utilizando:

- Termux
- `proot-distro`
- Debian
- Python
- FFmpeg
- Tesseract OCR

La versión de Android utiliza el mismo sistema Edge TTS que la versión de escritorio.

## Estructura del proyecto

```text
PenguSpeak/
├── bot.py
├── config.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── penguspeak/
│   ├── __init__.py
│   ├── audio.py
│   ├── database.py
│   ├── ocr.py
│   ├── queue.py
│   ├── state.py
│   ├── text.py
│   ├── views.py
│   └── voices.py
│
└── demos/
    ├── male/
    └── female/
```

## Datos locales y privacidad

PenguSpeak almacena localmente algunas preferencias de usuario:

- ID de usuario de Discord
- Voz seleccionada
- Apodo personalizado

Estos datos se guardan en una base de datos SQLite local.

Los archivos de base de datos están excluidos del repositorio mediante `.gitignore`.

## Seguridad

El archivo `.env` está excluido del repositorio para evitar publicar accidentalmente el token del bot.

Si un token se publica accidentalmente, debe regenerarse desde el Discord Developer Portal.

## Licencia

Todavía no se ha seleccionado una licencia para este proyecto.
