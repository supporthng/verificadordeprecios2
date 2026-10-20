"""Prueba aislada del foco, sin consultar precios ni modificar el lector."""
import streamlit as st
import streamlit.components.v1 as components
from auth_usuarios import require

require("usuarios")
st.title("🧪 Prueba del Cursor")
st.caption("Prueba independiente: no modifica la consulta de precios.")
st.write("Al abrir esta página, intenta escanear sin hacer clic en el campo. Luego pulsa F5 y repite.")
components.html(r"""
<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
body{font-family:system-ui,Arial,sans-serif;margin:8px;color:#102b50}
input{box-sizing:border-box;width:100%;padding:15px;border:2px solid #a6bad9;border-radius:12px;font-size:22px;text-align:center}
input:focus{outline:none;border-color:#16823c;box-shadow:0 0 0 3px #d9f5df}
#estado{margin:12px 0;font-size:16px} #resultado{font-size:16px;overflow-wrap:anywhere}
</style></head><body>
<label for="codigo">Código de barras</label>
<input id="codigo" type="text" placeholder="Escanea sin hacer clic" autocomplete="off" autofocus>
<div id="estado">Comprobando foco...</div><div id="resultado"></div>
<script>
const campo=document.getElementById('codigo'), estado=document.getElementById('estado'), resultado=document.getElementById('resultado');
function comprobar(){estado.textContent=document.activeElement===campo?'✓ Cursor activo en el textbox':'⚠ Cursor no activo todavía';}
function enfocar(){try{window.focus();campo.focus({preventScroll:true});}catch(e){} comprobar();}
campo.addEventListener('focus',comprobar);campo.addEventListener('blur',comprobar);
campo.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();resultado.textContent='Código recibido: '+campo.value;campo.value='';enfocar();}});
window.addEventListener('focus',enfocar);
window.addEventListener('pageshow',()=>setTimeout(enfocar,100));
requestAnimationFrame(()=>setTimeout(enfocar,150));
</script></body></html>
""",height=195,scrolling=False)
st.info("Esta prueba utiliza un campo HTML dentro de un componente. Que funcione aquí no garantiza que Streamlit pueda enfocar su textbox nativo; comprobaremos el resultado antes de integrarlo.")
