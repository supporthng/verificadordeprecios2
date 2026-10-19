# Conector Windows v4.1 — correccion de dependencia SQL Server

## Causa confirmada
En v4, `bridge.py` linea 585 ejecuta `import pyodbc`, pero `windows_bridge/requirements.txt` no incluye `pyodbc`. El registro muestra `ModuleNotFoundError` en esa linea. Por ello las consultas fallan antes de abrir SQL Server.

## Cambios
- Agregado `pyodbc>=5.1,<6` a requirements.txt.
- Agregado `--hidden-import=pyodbc` al empaquetado PyInstaller.
- Comprobacion de importacion de pyodbc en la compilacion.
- Error explicito si el modulo falta.
- Se mantiene el funcionamiento universal y la configuracion existente; no se fijan bases de datos.

## Instalacion
1. Copia las carpetas `windows_bridge`, `installer` y `.github` a tu repositorio, reemplazando sus archivos.
2. Ejecuta el workflow `Construir conector Windows` en GitHub Actions.
3. Descarga el artefacto y ejecuta el nuevo instalador EXE como administrador.
4. Consulta un producto desde Streamlit.

**Nota:** El paquete es codigo fuente, no EXE. La compilacion Windows y la conexion SQL real deben validarse en el equipo. `pyodbc` no sustituye el controlador ODBC de Microsoft: el equipo debe tener el driver ODBC elegido instalado.
