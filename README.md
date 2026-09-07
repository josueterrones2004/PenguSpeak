# 🐧 PenguSpeak

**PenguSpeak** es un bot de Text-to-Speech para Discord escrito en Python.

Convierte los mensajes de texto de Discord en voz dentro de un canal de voz, con voces en español, colas de reproducción, reconocimiento de imágenes mediante OCR y soporte para contenido como emojis, enlaces, imágenes, videos, menciones y stickers.

> Versión actual: **1.0.0**

---

## ✨ Características

- 🔊 Text-to-Speech en canales de voz de Discord.
- 🇪🇸 22 voces en español mediante Microsoft Edge TTS.
- 👨 Voces masculinas y 👩 voces femeninas.
- 👤 Voz configurable individualmente para cada usuario.
- 🏷️ Apodos personalizados para TTS.
- 💾 Configuración persistente mediante SQLite.
- 📚 Cola de reproducción independiente por servidor.
- ⚡ Prefetch del siguiente audio para reducir pausas.
- ⏭️ Cada usuario puede saltar sus propios mensajes.
- 💤 Desconexión automática por inactividad.
- 🔄 Reconexión automática cuando vuelve a escribirse un mensaje.
- 🔇 El bot permanece ensordecido en el canal de voz.
- 🖼️ Detección de imágenes.
- 🎥 Detección de videos.
- 🔗 Detección de enlaces.
- 🏷️ Lectura de menciones.
- 🎟️ Lectura de stickers.
- 😄 Soporte para emojis Unicode.
- 🎨 Soporte para emojis personalizados de Discord.
- 👀 Easter egg especial para `👀`.
- 🔎 OCR para leer texto de imágenes mediante `/tts decir`.
- ⚡ OCR optimizado con salida temprana y fallbacks progresivos.
- 🗣️ Lectura natural de mensajes con multimedia.
- 📱 Compatible con Linux y ejecución en Android mediante Termux + Debian/proot.

Ejemplo:

