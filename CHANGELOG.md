# Changelog — PenguSpeak

## [v1.3.0] — Actualización del bot

Cambios incorporados en esta actualización:

- **Respaldo automático:** Edge TTS permanece como motor principal. Cuando falla, PenguSpeak utiliza Azure Speech si está configurado y comprueba periódicamente si Edge vuelve a estar disponible.
- **Avisos del servicio:** notificaciones del cambio a Azure y del regreso a Edge para servidores que estén utilizando TTS, sin repetir avisos innecesarios.
- **Panel `/tts configurar`:** selección de voces con navegación, edición de apodo y opciones para restablecer preferencias.
- **Voces y configuración:** reorganización de los catálogos Edge/Azure y del almacenamiento de preferencias en SQLite.
- **Lectura de mensajes:** mejoras en las frases de menciones, respuestas y anuncios de imágenes, videos, enlaces, stickers, emojis y adjuntos combinados.
- **Colas y sesiones:** ajustes de reproducción progresiva, cancelación de mensajes, conexiones de voz y desconexión por inactividad.
- **Nueva web oficial:** PenguSpeak estrena página web propia con información del proyecto en [josueterrones2004.github.io/PenguSpeak-Web](https://josueterrones2004.github.io/PenguSpeak-Web/).
- **Mantenimiento:** reorganización interna de módulos y actualización de dependencias.

### 🌐 Web de PenguSpeak

La v1.3.0 coincide con el lanzamiento de la nueva web oficial de PenguSpeak:

**https://josueterrones2004.github.io/PenguSpeak-Web/**

La web se desarrolla en un repositorio independiente del bot: [PenguSpeak-Web](https://github.com/josueterrones2004/PenguSpeak-Web).

**Alcance:** este historial recoge los cambios de la v1.3.0 del bot y el lanzamiento de la web oficial asociado a esta versión. La incorporación inicial de Azure Speech corresponde a la versión anterior.
