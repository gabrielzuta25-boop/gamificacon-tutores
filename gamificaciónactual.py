# app.py - Versión limpia y profesional sin modal, todo en la página
import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import random
import os

# ---------- Config & CSS ----------
st.set_page_config(page_title="Gamificación — Selección de Tutores", layout="wide")
st.markdown("""
<style>
:root {
  --bg: #0b1220;
  --card: linear-gradient(180deg,#0f1724,#0c1320);
  --muted: #9aa7bf;
  --accent: #7c3aed;
  --text: #e6eef8;
  --glass: rgba(255,255,255,0.02);
}
html, body, [class*="css"] { background: var(--bg); color: var(--text); }
.container { max-width:1200px; margin:18px auto; font-family:Inter, system-ui, sans-serif; }
.card { background: var(--card); padding:16px; border-radius:12px; box-shadow: 0 8px 28px rgba(2,6,23,0.6); border:1px solid rgba(255,255,255,0.03); }
.title { font-size:22px; font-weight:700; color:var(--text); margin-bottom:4px; }
.muted { color:var(--muted); font-size:13px; margin-bottom:10px; }
.row { display:flex; gap:18px; align-items:flex-start; }
.col-2 { flex:2; }
.col-1 { flex:1; }
.avatar { font-size:56px; display:inline-block; padding:10px; border-radius:10px; background:var(--glass); }
.small { font-size:13px; color:var(--muted); }
.progress-steps { display:flex; gap:8px; align-items:center; margin-top:6px; }
.step-dot { width:12px; height:12px; border-radius:6px; background:#1f2937; border:1px solid rgba(255,255,255,0.03); }
.step-dot.done { background:var(--accent); box-shadow:0 0 8px rgba(124,58,237,0.12); }
.question-area { min-height:170px; margin-top:8px; }
.buttons { display:flex; gap:8px; margin-top:12px; }
.btn { background:#111827; color:var(--text); padding:8px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.03); cursor:pointer; }
.shop-item { display:flex; justify-content:space-between; align-items:center; padding:8px; border-radius:8px; background:rgba(255,255,255,0.02); margin-bottom:8px; }
.final-avatar { text-align:center; }
.footer-note { color:var(--muted); font-size:12px; margin-top:8px; }
</style>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
def csv_download_link_from_df(df, filename="submissions.csv"):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Descargar CSV</a>'

# ---------- Content: questions ----------
QUESTIONS = [
    # 5 open/opinion
    {"id":"o1","type":"open","title":"Opinión 1","prompt":"¿Cuál crees que es la característica más importante en un tutor preuniversitario?"},
    {"id":"o2","type":"open","title":"Opinión 2","prompt":"Describe tu estilo de enseñanza en 2-3 frases."},
    {"id":"o3","type":"open","title":"Opinión 3","prompt":"¿Qué método usas para mantener la atención en clase?"},
    {"id":"o4","type":"open","title":"Opinión 4","prompt":"¿Cómo organizas una sesión para un tema difícil?"},
    {"id":"o5","type":"open","title":"Opinión 5","prompt":"¿Qué diferencias harías entre explicar a nivel escolar y preuniversitario?"},
    # 3 cases (textual scenarios)
    {"id":"c1","type":"case","title":"Caso 1","prompt":"Un alumno está frustrado y evita participar. Describe cómo lo abordarías paso a paso."},
    {"id":"c2","type":"case","title":"Caso 2","prompt":"El grupo es heterogéneo: algunos avanzan rápido, otros no. ¿Cómo organizarías la clase?"}, 
    {"id":"c3","type":"case","title":"Caso 3","prompt":"Hay un conflicto entre dos estudiantes que afecta la dinámica. ¿Qué medidas tomarías?"},
    # 2 puzzles (order)
    {"id":"p1","type":"puzzle","title":"Puzzle 1","prompt":"Ordena: A) Actividad práctica, B) Objetivos claros, C) Evaluación inicial. (ej: B,C,A)","correct":["B","C","A"]},
    {"id":"p2","type":"puzzle","title":"Puzzle 2","prompt":"Ordena: A) Resumen, B) Retroalimentación, C) Tarea sugerida. (ej: A,B,C)","correct":["A","B","C"]},
]
TOTAL = len(QUESTIONS)

# ---------- Session init ----------
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "answers" not in st.session_state:
    st.session_state.answers = [""] * TOTAL
if "name" not in st.session_state:
    st.session_state.name = ""
if "dni" not in st.session_state:
    st.session_state.dni = ""
if "cel" not in st.session_state:
    st.session_state.cel = ""
if "email" not in st.session_state:
    st.session_state.email = ""
if "exp" not in st.session_state:
    st.session_state.exp = ""
if "edu" not in st.session_state:
    st.session_state.edu = ""
if "avatar" not in st.session_state:
    st.session_state.avatar = "🛡️"  # default emoji avatar
if "coins" not in st.session_state:
    st.session_state.coins = 50
if "xp" not in st.session_state:
    st.session_state.xp = 0
if "level" not in st.session_state:
    st.session_state.level = 1
if "owned" not in st.session_state:
    st.session_state.owned = []
if "submissions" not in st.session_state:
    st.session_state.submissions = []

# Accessories & avatars definitions
AVATARS = [
    {"id":"knight","emoji":"🛡️","label":"Defensor"},
    {"id":"mage","emoji":"🧙","label":"Estratega"},
    {"id":"mentor","emoji":"🧑‍🏫","label":"Mentor"}
]
ACCESSORIES = [
    {"id":"gafas","emoji":"🕶️","label":"Gafas","price":30},
    {"id":"gorra","emoji":"🧢","label":"Gorra","price":20},
    {"id":"libro","emoji":"📚","label":"Libro","price":40},
    {"id":"estrella","emoji":"⭐","label":"Medalla","price":60},
]

# ---------- Page container ----------
st.markdown('<div class="container">', unsafe_allow_html=True)

# ---------- Personal data form (CORREGIDO) ----------
# Coloca este bloque donde esté el formulario de datos (reemplaza el anterior)
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="title">Datos personales (confidencial)</div>', unsafe_allow_html=True)
st.markdown('<div class="muted">Completa estos datos antes de avanzar.</div>', unsafe_allow_html=True)

# Build a list of avatar choices labels for the radio
avatar_labels = [f'{a["emoji"]}  {a["label"]}' for a in AVATARS]
default_idx = 0
for i,a in enumerate(AVATARS):
    if a["emoji"] == st.session_state.avatar:
        default_idx = i

with st.form("personal_form_fixed"):
    name_in = st.text_input("Nombres y apellidos", value=st.session_state.name)
    dni_in = st.text_input("DNI", value=st.session_state.dni)
    cel_in = st.text_input("Celular", value=st.session_state.cel)
    email_in = st.text_input("Correo", value=st.session_state.email)
    exp_in = st.text_area("Experiencia (breve)", value=st.session_state.exp, height=80)
    edu_in = st.text_area("Educación recibida (breve)", value=st.session_state.edu, height=80)

    st.markdown("**Selecciona un avatar**")
    avatar_choice = st.radio("", avatar_labels, index=default_idx)

    # Submit button for form
    submitted_personal = st.form_submit_button("Guardar datos")

if submitted_personal:
    # Save into session_state
    st.session_state.name = name_in
    st.session_state.dni = dni_in
    st.session_state.cel = cel_in
    st.session_state.email = email_in
    st.session_state.exp = exp_in
    st.session_state.edu = edu_in
    # extract emoji from selected label
    st.session_state.avatar = avatar_choice.split()[0]
    st.success("Datos guardados ✔️")


with top_col_right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    # profile summary small card
    st.markdown(f"<div style='display:flex;align-items:center;gap:12px'><div class='avatar'>{st.session_state.avatar}</div><div><strong style='font-size:16px'>{st.session_state.name or '(Sin nombre)'}</strong><div class='small'>Nivel {st.session_state.level} • XP {st.session_state.xp}</div></div></div>", unsafe_allow_html=True)
    st.markdown("<div style='margin-top:12px'><strong>Coins</strong></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:20px'>{st.session_state.coins} 💰</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Main content: questions + right side shop/progress ----------
main_col, side_col = st.columns([3,1], gap="large")

# Main column with question card
with main_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    idx = st.session_state.idx
    q = QUESTIONS[idx]
    # Header with step and title
    st.markdown(f"### Paso {idx+1} de {TOTAL} — {q['title']}")
    st.markdown(f"**{q['prompt']}**")
    st.markdown('<div class="question-area">', unsafe_allow_html=True)
    # Inputs by type
    if q["type"] in ("open", "case"):
        txt = st.text_area("Tu respuesta (confidencial):", value=st.session_state.answers[idx], key=f"ans_{idx}", height=180)
        st.session_state.answers[idx] = txt
    elif q["type"] == "puzzle":
        txt = st.text_input("Orden (ej: B,A,C):", value=st.session_state.answers[idx], key=f"ans_{idx}")
        st.session_state.answers[idx] = txt
    st.markdown('</div>', unsafe_allow_html=True)

    # Buttons row
    cols = st.columns([1,1,1])
    with cols[0]:
        if st.button("← Anterior"):
            if st.session_state.idx > 0:
                st.session_state.idx -= 1
    with cols[1]:
        if st.button("Guardar y siguiente →"):
            # require name
            if not st.session_state.name:
                st.warning("Primero guarda tus datos personales (arriba).")
            else:
                # reward progression
                st.session_state.coins += 7
                st.session_state.xp += 12
                if st.session_state.xp >= st.session_state.level * 100:
                    st.session_state.level += 1
                    st.session_state.coins += 30
                    st.success(f"¡subiste al nivel {st.session_state.level}! +30 coins")
                if st.session_state.idx < TOTAL - 1:
                    st.session_state.idx += 1
                else:
                    st.success("Has completado todas las preguntas. Pulsa 'Enviar todo' abajo cuando quieras.")
    with cols[2]:
        if st.button("Reiniciar intento"):
            st.session_state.idx = 0
            st.session_state.answers = [""] * TOTAL
            st.session_state.coins = 50
            st.session_state.xp = 0
            st.session_state.level = 1
            st.session_state.owned = []
            st.success("Sesión reiniciada.")

    st.markdown('</div>', unsafe_allow_html=True)

# Side column: progress and shop
with side_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    # Progress dots
    dots_html = "<div class='progress-steps'>"
    for i in range(TOTAL):
        cls = "step-dot done" if i <= st.session_state.idx else "step-dot"
        dots_html += f"<div class='{cls}' title='Paso {i+1}'></div>"
    dots_html += "</div>"
    st.markdown(dots_html, unsafe_allow_html=True)
    st.markdown(f"<div class='small'>Paso {st.session_state.idx+1} de {TOTAL}</div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<strong>🛍️ Tienda</strong>", unsafe_allow_html=True)
    st.markdown("<div class='small'>Personaliza tu avatar con accesorios (emoji).</div>", unsafe_allow_html=True)
    for item in ACCESSORIES:
        cols = st.columns([2,1])
        with cols[0]:
            st.markdown(f"{item['emoji']} <strong>{item['label']}</strong> <span class='small'>- {item['price']} coins</span>", unsafe_allow_html=True)
        with cols[1]:
            if item["id"] in st.session_state.owned:
                st.button("Comprado", key=f"owned_{item['id']}", disabled=True)
            else:
                if st.button("Comprar", key=f"buy_{item['id']}"):
                    if st.session_state.coins >= item['price']:
                        st.session_state.coins -= item['price']
                        st.session_state.owned.append(item["id"])
                        st.success(f"Compraste {item['label']} ✅")
                    else:
                        st.error("No tienes suficientes coins.")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Final submission card ----------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### ✅ Enviar todo (registro confidencial)")
st.markdown('<div class="small">Cuando termines todas las preguntas, pulsa ENVIAR. Nosotros evaluamos internamente; tus respuestas no se muestran a otros usuarios.</div>', unsafe_allow_html=True)
if st.button("Enviar todo"):
    if not st.session_state.name:
        st.warning("Completa tus datos antes de enviar (arriba).")
    else:
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "name": st.session_state.name,
            "dni": st.session_state.dni,
            "cel": st.session_state.cel,
            "email": st.session_state.email,
            "exp": st.session_state.exp,
            "edu": st.session_state.edu,
            "avatar": st.session_state.avatar,
            "owned": ",".join(st.session_state.owned),
            "coins": st.session_state.coins,
            "xp": st.session_state.xp,
            "level": st.session_state.level,
            "answers": st.session_state.answers,
        }
        st.session_state.submissions.append(record)
        st.success("Tu intento ha sido registrado. ¡Gracias! 🎉")
        # Show final avatar composition (emoji + accessories)
        badges = " ".join([acc["emoji"] for acc in ACCESSORIES if acc["id"] in st.session_state.owned])
        st.markdown(f"<div class='final-avatar'><div style='font-size:120px'>{st.session_state.avatar}</div><div style='font-size:28px'>{badges}</div><div style='margin-top:8px;font-weight:600'>Gracias, nos vemos pronto 😊</div></div>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ---------- Admin download panel (protected) ----------
st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
st.markdown('<div class="small">Si eres admin y quieres descargar los registros, ingresa la clave abajo.</div>', unsafe_allow_html=True)
admin_key = st.text_input("Clave admin (solo descarga)", type="password", key="admin_key_input")
if admin_key:
    try:
        secret = st.secrets.get("ADMIN_PASS", None)
    except Exception:
        secret = os.getenv("ADMIN_PASS", None)
    if secret and admin_key == secret:
        st.success("Acceso admin verificado.")
        if st.session_state.submissions:
            df = pd.DataFrame(st.session_state.submissions)
            st.markdown(csv_download_link_from_df(df, "submissions.csv"), unsafe_allow_html=True)
            st.markdown(f"Intentos registrados: {len(df)}")
        else:
            st.info("No hay intentos registrados aún.")
    else:
        st.error("Clave incorrecta.")

st.markdown('<div class="footer-note">Nota: este prototipo guarda datos en la memoria de la app. Para producción, conecta Google Sheets o una base de datos para persistencia.</div>', unsafe_allow_html=True)

# End container
st.markdown('</div>', unsafe_allow_html=True)