```text
Yarin escribe:
mira esto

y adjunta una imagen.

PenguSpeak:
"Yarin envió una imagen y dice: mira esto"
📋 Requisitos
Python

Se recomienda:

Python 3.12+

PenguSpeak también ha sido probado con Python 3.13.

Dependencias del sistema

PenguSpeak necesita:

FFmpeg
Tesseract OCR
Datos de idioma español para Tesseract
CachyOS / Arch Linux
sudo pacman -S ffmpeg tesseract tesseract-data-spa
Debian / Ubuntu
sudo apt update
sudo apt install ffmpeg tesseract-ocr tesseract-ocr-spa

Tesseract solamente se utiliza para el OCR de imágenes enviado explícitamente mediante /tts decir.

📦 Dependencias de Python

Las dependencias del proyecto se encuentran en:

requirements.txt

Actualmente incluyen:

discord.py[voice]==2.7.1
davey==0.1.6
edge-tts==7.2.8
python-dotenv==1.2.3
Pillow==12.3.0
pytesseract==0.3.13
emoji>=2.14,<3
🚀 Instalación

Clona el repositorio:

git clone https://github.com/josueteronnes2004/PenguSpeak.git
cd PenguSpeak

Crea un entorno virtual:

python -m venv .venv

Actívalo:

source .venv/bin/activate

Instala las dependencias:

pip install -r requirements.txt

También puedes utilizar uv:

uv pip install -r requirements.txt --python .venv/bin/python
🔐 Configuración

Copia el archivo de ejemplo:

cp .env.example .env

Abre .env y coloca el token de tu bot:

DISCORD_TOKEN=TU_TOKEN_AQUI

Nunca publiques tu archivo .env ni el token del bot.

🤖 Configuración del bot en Discord

PenguSpeak necesita acceso a los intents necesarios para leer mensajes y gestionar estados de voz.

Asegúrate de habilitar:

Message Content Intent

El bot también necesita permisos para:

Ver canales
Enviar mensajes
Usar comandos de aplicación
Conectarse a canales de voz
Hablar

Los slash commands se sincronizan automáticamente al iniciar.

▶️ Ejecutar PenguSpeak

Con el entorno virtual activado:

python bot.py

O directamente:

.venv/bin/python bot.py

Al iniciar correctamente deberías ver algo similar a:

PenguSpeak conectado como PenguSpeak
4 grupos de comandos sincronizados.
🎙️ Comandos
/tts iniciar

Activa el TTS continuo para el usuario.

Mientras esté activado, los mensajes escritos por ese usuario serán enviados a la cola de voz.

/tts iniciar
/tts detener

Desactiva el TTS continuo.

/tts detener
/tts decir

Reproduce un mensaje manualmente sin necesidad de activar el TTS continuo.

Puede utilizar:

texto
imagen
texto + imagen

Ejemplo:

/tts decir texto: Hola a todos

Si se proporciona una imagen, PenguSpeak utiliza OCR para detectar y leer texto dentro de ella.

El OCR solamente se ejecuta mediante /tts decir.

Las imágenes enviadas normalmente con /tts iniciar no utilizan OCR.

/tts saltar

Permite al usuario saltar su propio mensaje actual o eliminar su siguiente mensaje de la cola.

No permite saltar los mensajes de otros usuarios.

🗣️ Voces
/voz actual

Muestra la voz actualmente seleccionada por el usuario.

/voces hombres

Abre el selector de voces masculinas.

/voces mujeres

Abre el selector de voces femeninas.

Cada usuario puede elegir su propia voz.

La voz predeterminada es:

Jorge
🏷️ Apodos

PenguSpeak permite establecer un nombre personalizado para ser leído por el TTS.

/apodo poner

Ejemplo:

/apodo poner apodo: Yarin
/apodo quitar

Elimina el apodo configurado.

/apodo actual

Muestra el apodo actual.

Los apodos pueden contener:

letras
números
espacios

Los emojis y símbolos especiales no están permitidos en los apodos.

🖼️ Imágenes, videos y enlaces

Cuando el TTS continuo está activado, PenguSpeak reconoce contenido multimedia.

Imagen
Yarin envió una imagen
Imagen con texto
Yarin envió una imagen y dice: mira esto
Video
Yarin envió un video
Video con texto
Yarin envió un video y dice: mira esto
Enlace
Yarin envió un enlace
Enlace con texto
Yarin envió un enlace y dice: mira esto
🔎 OCR

PenguSpeak utiliza Tesseract OCR para leer texto dentro de imágenes.

El OCR está reservado para:

/tts decir imagen:

El sistema utiliza varias etapas de reconocimiento:

Imagen
  ↓
Escala de grises / contraste
  ↓
Salida temprana si el resultado es bueno
  ↓
PSM alternativo
  ↓
Threshold
  ↓
Canales de color
  ↓
Mejor resultado

Esto evita ejecutar todas las variantes cuando una imagen sencilla ya puede reconocerse correctamente.

😄 Emojis

PenguSpeak puede convertir emojis Unicode a nombres hablados en español.

Ejemplo:

😂

se convierte en una descripción hablada equivalente.

También reconoce emojis personalizados de Discord.

Ejemplo:

<:penguDance:123456789>

puede convertirse en:

pengu Dance

Existe además un pequeño easter egg:

👀

se lee como:

ojitos void
🏷️ Menciones

PenguSpeak puede reconocer menciones de usuarios dentro de mensajes.

Ejemplo:

@Yarin mira esto + imagen

puede leerse como:

Josué etiquetó a Yarin en una imagen y dice: mira esto
🎟️ Stickers

Los stickers de Discord también pueden ser reconocidos por nombre.

Ejemplo:

sticker Gato feliz
⚡ Cola y prefetch

Cada servidor utiliza su propia cola de reproducción.

Mientras se reproduce un mensaje, PenguSpeak puede comenzar a generar el audio del siguiente mensaje.

Esto reduce el tiempo entre mensajes consecutivos.

Cada mensaje sigue tratándose como una unidad independiente dentro de la cola.

⏭️ Sistema de salto

Cada usuario puede saltar únicamente sus propios mensajes.

Si el mensaje que se está reproduciendo pertenece al usuario, puede detenerlo.

Si no, PenguSpeak busca el siguiente mensaje de ese mismo usuario dentro de la cola.

Los mensajes de otros usuarios no se eliminan.

💤 Inactividad

Si no hay actividad durante varios minutos, PenguSpeak se desconecta automáticamente del canal de voz.

Los usuarios que todavía tengan /tts iniciar activo mantienen su sesión.

Cuando uno de ellos vuelve a escribir desde un canal de voz válido, PenguSpeak puede reconectarse automáticamente y leer ese mismo mensaje.

🔇 Estado de voz

PenguSpeak se conecta utilizando:

self_deaf=True

De esta forma, el bot no necesita escuchar el audio del canal de voz.

También intenta conservar este estado al cambiar de canal.

📱 Android / Termux

PenguSpeak también puede ejecutarse permanentemente desde un teléfono Android utilizando:

Termux
proot-distro
Debian
tmux

El repositorio puede mantenerse sincronizado con GitHub:

git pull
pip install -r requirements.txt

Luego puede ejecutarse dentro del entorno virtual:

source .venv/bin/activate
python bot.py
Ejecución con tmux

Ejemplo:

tmux new-session -s penguspeak

Dentro de la sesión:

proot-distro login debian
cd ~/PenguSpeak
source .venv/bin/activate
python bot.py

Para salir de la sesión sin cerrar el bot:

Ctrl+B
D

Para volver a entrar:

tmux attach -t penguspeak
📁 Estructura del proyecto
PenguSpeak/
├── bot.py
├── config.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── CHANGELOG.md
├── LICENSE
├── demos/
│   ├── male/
│   └── female/
└── penguspeak/
    ├── __init__.py
    ├── audio.py
    ├── database.py
    ├── ocr.py
    ├── queue.py
    ├── state.py
    ├── text.py
    ├── views.py
    └── voices.py
🔒 Seguridad

El token de Discord debe almacenarse únicamente en:

.env

El archivo .env debe estar excluido mediante .gitignore.

Nunca publiques tu token de Discord ni lo incluyas directamente en el código.

🧪 Comprobación rápida

Antes de ejecutar una nueva versión puedes comprobar errores de sintaxis con:

python -m py_compile \
    bot.py \
    penguspeak/*.py

Si no aparece ningún error, puedes iniciar el bot normalmente.

🔄 Actualizar PenguSpeak

En una instalación existente:

git pull

Después actualiza las dependencias:

pip install -r requirements.txt

Y vuelve a iniciar:

python bot.py
📦 Versión

Versión estable actual:

PenguSpeak 1.0.0
📜 Licencia

Este proyecto está disponible bajo la licencia MIT.

Consulta el archivo:

LICENSE

para más información.

🐧 PenguSpeak

Hecho con Python, Discord.py, Edge TTS, Tesseract y demasiadas ganas de hacer hablar a un pingüino.
