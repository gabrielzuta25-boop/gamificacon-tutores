# app.py
import streamlit as st
from PIL import Image
import io, csv
from datetime import datetime
import pandas as pd
import requests
import os

# ---------- Config ----------
st.set_page_config(page_title="Gamificación - Selección de Tutores", layout="centered")
st.markdown("""
<style>
/* Minimalist styling */
.reportview-container .main {
    padding: 1.2rem 1.2rem 2rem 1.2rem;
}
.css-1d391kg { font-size: 16px; }
.card { border-radius: 12px; padding: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); background-color: white; }
small { color: #6b7280; }
.avatar-selected { outline: 3px solid #4f46e5; border-radius: 6px; padding: 3px; }
</style>
""", unsafe_allow_html=True)

st.title("🎮 Prototipo Gamificación — Selección de Tutores")
st.write("Prototipo editable. Completa tus datos, elige avatar, responde casos y envía tu resultado.")

# ---------- ADMIN AUTH ----------
# Preferimos leer desde st.secrets en Streamlit Cloud, si no existe usamos env var
ADMIN_PASS = None
try:
    ADMIN_PASS = st.secrets.get("ADMIN_PASS", None)
except Exception:
    ADMIN_PASS = os.getenv("ADMIN_PASS", None)

st.sidebar.header("Administración")
admin_input = st.sidebar.text_input("Clave admin (solo para editar)", type="password")

is_admin = False
if ADMIN_PASS:
    if admin_input and admin_input == ADMIN_PASS:
        is_admin = True
        st.sidebar.success("Autenticado como admin ✅")
    elif admin_input:
        st.sidebar.error("Clave incorrecta ❌")
else:
    st.sidebar.info("No se ha configurado ADMIN_PASS en Secrets. Añádela en Settings → Secrets si quieres bloqueo admin.")

# ---------- Avatars (DiceBear pixel-art) ----------
AVATAR_SEEDS = [
    "hawk","luna","milo","nova","zephyr","pixelkid","aurora","tiger","sable","echo"
]
AVATAR_URLS = {s: f"https://avatars.dicebear.com/api/pixel-art/{s}.png?size=64" for s in AVATAR_SEEDS}

st.sidebar.header("Modo")
mode_default = "Jugar"
mode = st.sidebar.selectbox("Modo", [mode_default, "Editar preguntas (admin prototipo)"] if is_admin else [mode_default], index=0)

# ---------- Preguntas por defecto (editable) ----------
default_questions = [
    {
        "type": "quiz",
        "prompt": "Caso 1: Un estudiante no alcanza el objetivo de la sesión. ¿Qué haces?",
        "options": ["Repetir la clase igual", "Adaptar la explicación y usar ejercicio práctico", "Sancionar al estudiante"],
        "correct_idx": 1,
        "points": 10,
        "explain": "Valora adaptación pedagógica."
    },
    {
        "type": "quiz",
        "prompt": "Caso 2: ¿Cuál es la mejor estrategia para explicar un concepto abstracto?",
        "options": ["Dar muchas definiciones teóricas", "Usar ejemplos concretos y analogías", "Pedir más tarea"],
        "correct_idx": 1,
        "points": 10,
        "explain": "Preferencia por ejemplos."
    },
    {
        "type": "open",
        "prompt": "Situación: Describe brevemente cómo motivarías a un grupo con baja asistencia.",
        "points": 10,
        "explain": "Se evalúa criterio didáctico."
    },
    {
        "type": "puzzle",
        "prompt": "Puzzle: Ordena las acciones para planificar una clase efectiva (1-3):  A) Evaluación inicial  B) Actividad práctica C) Objetivos claros",
        "correct_order": ["C","A","B"],
        "points": 10,
        "explain": "Secuencia lógica de planificación."
    }
]

if "questions" not in st.session_state:
    st.session_state["questions"] = default_questions.copy()

