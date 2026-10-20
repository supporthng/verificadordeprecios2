"""Prueba independiente del enfoque del lector. No modifica la aplicación principal."""
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Prueba de foco del lector", layout="centered")
st.title("Prueba de foco del lector")
st.write("Esta página es independiente. No consulta productos ni modifica Supabase.")

st.subheader("Prueba A — Campo nativo de Streamlit")
st.text_input("Campo A", key="prueba_foco_nativo", placeholder="Campo nativo: escanea aquí")
st.caption("Este campo permite comprobar si el foco se activa sin hacer clic.")

st.subheader("Prueba B — Campo dentro del componente")
components.html('''
<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
body{font:15px Arial,sans-serif;margin:0;padding:5px}
input{box-sizing:border-box;width:100%;padding:12px;border:2px solid #b9c8db;border-radius:8px;font-size:17px}
#status{padding:9px 0;font-weight:bold}button{padding:8px 12px;margin-right:5px}
</style></head><body>
<input id="scan" autofocus placeholder="Campo B: escanea aquí" autocomplete="off" />
<div id="status">Comprobando foco...</div>
<button id="btn" type="button">Activar campo B</button>
<script>
const field=document.getElementById('scan'), status=document.getElementById('status');
function report(){
 const isActive=document.activeElement===field;
 const hasFocus=document.hasFocus();
 status.textContent='Campo B activo: '+(isActive?'SÍ':'NO')+' | Ventana del componente activa: '+(hasFocus?'SÍ':'NO');
 status.style.color=(isActive&&hasFocus)?'#087f23':'#9c3818';
}
function focusField(){try{field.focus({preventScroll:true})}catch(e){field.focus()}report()}
document.getElementById('btn').onclick=focusField;
field.addEventListener('focus',report);field.addEventListener('blur',report);
window.addEventListener('focus',report);window.addEventListener('blur',report);
[0,150,500,1200,2500].forEach(t=>setTimeout(focusField,t));
setInterval(report,500);
</script></body></html>
''', height=165, scrolling=False)

st.info("Prueba: abre esta página o presiona F5. SIN hacer clic, mira si el Campo A o B muestra el cursor. Luego pulsa 'Activar campo B' y observa el indicador.")
st.caption("Para volver a la aplicación principal, abre su página normal. No necesitas cambiar ningún archivo existente.")
