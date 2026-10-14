# 🐧 PenguSpeak

**PenguSpeak v1.3.0** es un bot de texto a voz (TTS) para Discord, desarrollado en Python. Reproduce mensajes escritos en canales de voz, con voces en español, preferencias individuales y colas por servidor.

## Características

- Lectura automática de mensajes mediante `/tts iniciar` y `/tts detener`, para usuarios que permanezcan en el canal de voz de la sesión.
- Lectura manual mediante `/tts decir`, con opción de adjuntar una imagen para extraer su texto con Tesseract (OCR). El OCR no se ejecuta automáticamente sobre las imágenes del chat.
- Voces masculinas y femeninas en español de diferentes regiones, con muestras de audio cuando estén disponibles.
- Panel interactivo `/tts configurar` para elegir voz, editar apodo y restablecer preferencias.
- Lectura contextual de menciones, respuestas, emojis, stickers, enlaces, imágenes, videos y archivos adjuntos.
- Colas independientes por servidor, reproducción progresiva, preparación anticipada del audio y opción de saltar mensajes propios.
- Reconexión de voz, protección de sesiones activas frente a cambios de canal y desconexión por inactividad.
- Persistencia de voces y apodos en SQLite.

## Motores de voz

**Edge TTS** es el motor principal. Si Edge falla y están configuradas las credenciales necesarias, **Azure Speech** actúa como respaldo. Mientras utiliza Azure, el bot comprueba periódicamente si Edge se recupera y vuelve al motor principal cuando funciona. Puede enviar avisos de cambio y recuperación a servidores con actividad TTS.

Azure Speech es opcional y puede estar sujeto a cuotas o costes según la cuenta. Las voces disponibles dependen del proveedor.

## Comandos

| Comando | Función |
| --- | --- |
| `/tts iniciar` | Activa la lectura automática. |
| `/tts detener` | Desactiva la lectura automática. |
| `/tts decir` | Reproduce texto o intenta leer texto de una imagen. |
| `/tts saltar` | Salta un mensaje propio de la cola. |
| `/tts configurar` | Abre el panel personal de voz y apodo. |
| `/voz actual` | Consulta la voz actual. |
| `/voces hombres` | Explora voces masculinas. |
| `/voces mujeres` | Explora voces femeninas. |
| `/apodo poner` | Establece un apodo hablado. |
| `/apodo quitar` | Elimina el apodo. |
| `/apodo actual` | Consulta el apodo. |

## Instalación

Necesitas Python, FFmpeg y una aplicación de Discord con **Message Content Intent** habilitado y permisos para leer mensajes, conectarse y hablar en canales de voz. Para utilizar OCR también necesitas Tesseract y datos de idioma español.

En Arch Linux / CachyOS:

```sh
sudo pacman -S ffmpeg tesseract tesseract-data-spa
```

En Debian / Ubuntu:

```sh
sudo apt update
sudo apt install ffmpeg tesseract-ocr tesseract-ocr-spa
```

Clona el proyecto e instala las dependencias:

```sh
git clone https://github.com/josueterrones2004/PenguSpeak.git
cd PenguSpeak
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Crea un archivo `.env` basado en `.env.example` y configura tu token:

```dotenv
DISCORD_TOKEN=tu_token_de_discord
```

Para habilitar el respaldo opcional con Azure Speech, añade:

```dotenv
AZURE_SPEECH_KEY=tu_clave
AZURE_SPEECH_REGION=tu_region
```

Inicia el bot:

```sh
.venv/bin/python bot.py
```

No publiques archivos `.env`, claves, tokens ni copias privadas de la base de datos.

## Versiones y desarrollo

- La versión actual del bot es **v1.3.0**.
- La rama `development/2.0` conserva un nombre histórico y no indica la versión del producto.
- La nueva página web se desarrolla por separado y no forma parte de este repositorio.
- Consulta [CHANGELOG.md](CHANGELOG.md) para los cambios de la v1.3.0.
- El bot también puede ejecutarse en Android mediante Termux con dependencias y entorno compatibles.

## Licencia

MIT. Consulta [LICENSE](LICENSE).
