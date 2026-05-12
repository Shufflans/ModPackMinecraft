# Sistema de Actualización Incremental de Modpacks

## Problema
Distribuir un modpack de 550 MB cada vez que hay un cambio (por ejemplo, un solo archivo de configuración) es ineficiente y frustrante para los usuarios.

## Solución
Un launcher Python que utiliza un archivo de manifiesto (JSON) con hashes SHA1 por archivo para comparar la versión local con la remota, descargando únicamente los archivos modificados o nuevos, y eliminando los obsoletos con respaldo automático.

## Tecnologías
- Python 3, tkinter, requests, hashlib
- GitHub Actions para generación automática de manifiesto y releases
- Empaquetado con PyInstaller para distribución de un solo .exe

## Arquitectura
[Diagrama mostrando cliente, repositorio, descarga selectiva]

## Resultados
Reducción del tiempo de actualización en un 95% para cambios pequeños. Experiencia de usuario sin intervención manual.

## Autor
Shufflan.
