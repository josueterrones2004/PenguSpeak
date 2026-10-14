# 🐧 PenguSpeak

**PenguSpeak** es un bot de texto a voz (TTS) para Discord desarrollado en Python. Lee mensajes dentro de canales de voz y ofrece voces configurables, colas de reproducción y reconocimiento opcional de texto en imágenes.

**Versión de actualización en preparación: 1.2.0** · Versión anterior: 1.1

## Características

- TTS continuo mediante `/tts iniciar` y `/tts detener`.
- Lectura manual mediante `/tts decir`.
- Selección de voz por usuario y apodos personalizados.
- Colas de reproducción independientes por servidor y preparación anticipada del siguiente audio.
- Comando `/tts saltar` para saltar mensajes propios.
- Lectura de menciones, emojis, stickers, enlaces y avisos de contenido multimedia.
- OCR con Tesseract para imágenes enviadas explícitamente con `/tts decir`.
- Configuración persistente con SQLite.
- Desconexión por inactividad y reconexión automática.
- Ejecución en Linux y Android mediante Termux.

## Sitio web

La nueva página de presentación se encuentra en [`docs/`](docs/). Es una web estática independiente del proceso del bot, preparada para publicarse con GitHub Pages.

Incluye una animación ASCII interactiva, renderizado WebGL2 en dispositivos móviles compatibles y ajustes de desplazamiento para Chrome Android. No es necesario instalar dependencias de Python para visualizarla.

Para probarla localmente, sirve la carpeta `docs/` mediante un servidor HTTP y abre la dirección que muestre el servidor.

## Instalación del bot

Requisitos: Python 3.12 o posterior, FFmpeg y, para OCR, Tesseract con datos de idioma español.

En Arch Linux / CachyOS:

```fish
sudo pacman -S ffmpeg tesseract tesseract-data-spa
```

En Debian / Ubuntu:

```sh
sudo apt update
sudo apt install ffmpeg tesseract-ocr tesseract-ocr-spa
```

Clona el repositorio y prepara el entorno:

```sh
git clone https://github.com/josueterrones2004/PenguSpeak.git
cd PenguSpeak
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Copia `.env.example` a `.env` y configura `DISCORD_TOKEN` con el token de tu aplicación de Discord. Habilita **Message Content Intent** y concede al bot permisos para leer mensajes, conectarse y hablar en canales de voz.

Ejecuta:

```sh
.venv/bin/python bot.py
```

> Nunca publiques el archivo `.env`, tokens de Discord ni copias de la base de datos con información privada.

## Comandos principales

| Comando | Función |
| --- | --- |
| `/tts iniciar` | Activa la lectura continua de mensajes. |
| `/tts detener` | Detiene la lectura continua del usuario. |
| `/tts decir` | Lee texto manualmente y admite OCR de imágenes. |
| `/tts saltar` | Salta el mensaje propio que corresponda. |
| `/voz actual` | Consulta la voz seleccionada. |
| `/voces hombres` | Abre el selector de voces masculinas. |
| `/voces mujeres` | Abre el selector de voces femeninas. |
| `/apodo poner` | Establece un apodo hablado. |
| `/apodo quitar` | Elimina el apodo personalizado. |
| `/apodo actual` | Consulta el apodo actual. |

## Android

El bot puede ejecutarse en Android con Termux, Debian mediante `proot-distro` y una sesión `tmux`. La instalación requiere las dependencias de voz y Python adecuadas para ese entorno.

## Desarrollo y versiones

La rama de trabajo existente se llama `development/2.0` por motivos históricos. **Ese nombre no determina la versión del producto**: la próxima actualización se identifica como **v1.2.0**, no v2.0.

Consulta [CHANGELOG.md](CHANGELOG.md) para ver el alcance de la actualización. Las mejoras de la web no implican por sí mismas cambios en el motor TTS del bot.

## Licencia

MIT. Consulta [LICENSE](LICENSE).