# ---------- Modo Edición (solo admin) ----------
if mode == "Editar preguntas (admin prototipo)":
    if not is_admin:
        st.sidebar.error("Necesitas ser admin para editar.")
        st.stop()
    st.sidebar.markdown("### Editor de preguntas (prototipo)")
    if st.sidebar.button("Restaurar preguntas por defecto"):
        st.session_state["questions"] = default_questions.copy()
        st.sidebar.success("Restaurado.")
    for i, q in enumerate(st.session_state["questions"]):
        st.sidebar.markdown(f"**Pregunta {i+1}**")
        new_prompt = st.sidebar.text_input(f"Prompt {i+1}", value=q.get("prompt",""), key=f"prompt_{i}")
        q["prompt"] = new_prompt
        qtype = st.sidebar.selectbox(f"Tipo {i+1}", ["quiz","open","puzzle"], index=["quiz","open","puzzle"].index(q.get("type","quiz")), key=f"type_{i}")
        q["type"] = qtype
        if qtype == "quiz":
            opts = q.get("options", ["Opción 1","Opción 2","Opción 3"])
            opts_line = st.sidebar.text_input(f"Opciones (separadas por ,) {i+1}", value=",".join(opts), key=f"opts_{i}")
            q["options"] = [o.strip() for o in opts_line.split(",") if o.strip()]
            corr = st.sidebar.number_input(f"Índice correcto (0-based) {i+1}", min_value=0, max_value=max(0,len(q["options"])-1), value=int(q.get("correct_idx",0)), key=f"corr_{i}")
            q["correct_idx"] = int(corr)
        if qtype == "puzzle":
            order = st.sidebar.text_input(f"Orden correcto (separado por ,) {i+1}", value=",".join(q.get("correct_order",[])), key=f"order_{i}")
            q["correct_order"] = [o.strip() for o in order.split(",") if o.strip()]
        pts = st.sidebar.number_input(f"Puntos {i+1}", min_value=0, value=int(q.get("points",10)), key=f"pts_{i}")
        q["points"] = int(pts)
    if st.sidebar.button("Añadir nueva pregunta"):
        st.session_state["questions"].append({
            "type":"quiz","prompt":"Nueva pregunta","options":["Opción A","Opción B"],"correct_idx":0,"points":10
        })
        st.sidebar.success("Pregunta añadida (aparece en la lista principal).")
    st.stop()

# ---------- Modo Juego ----------
st.subheader("1) Datos del postulante")

# Preparar session_state para avatar temporario si no existe
if "selected_avatar_temp" not in st.session_state:
    st.session_state["selected_avatar_temp"] = None

# Modal / formulario emergente para datos y selección de avatar (visual)
open_modal = st.button("📋 Completar datos personales")

if open_modal:
    with st.modal("Completa tus datos"):
        with st.form("form_modal_datos"):
            dni = st.text_input("DNI")
            nombres = st.text_input("Nombres y apellidos")
            celular = st.text_input("Celular")
            correo = st.text_input("Correo")
            experiencia = st.text_area("Experiencia (breve)")
            educacion = st.text_area("Educación recibida (breve)")

            st.write("Elige tu avatar (clic en 'Elegir'):")
            cols = st.columns(len(AVATAR_SEEDS))
            # mostrar imágenes y botones para seleccionar; guardamos elección en session_state['selected_avatar_temp']
            for c, seed in zip(cols, AVATAR_SEEDS):
                url = AVATAR_URLS[seed]
                try:
                    r = requests.get(url, timeout=5)
                    img = Image.open(io.BytesIO(r.content))
                    if st.session_state.get("selected_avatar_temp") == seed:
                        c.image(img, caption=seed, use_column_width=False)
                        c.markdown(f"<div class='avatar-selected'>Seleccionado</div>", unsafe_allow_html=True)
                    else:
                        c.image(img, caption=seed, use_column_width=False)
                except Exception:
                    c.write("Avatar")
                if c.button("Elegir", key=f"avatar_btn_{seed}"):
                    st.session_state["selected_avatar_temp"] = seed

            enviar = st.form_submit_button("Guardar y cerrar")
        if enviar:
            # guardar datos en session_state para uso posterior
            st.session_state["dni"] = dni
            st.session_state["nombres"] = nombres
            st.session_state["celular"] = celular
            st.session_state["correo"] = correo
            st.session_state["experiencia"] = experiencia
            st.session_state["educacion"] = educacion
            # si el usuario no seleccionó explicitamente avatar, usamos la temporal o el primero
            chosen = st.session_state.get("selected_avatar_temp", AVATAR_SEEDS[0])
            st.session_state["avatar_choice"] = chosen
            st.success("Datos guardados correctamente ✅")
            st.experimental_rerun()

