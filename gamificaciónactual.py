# app.py (pegar completo en GitHub, sin líneas de instalación)
import streamlit as st
from PIL import Image
import io, csv
from datetime import datetime
import pandas as pd

# ---------- Config ----------
st.set_page_config(page_title="Gamificación - Selección de Tutores", layout="centered")
st.markdown("""
<style>
/* Minimalist styling */
.reportview-container .main {
    padding: 1.2rem 1.2rem 2rem 1.2rem;
}
.css-1d391kg {  /* streamlit main font-size adjust */
    font-size: 16px;
}
.card {
    border-radius: 12px;
    padding: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    background-color: white;
}
small { color: #6b7280; }
</style>
""", unsafe_allow_html=True)

st.title("🎮 Prototipo Gamificación — Selección de Tutores")
st.write("Prototipo editable. Completa tus datos, elige avatar, responde casos y envía tu resultado.")

# ---------- Avatares ----------
st.sidebar.header("Configuración / Edición (solo prototipo)")
mode = st.sidebar.selectbox("Modo", ["Jugar", "Editar preguntas (admin prototipo)"])

# Avatares (puedes reemplazar URLs por tus imágenes)
AVATARS = {
    "Alegre": "https://i.imgur.com/8Km9tLL.png",
    "Serio":  "https://i.imgur.com/3GvwNBf.png",
    "Creativo":"https://i.imgur.com/jZ5t9Zg.png",
    "Profesional":"https://i.imgur.com/4AiXzf8.png",
    "Empático":"https://i.imgur.com/2yAf7wE.png",
    "Enérgico":"https://i.imgur.com/t6Y2X7b.png"
}

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

# Guardar/recuperar preguntas en sesión para editar
if "questions" not in st.session_state:
    st.session_state["questions"] = default_questions.copy()

# ---------- Modo Edición ----------
if mode == "Editar preguntas (admin prototipo)":
    st.sidebar.markdown("### Editor de preguntas (prototipo)")
    if st.sidebar.button("Restaurar preguntas por defecto"):
        st.session_state["questions"] = default_questions.copy()
        st.sidebar.success("Restaurado.")
    # Mostrar y editar preguntas existentes
    for i, q in enumerate(st.session_state["questions"]):
        st.sidebar.markdown(f"**Pregunta {i+1}**")
        new_prompt = st.sidebar.text_input(f"Prompt {i+1}", value=q.get("prompt",""), key=f"prompt_{i}")
        q["prompt"] = new_prompt
        qtype = st.sidebar.selectbox(f"Tipo {i+1}", ["quiz","open","puzzle"], index=["quiz","open","puzzle"].index(q.get("type","quiz")), key=f"type_{i}")
        q["type"] = qtype
        if qtype == "quiz":
            opts = q.get("options", ["Opción 1","Opción 2","Opción 3"])
            # editable options as single line comma-separated
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
    st.stop()  # terminar render para no mostrar modo juego debajo cuando en edición

# ---------- Modo Juego ----------
st.subheader("1) Datos del postulante")
with st.form("form_datos"):
    dni = st.text_input("DNI")
    nombres = st.text_input("Nombres y apellidos")
    celular = st.text_input("Celular")
    correo = st.text_input("Correo")
    experiencia = st.text_area("Experiencia (breve)")
    educacion = st.text_area("Educación recibida (breve)")
    avatar_choice = st.selectbox("Elige tu avatar", list(AVATARS.keys()))
    submitted = st.form_submit_button("Guardar datos y continuar")
if submitted:
    st.success("Datos guardados (en memoria para esta sesión).")

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
        # open responses not auto-graded
        answers_for_csv.append(resp)
    elif q["type"] == "puzzle":
        # mostrar inputs para poner orden
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
    row = [now,dni,nombres,celular,correo,avatar_choice,total_score,experiencia,educacion] + answers_for_csv
    # CSV en memoria
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    writer.writerow(row)
    st.success("Resultado generado. Descarga abajo o copia el contenido.")
    st.download_button("Descargar resultado (CSV)", output.getvalue(), file_name=f"resultado_{nombres.replace(' ','_')[:20]}.csv", mime="text/csv")
    # Mostrar tabla previa
    df = pd.DataFrame([row], columns=header)
    st.table(df)

st.markdown("___")
st.caption("Prototipo desarrollado por Gabriel — edición y uso para presentación. No use datos sensibles en demos públicas.")

