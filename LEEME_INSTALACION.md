# Conector Windows — actualización de autoinicio v1.2 (fuentes)

Este ZIP contiene las carpetas `windows_bridge`, `installer` y `.github/workflows` listas para copiar a la raíz del repositorio. **No contiene un EXE compilado**.

## Cambios
- Actualiza `bridge.py` a la versión con consultas externas, corrige el atributo `cn.timeout` y registra la ubicación de los errores sin exponer mensajes ODBC en el log.
- Durante la instalación, detiene la tarea anterior y todos los procesos del ejecutable instalado, incluidos los procesos secundarios de PyInstaller; verifica que el puerto 8765 esté libre. Si otro programa ocupa el puerto, la instalación se detiene para evitar conflictos.
- Registra una tarea de arranque con Windows y una segunda tarea de vigilancia cada minuto. Esta última verifica `/health` y que el procesador de colas haya avanzado recientemente; si falla, detiene los procesos propios y solicita el reinicio de la tarea.
- Conserva `%PROGRAMDATA%\ConsultaPrecios\bridge.env` y `sql_credentials.dpapi` durante las actualizaciones.

## Compilar
1. Extrae el ZIP y copia las carpetas `.github`, `installer` y `windows_bridge` a la raíz del repositorio, reemplazando los archivos correspondientes.
2. En GitHub abre Actions > Construir conector Windows > Run workflow.
3. Descarga el artefacto `Conector-Windows-Portatil-e-Instalador` y ejecuta el instalador EXE como administrador.
4. Comprueba en PowerShell `Get-ScheduledTask ConsultaPreciosConectorLAN,ConsultaPreciosConectorVigilancia | Select TaskName,State` y `Invoke-RestMethod http://127.0.0.1:8765/health`.

## Importante
- **Sin probar en Windows todavía.** Se verificó la sintaxis Python y la integridad del ZIP; la compilación de Inno Setup y la ejecución de las tareas requieren una prueba real.
- La vigilancia usa una segunda tarea programada, no otra instancia permanente del conector.
- El endpoint `/health` no requiere autenticación y solo debe estar accesible en una red de confianza. No expongas el puerto 8765 a internet.
- No incluyas claves reales ni archivos `.env` con secretos en GitHub.