# Mostrar resumen si ya hay datos guardados
if st.session_state.get("nombres"):
    # mostrar mini avatar junto al nombre
    avatar_name = st.session_state.get("avatar_choice", AVATAR_SEEDS[0])
    avatar_url = AVATAR_URLS.get(avatar_name)
    if avatar_url:
        try:
            r = requests.get(avatar_url, timeout=5)
            img = Image.open(io.BytesIO(r.content))
            st.image(img, width=64)
        except Exception:
            pass
    st.markdown(f"**Postulante:** {st.session_state.get('nombres')}  \n**Avatar:** {avatar_name}")
else:
    st.info("Aún no has completado tus datos. Haz clic en '📋 Completar datos personales'.")

st.markdown("---")
st.subheader("2) Evaluación: casos, quiz y puzzle")
total_score = 0
answers_for_csv = []

for idx, q in enumerate(st.session_state["questions"]):
    st.markdown(f"**Pregunta {idx+1}.**")
    st.write(q.get("prompt",""))
    if q["type"] == "quiz":
        opt = st.radio("", q["options"], key=f"q_{idx}")
        sel_idx = q["options"].index(opt)
        correct = (sel_idx == q.get("correct_idx",0))
        if correct:
            st.write("✅ Opción evaluada como correcta.")
            total_score += q.get("points",10)
        else:
            st.write("❌ Opción considerada no óptima.")
        answers_for_csv.append(opt)
    elif q["type"] == "open":
        resp = st.text_area("", key=f"open_{idx}", placeholder="Escribe tu respuesta...")
        answers_for_csv.append(resp)
    elif q["type"] == "puzzle":
        st.write("Ingresa el orden correcto (separado por comas). Usa etiquetas propuestas o letras.")
        resp = st.text_input("Tu orden", key=f"puz_{idx}", placeholder="Ej: C,A,B")
        user_order = [s.strip() for s in resp.split(",") if s.strip()]
        if user_order and "correct_order" in q and user_order == q["correct_order"]:
            st.write("✅ Orden correcto.")
            total_score += q.get("points",10)
        elif user_order:
            st.write("❌ Orden distinto al esperado.")
        answers_for_csv.append(resp)
    st.markdown("---")

st.subheader(f"Resultado provisional: {total_score} pts")

# ---------- Envío / Guardado ----------
if st.button("Enviar y generar resultado (descargar CSV)"):
    now = datetime.now().isoformat()
    header = ["timestamp","dni","nombres","celular","correo","avatar","score","experiencia","educacion"] + [f"q{i+1}" for i in range(len(st.session_state["questions"]))]
    row = [
        now,
        st.session_state.get("dni",""),
        st.session_state.get("nombres",""),
        st.session_state.get("celular",""),
        st.session_state.get("correo",""),
        st.session_state.get("avatar_choice",""),
        total_score,
        st.session_state.get("experiencia",""),
        st.session_state.get("educacion",""),
    ] + answers_for_csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    writer.writerow(row)
    st.success("Resultado generado. Descarga abajo o copia el contenido.")
    st.download_button("Descargar resultado (CSV)", output.getvalue(), file_name=f"resultado_{st.session_state.get('nombres','postulante')[:20]}.csv", mime="text/csv")
    df = pd.DataFrame([row], columns=header)
    st.table(df)

st.markdown("___")
st.caption("Prototipo desarrollado por Gabriel — edición y uso para presentación. No use datos sensibles en demos públicas.")


st.markdown("___")
st.caption("Prototipo desarrollado por Gabriel — edición y uso para presentación. No use datos sensibles en demos públicas.")

