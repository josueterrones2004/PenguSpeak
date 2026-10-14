# Changelog — PenguSpeak

## [v1.3.0] — Actualización del bot

Cambios incorporados en esta actualización:

- **Respaldo automático:** Edge TTS permanece como motor principal. Cuando falla, PenguSpeak utiliza Azure Speech si está configurado y comprueba periódicamente si Edge vuelve a estar disponible.
- **Avisos del servicio:** notificaciones del cambio a Azure y del regreso a Edge para servidores que estén utilizando TTS, sin repetir avisos innecesarios.
- **Panel `/tts configurar`:** selección de voces con navegación, edición de apodo y opciones para restablecer preferencias.
- **Voces y configuración:** reorganización de los catálogos Edge/Azure y del almacenamiento de preferencias en SQLite.
- **Lectura de mensajes:** mejoras en las frases de menciones, respuestas y anuncios de imágenes, videos, enlaces y adjuntos combinados.
- **Colas y sesiones:** ajustes de reproducción progresiva, cancelación de mensajes, conexiones de voz y desconexión por inactividad.
- **Mantenimiento:** reorganización interna de módulos y actualización de dependencias.

**Alcance:** este historial recoge únicamente los cambios de la v1.3.0 del bot. La incorporación inicial de Azure Speech corresponde a la versión anterior. La nueva página web no forma parte de esta actualización.
