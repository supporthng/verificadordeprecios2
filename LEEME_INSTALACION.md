# Conector Windows v4 — diagnóstico SQL y registros

Paquete de fuentes para GitHub; no contiene EXE compilado.

Cambios: `/health` muestra versión, ruta y estado del registro, cantidad de trabajos, último trabajo y tipo de último error (sin credenciales). Se registran las etapas de conexión y consulta SQL, así como el traceback de fallos, sin imprimir SQL credentials. Se conservan la configuración, los mecanismos de arranque y el carácter configurable de las bases/tablas/columnas.

**Instalación:** copiar `.github`, `installer` y `windows_bridge` al repositorio, compilar en GitHub Actions y ejecutar el instalador generado. Después consultar `http://127.0.0.1:8765/health` y confirmar `asistente-universal-v4`. Ante fallo de consulta, mirar `log_path` y `last_error_type`.

**Limitación:** esta versión instrumenta el error para determinar su causa; no garantiza que SQL Server quede corregido sin conocer el error real. No se ha probado en Windows.
