<div align="center">

# 🐧 PenguSpeak

**Convierte conversaciones de Discord en voz, con baja latencia, 22 voces en español y configuración por usuario.**

[![Version](https://img.shields.io/badge/version-1.3.0-5865F2?style=flat-square)](https://github.com/josueterrones2004/PenguSpeak/releases/tag/v1.3.0)
[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![discord.py](https://img.shields.io/badge/discord.py-2.7.1-5865F2?style=flat-square&logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![Edge TTS](https://img.shields.io/badge/Edge_TTS-principal-0078D7?style=flat-square)](https://github.com/rany2/edge-tts)
[![Azure Speech](https://img.shields.io/badge/Azure_Speech-respaldo-0089D6?style=flat-square&logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/products/ai-services/ai-speech)
[![License](https://img.shields.io/badge/licencia-MIT-22c55e?style=flat-square)](LICENSE)

**[🌐 Web oficial](https://josueterrones2004.github.io/PenguSpeak-Web/)** · **[📦 Releases](https://github.com/josueterrones2004/PenguSpeak/releases)** · **[📝 Changelog](CHANGELOG.md)**

</div>

---

PenguSpeak es un bot de **Text-to-Speech para Discord** escrito en Python. Está pensado para poder escuchar el chat mientras juegas, hablas con otras personas o simplemente no quieres estar mirando constantemente el canal de texto.

Cada usuario puede elegir su propia voz y apodo. PenguSpeak mantiene colas independientes por servidor, procesa mensajes de forma contextual y reproduce el audio de forma progresiva para reducir las esperas entre mensajes.

> **Versión estable actual:** `1.3.0`

## ✨ Qué incluye

- 🔊 TTS continuo con `/tts iniciar` y `/tts detener`.
- 💬 Reproducción manual con `/tts decir`.
- 🎙️ **22 voces en español** de distintos países y regiones.
- 👤 Voz configurable individualmente para cada usuario.
- 🏷️ Apodos personalizados para el TTS.
- ⚙️ Panel interactivo de configuración con `/tts configurar`.
- 💾 Preferencias persistentes mediante SQLite.
- 🧠 Lectura contextual de mensajes, respuestas, menciones y contenido multimedia.
- 😄 Soporte para emojis Unicode y emojis personalizados de Discord.
- 🎟️ Lectura de stickers por nombre.
- 🖼️ Detección de imágenes.
- 🎥 Detección de videos.
- 🔗 Detección de enlaces.
- 📎 Detección de archivos adjuntos.
- 📚 Cola independiente por servidor.
- ⚡ Reproducción progresiva y preparación anticipada del siguiente audio.
- ⏭️ Cada usuario puede saltar únicamente sus propios mensajes.
- 🔄 Reconexión automática de voz cuando una sesión válida continúa activa.
- 🔒 Protección para evitar que una sesión activa sea movida a otro canal de voz.
- 🔇 Conexión con `self_deaf=True`: PenguSpeak no necesita escuchar el audio del canal.
- 💤 Gestión automática de sesiones e inactividad.
- 🛟 Cambio automático entre Edge TTS y Azure Speech cuando es necesario.
- 📱 Compatible con Linux y también ejecutable en Android mediante Termux con un entorno compatible.

---

## 🔊 Dos formas de usar el TTS

### TTS continuo

Con `/tts iniciar`, PenguSpeak comienza a leer los mensajes que escriba ese usuario mientras permanezca en el canal de voz de la sesión.

```text
/tts iniciar
```

Cuando ya no quieras que lea tus mensajes:

```text
/tts detener
```

El TTS continuo es individual: activar PenguSpeak para una persona no activa automáticamente la lectura para los demás usuarios del canal.

### TTS manual

`/tts decir` permite reproducir un texto puntual sin activar el modo continuo.

```text
/tts decir texto: Hola a todos
```

---

## 🧠 Lectura contextual de mensajes

PenguSpeak no se limita a enviar el texto tal cual al sintetizador. Antes construye una frase hablada que intenta conservar el contexto del mensaje.

| Contenido | Comportamiento |
| --- | --- |
| 💬 Texto normal | Lee el contenido del mensaje. |
| ↩️ Respuesta | Puede indicar a quién está respondiendo el usuario. |
| 👤 Mención de usuario | Pronuncia el nombre o apodo correspondiente. |
| 🏷️ Mención de rol | Identifica el rol mencionado. |
| 📣 `@everyone` / `@here` | Reconoce la mención cuando Discord la marca como real. |
| 🖼️ Imagen | Anuncia que el usuario envió una imagen. |
| 🎥 Video | Anuncia que el usuario envió un video. |
| 🔗 Enlace | Anuncia la presencia de un enlace sin leer la URL completa. |
| 📎 Archivo | Anuncia que se envió un archivo. |
| 🎟️ Sticker | Utiliza el nombre del sticker cuando está disponible. |
| 😄 Emoji Unicode | Convierte el emoji a una forma hablable. |
| 🎨 Emoji personalizado | Humaniza el nombre del emoji de Discord. |

Por ejemplo, un mensaje con texto e imagen puede terminar reproduciéndose de forma similar a:

```text
Yarin envió una imagen y dice: mira esto
```

Si el mensaje responde a otra persona o contiene menciones, PenguSpeak incorpora ese contexto a la frase cuando corresponde.

### 😄 Emojis

Los emojis Unicode se transforman a nombres que puedan ser pronunciados por el TTS. Los emojis personalizados de Discord utilizan su nombre como base.

```text
<:penguDance:123456789>
→ pengu Dance
```

También se conserva un pequeño easter egg del proyecto:

```text
👀 → ojitos void
```

### 🎟️ Stickers

Cuando un mensaje contiene un sticker con nombre disponible, PenguSpeak puede anunciarlo en voz.

```text
sticker Gato feliz
```

### 🖼️ Imágenes, videos, enlaces y archivos

PenguSpeak reconoce el tipo de contenido adjunto y lo integra en la frase hablada. No necesita leer una URL completa ni reproducir nombres de archivo complicados para indicar qué ocurrió en el chat.

Ejemplos:

```text
Yarin envió una imagen
Yarin envió un video y dice: mira esto
Yarin envió un enlace
Yarin envió un archivo
```

---

## 🎙️ Voces

PenguSpeak incluye **22 voces en español** y permite seleccionar una preferencia personal desde Discord. La misma elección se conserva al cambiar entre Edge TTS y Azure Speech cuando existe una voz equivalente.

La voz predeterminada es **🇲🇽 Jorge · México**.

### 👨 Voces masculinas

| Voz | Región |
| --- | --- |
| 🇲🇽 Jorge | México |
| 🇪🇸 Álvaro | España |
| 🇦🇷 Tomas | Argentina |
| 🇧🇴 Marcelo | Bolivia |
| 🇨🇱 Lorenzo | Chile |
| 🇨🇷 Juan | Costa Rica |
| 🇨🇺 Manuel | Cuba |
| 🇩🇴 Emilio | República Dominicana |
| 🇬🇹 Andres | Guatemala |
| 🇳🇮 Federico | Nicaragua |
| 🇵🇦 Roberto | Panamá |
| 🇵🇪 Alex | Perú |
| 🇵🇷 Victor | Puerto Rico |

### 👩 Voces femeninas

| Voz | Región |
| --- | --- |
| 🇲🇽 Dalia | México |
| 🇧🇴 Sofia | Bolivia |
| 🇨🇱 Catalina | Chile |
| 🇩🇴 Ramona | República Dominicana |
| 🇬🇹 Marta | Guatemala |
| 🇭🇳 Karla | Honduras |
| 🇳🇮 Yolanda | Nicaragua |
| 🇵🇦 Margarita | Panamá |
| 🇵🇪 Camila | Perú |

Las voces pueden explorarse desde `/voces hombres`, `/voces mujeres` o directamente desde `/tts configurar`. Cuando existen archivos de demostración, el navegador de voces los adjunta para poder escucharlos antes de elegir.

---

## ⚙️ Panel de configuración

`/tts configurar` abre un panel privado para personalizar PenguSpeak sin tener que recordar todos los comandos.

Desde ahí puedes:

- 🎙️ Abrir las voces masculinas.
- 🎙️ Abrir las voces femeninas.
- ✏️ Editar tu apodo.
- 🗑️ Quitar tu apodo.
- 🔄 Restablecer la voz o todas tus preferencias.
- 🔃 Actualizar el estado mostrado por el panel.

Los selectores y botones del panel solamente pueden ser utilizados por el usuario que lo abrió.

---

## 🏷️ Apodos

PenguSpeak permite configurar un nombre alternativo para que el TTS lo utilice al hablar de ti.

```text
/apodo poner apodo: Yarin
```

También puedes consultar o quitar el apodo:

```text
/apodo actual
/apodo quitar
```

Los apodos aceptan letras, números y espacios. Los símbolos especiales se rechazan para mantener una pronunciación predecible.

---

## ⚡ Cola, streaming y baja latencia

Cada servidor tiene su propia cola. Esto evita que la actividad de un servidor interfiera con la reproducción de otro.

PenguSpeak prepara el audio mientras administra la cola y puede comenzar a preparar el siguiente mensaje antes de que llegue su turno. El objetivo es reducir las pausas perceptibles entre mensajes consecutivos.

El sistema también mantiene información sobre el mensaje actual, elementos cancelados y streams pendientes para poder reaccionar a saltos, desconexiones y cambios de estado sin vaciar innecesariamente toda la sesión.

### ⏭️ Saltar mensajes

`/tts saltar` está limitado a los mensajes del propio usuario.

Si el mensaje que se está reproduciendo pertenece a quien ejecuta el comando, PenguSpeak puede detenerlo. Si pertenece a otra persona, busca el siguiente mensaje pendiente del usuario que pidió el salto.

Los mensajes de otros usuarios no se eliminan.

---

## 🛟 Edge TTS + Azure Speech

**Edge TTS** es el motor principal de PenguSpeak.

Si Edge deja de estar disponible y las credenciales de Azure están configuradas, **Azure Speech** entra automáticamente como respaldo. Mientras Azure está activo, PenguSpeak comprueba periódicamente si Edge vuelve a funcionar y regresa al motor principal cuando se recupera.

Cuando una sesión TTS está activa, PenguSpeak puede avisar en Discord del cambio de motor y de la recuperación para que los usuarios sepan por qué el comportamiento o la latencia pudieron variar.

```text
Edge TTS
   │
   ├── disponible ───────────────→ TTS normal
   │
   └── error
        ↓
    Azure Speech
        │
        └── comprobaciones periódicas → regreso a Edge
```

Azure Speech es opcional y requiere tus propias credenciales.

---

## 🔒 Sesiones de voz

PenguSpeak mantiene una sesión asociada al canal de voz donde comenzó la actividad TTS.

- Si existe una sesión activa, no permite moverla silenciosamente a otro canal.
- Los mensajes solo se leen cuando el usuario continúa en el canal de voz de la sesión.
- Si un usuario activo abandona ese canal, su TTS se desactiva y se eliminan sus mensajes pendientes.
- Cuando sale el último usuario TTS de la sesión, PenguSpeak limpia la cola y se desconecta.
- El bot se conecta ensordecido con `self_deaf=True` porque solo necesita reproducir audio, no escuchar a los usuarios.
- Si Discord interrumpe la conexión pero la sesión sigue siendo válida, PenguSpeak puede intentar reconectarse al canal original.

---

## 🎙️ Comandos

| Comando | Función |
| --- | --- |
| `/tts iniciar` | Activa la lectura automática para el usuario. |
| `/tts detener` | Desactiva la lectura automática y limpia sus mensajes pendientes. |
| `/tts decir` | Reproduce un texto manualmente. |
| `/tts saltar` | Salta el mensaje actual o el siguiente mensaje propio de la cola. |
| `/tts configurar` | Abre el panel interactivo de voz y apodo. |
| `/voz actual` | Muestra la voz actualmente seleccionada. |
| `/voces hombres` | Abre el navegador de voces masculinas. |
| `/voces mujeres` | Abre el navegador de voces femeninas. |
| `/apodo poner` | Crea o cambia el apodo hablado. |
| `/apodo quitar` | Elimina el apodo personalizado. |
| `/apodo actual` | Muestra el apodo actual. |

Los slash commands se sincronizan automáticamente al iniciar el bot.

---

## 📋 Requisitos

PenguSpeak necesita:

- Python.
- FFmpeg.
- Una aplicación de Discord con **Message Content Intent** habilitado.
- Permisos para ver y enviar mensajes, utilizar comandos de aplicación, conectarse a canales de voz y hablar.

### Arch Linux / CachyOS

```bash
sudo pacman -S ffmpeg
```

### Debian / Ubuntu

```bash
sudo apt update
sudo apt install ffmpeg
```

---

## 🚀 Instalación

Clona el repositorio:

```bash
git clone https://github.com/josueterrones2004/PenguSpeak.git
cd PenguSpeak
```

Crea un entorno virtual:

```bash
python -m venv .venv
```

Actívalo:

```bash
source .venv/bin/activate
```

Instala las dependencias:

```bash
pip install -r requirements.txt
```

Crea tu archivo `.env` a partir del ejemplo:

```bash
cp .env.example .env
```

Configura el token de Discord:

```dotenv
DISCORD_TOKEN=tu_token_de_discord
```

Para habilitar Azure Speech como respaldo, añade también:

```dotenv
AZURE_SPEECH_KEY=tu_clave
AZURE_SPEECH_REGION=tu_region
```

Inicia PenguSpeak:

```bash
python bot.py
```

O directamente con el intérprete del entorno virtual:

```bash
.venv/bin/python bot.py
```

---

## 🤖 Configuración en Discord

En el **Discord Developer Portal** habilita:

- **Message Content Intent**.

Y asegúrate de que el bot pueda:

- Ver los canales necesarios.
- Enviar mensajes.
- Usar comandos de aplicación.
- Conectarse a canales de voz.
- Hablar en canales de voz.

PenguSpeak utiliza los estados de voz para saber si el usuario continúa dentro de la sesión TTS correspondiente.

---

## 📱 Android / Termux

PenguSpeak también puede ejecutarse en Android utilizando Termux y un entorno Linux compatible.

Una instalación existente puede mantenerse actualizada con:

```bash
git pull
pip install -r requirements.txt
```

Para mantener el proceso activo puedes utilizar herramientas como `tmux` dentro del entorno donde ejecutes el bot.

---

## 📁 Estructura del proyecto

```text
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
    ├── queue.py
    ├── state.py
    ├── text.py
    ├── views.py
    └── voices.py
```

### Componentes principales

- `bot.py` — eventos de Discord, slash commands y sesiones de voz.
- `audio.py` — motores TTS, streaming, FFmpeg y fallback Edge/Azure.
- `database.py` — preferencias persistentes de voz y apodos mediante SQLite.
- `queue.py` — colas por servidor, prefetch, reproducción y cancelación.
- `state.py` — estado de sesiones, usuarios activos e inactividad.
- `text.py` — procesamiento contextual de mensajes, emojis, menciones y adjuntos.
- `views.py` — panel de configuración, selectores y navegador de voces.
- `voices.py` — catálogo de voces Edge/Azure y equivalencias entre motores.

---

## 🔐 Seguridad

El token del bot y las credenciales de Azure deben mantenerse fuera del repositorio.

No publiques:

- `.env`
- tokens de Discord
- claves de Azure
- bases de datos SQLite con preferencias de usuarios
- archivos de log privados

El `.gitignore` del proyecto ya excluye archivos `.env`, bases de datos locales y logs habituales.

---

## 🔄 Actualizar PenguSpeak

En una instalación existente:

```bash
git pull
pip install -r requirements.txt
```

Después reinicia el bot normalmente.

---

## 🌐 Web oficial

PenguSpeak también tiene una página web propia con información del proyecto:

**https://josueterrones2004.github.io/PenguSpeak-Web/**

El sitio web se mantiene en un repositorio separado: [PenguSpeak-Web](https://github.com/josueterrones2004/PenguSpeak-Web).

---

## 📦 Versión

Versión estable actual:

**PenguSpeak v1.3.0**

Consulta [CHANGELOG.md](CHANGELOG.md) para ver los cambios de la versión actual y la sección de [Releases](https://github.com/josueterrones2004/PenguSpeak/releases) para versiones publicadas.

---

## 📜 Licencia

PenguSpeak está disponible bajo la licencia **MIT**. Consulta [LICENSE](LICENSE) para más información.

---

<div align="center">

🐧 **PenguSpeak**

Hecho con Python, discord.py, Edge TTS y Azure Speech.

</div>
