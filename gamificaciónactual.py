# app.py
import streamlit as st
import pandas as pd
import io, base64, random
from datetime import datetime
import os

# ---------- Config ----------
st.set_page_config(page_title="Gamificación — Selección de Tutores", layout="wide")
st.markdown(
    """
    <style>
    :root {
      --bg: #0b1220;
      --card: #0f1724;
      --muted: #9aa7bf;
      --accent: #7c3aed;
      --text: #e6eef8;
    }
    body { background: var(--bg); color: var(--text); }
    .container { max-width:1200px; margin:18px auto; }
    .card { background: var(--card); padding:18px; border-radius:12px; box-shadow: 0 8px 28px rgba(2,6,23,0.6); border:1px solid rgba(255,255,255,0.03); }
    .title { font-size:24px; font-weight:700; margin:0 0 6px 0; color:var(--text); }
    .muted { color: var(--muted); font-size:13px; margin-bottom:10px; }
    .progress-steps { display:flex; gap:10px; align-items:center; }
    .step-dot { width:12px; height:12px; border-radius:6px; background:#1f2937; border:1px solid rgba(255,255,255,0.03); }
    .step-dot.done { background: var(--accent); box-shadow:0 0 8px rgba(124,58,237,0.12); }
    .question-area { min-height:180px; margin-top:8px; }
    .footer-small { color:var(--muted); font-size:12px; margin-top:8px; }
    .avatar-preview { font-size:48px; display:inline-block; padding:8px; border-radius:10px; background:rgba(255,255,255,0.02); }
    .accessory-badge { font-size:20px; margin-right:6px; }
    .shop-btn { border-radius:8px; padding:6px 10px; background:#111827; color:var(--text); border:1px solid rgba(255,255,255,0.03); }
    .center { text-align:center; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Helpers ----------
def csv_download_link(df, filename="submissions.csv"):
    csv_str = df.to_csv(index=False)
    b64 = base64.b64encode(csv_str.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Descargar CSV</a>'

# ---------- Admin Secret ----------
try:
    ADMIN_SECRET = st.secrets.get("ADMIN_PASS", None)
except Exception:
    ADMIN_SECRET = os.getenv("ADMIN_PASS", None)

# ---------- Questionnaire setup ----------
QUESTIONS = [
    # 5 opinion (open)
    {"id":"o1","type":"open","title":"Opinión 1","prompt":"¿Cuál crees que es la característica más importante en un tutor preuniversitario?"},
    {"id":"o2","type":"open","title":"Opinión 2","prompt":"Describe tu estilo de enseñanza en 2-3 frases."},
    {"id":"o3","type":"open","title":"Opinión 3","prompt":"¿Qué método usas para mantener la atención en clase?"},
    {"id":"o4","type":"open","title":"Opinión 4","prompt":"¿Cómo organizas una sesión para un tema difícil?"},
    {"id":"o5","type":"open","title":"Opinión 5","prompt":"¿Qué diferencias harías entre explicar a nivel escolar y preuniversitario?"},
    # 3 cases (no images; description only)
    {"id":"c1","type":"case","title":"Caso 1","prompt":"(Caso) Un alumno claramente frustrado con un ejercicio. Describe tu intervención paso a paso."},
    {"id":"c2","type":"case","title":"Caso 2","prompt":"(Caso) Un grupo muy heterogéneo: algunos avanzan rápido y otros no. ¿Cómo organizas la clase?"},
    {"id":"c3","type":"case","title":"Caso 3","prompt":"(Caso) Un conflicto entre dos estudiantes impacta la dinámica. ¿Qué medidas tomas?"},
    # 2 puzzles (order)
    {"id":"p1","type":"puzzle","title":"Puzzle 1","prompt":"Ordena: A) Actividad práctica, B) Objetivos claros, C) Evaluación inicial. (ej: B,C,A)","correct":["B","C","A"]},
    {"id":"p2","type":"puzzle","title":"Puzzle 2","prompt":"Ordena: A) Resumen, B) Retroalimentación, C) Tarea sugerida. (ej: A,B,C)","correct":["A","B","C"]},
]
TOTAL = len(QUESTIONS)

# ---------- Session state init ----------
if "index" not in st.session_state:
    st.session_state["index"] = 0
if "answers" not in st.session_state:
    st.session_state["answers"] = [""] * TOTAL
if "coins" not in st.session_state:
    st.session_state["coins"] = 50
if "xp" not in st.session_state:
    st.session_state["xp"] = 0
if "level" not in st.session_state:
    st.session_state["level"] = 1
if "owned" not in st.session_state:
    st.session_state["owned"] = []
if "avatar" not in st.session_state:
    # three avatar emojis
    st.session_state["avatar"] = "🛡️"
if "name" not in st.session_state:
    st.session_state["name"] = ""
if "dni" not in st.session_state:
    st.session_state["dni"] = ""
if "cel" not in st.session_state:
    st.session_state["cel"] = ""
if "email" not in st.session_state:
    st.session_state["email"] = ""
if "exp" not in st.session_state:
    st.session_state["exp"] = ""
if "edu" not in st.session_state:
    st.session_state["edu"] = ""
if "submissions" not in st.session_state:
    st.session_state["submissions"] = []

# Accessories (emoji) available in shop
ACCESSORIES = [
    {"id":"gafas","emoji":"🕶️","label":"Gafas","price":30},
    {"id":"gorra","emoji":"🧢","label":"Gorra","price":20},
    {"id":"libro","emoji":"📚","label":"Libro","price":40},
    {"id":"estrella","emoji":"⭐","label":"Medalla","price":60},
]

# Avatar choices (emoji + label)
AVATARS = [
    {"id":"knight","emoji":"🛡️","label":"Defensor"},
    {"id":"mage","emoji":"🧙","label":"Estratega"},
    {"id":"tutor","emoji":"🧑‍🏫","label":"Mentor"},
]

# ---------- Layout top (title + CTA to fill data modal) ----------
st.markdown('<div class="container">', unsafe_allow_html=True)
st.markdown('<div class="card">', unsafe_allow_html=True)
col_t1, col_t2 = st.columns([3,1])
with col_t1:
    st.markdown('<div class="title">🎮 Gamificación — Selección de Tutores</div>', unsafe_allow_html=True)
    st.markdown('<div class="muted">Responde con sinceridad. Tus respuestas se almacenan de forma confidencial y se evaluarán internamente.</div>', unsafe_allow_html=True)
with col_t2:
    # Personal data button (opens modal or expander)
    if st.button("📋 Completar mis datos"):
        # modal if available
        if hasattr(st, "modal"):
            modal = st.modal("Tus datos (confidencial)")
            with modal:
                with st.form("form_personal"):
                    name = st.text_input("Nombres y apellidos", value=st.session_state["name"])
                    dni = st.text_input("DNI", value=st.session_state["dni"])
                    cel = st.text_input("Celular", value=st.session_state["cel"])
                    email = st.text_input("Correo", value=st.session_state["email"])
                    exp = st.text_area("Experiencia (breve)", value=st.session_state["exp"], height=80)
                    edu = st.text_area("Educación recibida (breve)", value=st.session_state["edu"], height=80)
                    st.markdown("**Elige tu avatar**")
                    avatar_choice = st.radio("", [f'{a["emoji"]}  {a["label"]}' for a in AVATARS], index=[a["emoji"] for a in AVATARS].index(st.session_state["avatar"]) if st.session_state["avatar"] in [a["emoji"] for a in AVATARS] else 0)
                    submit = st.form_submit_button("Guardar y cerrar")
                    if submit:
                        st.session_state["name"] = name
                        st.session_state["dni"] = dni
                        st.session_state["cel"] = cel
                        st.session_state["email"] = email
                        st.session_state["exp"] = exp
                        st.session_state["edu"] = edu
                        # set avatar emoji based on selection
                        sel_emoji = avatar_choice.split()[0]
                        st.session_state["avatar"] = sel_emoji
                        st.success("Datos guardados ✔️")
                        st.experimental_rerun()
        else:
            with st.expander("Tus datos (confidencial)"):
                with st.form("form_personal2"):
                    name = st.text_input("Nombres y apellidos", value=st.session_state["name"])
                    dni = st.text_input("DNI", value=st.session_state["dni"])
                    cel = st.text_input("Celular", value=st.session_state["cel"])
                    email = st.text_input("Correo", value=st.session_state["email"])
                    exp = st.text_area("Experiencia (breve)", value=st.session_state["exp"], height=80)
                    edu = st.text_area("Educación recibida (breve)", value=st.session_state["edu"], height=80)
                    st.markdown("**Elige tu avatar**")
                    avatar_choice = st.radio("", [f'{a["emoji"]}  {a["label"]}' for a in AVATARS], index=[a["emoji"] for a in AVATARS].index(st.session_state["avatar"]) if st.session_state["avatar"] in [a["emoji"] for a in AVATARS] else 0)
                    submit = st.form_submit_button("Guardar y cerrar")
                    if submit:
                        st.session_state["name"] = name
                        st.session_state["dni"] = dni
                        st.session_state["cel"] = cel
                        st.session_state["email"] = email
                        st.session_state["exp"] = exp
                        st.session_state["edu"] = edu
                        sel_emoji = avatar_choice.split()[0]
                        st.session_state["avatar"] = sel_emoji
                        st.success("Datos guardados ✔️")
                        st.experimental_rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ---------- Main content: question area + right column (shop/progress) ----------
col_main, col_side = st.columns([3,1], gap="large")

with col_main:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    # show avatar (emoji) and small greeting
    avatar_display = st.session_state["avatar"]
    name_display = st.session_state["name"] if st.session_state["name"] else "(Sin nombre)"
    st.markdown(f"<div style='display:flex;align-items:center;gap:12px'><div class='avatar-preview'>{avatar_display}</div><div><strong>{name_display}</strong><div class='muted'>Nivel {st.session_state['level']} • XP {st.session_state['xp']} • Coins {st.session_state['coins']}</div></div></div>", unsafe_allow_html=True)

    st.write("")  # small separation

    idx = st.session_state["index"]
    q = QUESTIONS[idx]
    # Progress mini indicator (text)
    st.markdown(f"### Paso {idx+1} de {TOTAL}: {q['title']}")
    st.markdown(f"**{q['prompt']}**")
    st.markdown('<div class="question-area">', unsafe_allow_html=True)

    # Inputs by type (no immediate feedback about correctness)
    if q["type"] in ["open","case"]:
        prev = st.session_state["answers"][idx]
        ans = st.text_area("Tu respuesta (confidencial):", value=prev, height=160, placeholder="Escribe con claridad...")
        st.session_state["answers"][idx] = ans
    elif q["type"] == "puzzle":
        prev = st.session_state["answers"][idx]
        order = st.text_input("Orden (ej: B,A,C):", value=prev, placeholder="Ej: B,A,C")
        st.session_state["answers"][idx] = order

    st.markdown('</div>', unsafe_allow_html=True)

    # Navigation buttons
    nav_l, nav_c, nav_r = st.columns([1,1,1])
    with nav_l:
        if st.button("← Anterior"):
            if st.session_state["index"] > 0:
                st.session_state["index"] -= 1
    with nav_c:
        if st.button("Guardar y siguiente →"):
            if not st.session_state["name"]:
                st.warning("Completa tus datos primero (botón '📋 Completar mis datos').")
            else:
                # add rewards for moving forward
                st.session_state["coins"] += 7
                st.session_state["xp"] += 12
                # level up condition
                if st.session_state["xp"] >= st.session_state["level"] * 100:
                    st.session_state["level"] += 1
                    st.session_state["coins"] += 30
                    st.success(f"¡Subiste al nivel {st.session_state['level']}! Has recibido 30 coins.")
                if st.session_state["index"] < TOTAL - 1:
                    st.session_state["index"] += 1
                else:
                    st.success("Ya completaste todas las preguntas. Pulsa ENVIAR todo abajo cuando estés listo.")
    with nav_r:
        if st.button("Marcar/flag"):
            st.session_state.setdefault("flags", []).append(q["id"])
            st.success("Marcado para revisión interna.")

    st.markdown('</div>', unsafe_allow_html=True)

with col_side:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    # Progress path visualization (dots)
    st.markdown("<div style='margin-bottom:10px;'><strong>Progreso</strong></div>", unsafe_allow_html=True)
    dots_html = "<div class='progress-steps' aria-hidden='true'>"
    for i in range(TOTAL):
        cls = "step-dot done" if i <= st.session_state["index"] else "step-dot"
        dots_html += f"<div class='{cls}' title='Paso {i+1}'></div>"
    dots_html += "</div>"
    st.markdown(dots_html, unsafe_allow_html=True)
    st.markdown(f"<div class='muted'>Paso {st.session_state['index']+1} de {TOTAL}</div>", unsafe_allow_html=True)

    st.write("---")
    st.markdown("<strong>🛍️ Tienda</strong>", unsafe_allow_html=True)
    st.markdown("<div class='muted'>Personaliza tu avatar con accesorios (emojis).</div>", unsafe_allow_html=True)
    for item in ACCESSORIES:
        cols = st.columns([2,1])
        with cols[0]:
            st.markdown(f"{item['emoji']}  **{item['label']}**  <span class='muted'>- {item['price']} coins</span>", unsafe_allow_html=True)
        with cols[1]:
            if item["id"] in st.session_state["owned"]:
                st.button("Comprado", key=f"owned_{item['id']}", disabled=True)
            else:
                if st.button(f"Comprar", key=f"buy_{item['id']}"):
                    if st.session_state["coins"] >= item["price"]:
                        st.session_state["coins"] -= item["price"]
                        st.session_state["owned"].append(item["id"])
                        st.success(f"Compraste {item['label']} ✅")
                    else:
                        st.error("No tienes suficientes coins.")

    st.write("---")
    st.markdown("<strong>⚙️ Estado</strong>", unsafe_allow_html=True)
    st.markdown(f"<div class='muted'>Nombre:</div> {st.session_state['name'] or '(sin nombre)'}", unsafe_allow_html=True)
    st.markdown(f"<div class='muted'>Avatar:</div> <span style='font-size:20px'>{st.session_state['avatar']}</span>", unsafe_allow_html=True)
    st.markdown(f"<div class='muted'>Nivel:</div> {st.session_state['level']}", unsafe_allow_html=True)
    st.markdown(f"<div class='muted'>Coins:</div> {st.session_state['coins']}", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Submission area ----------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### ✅ Enviar todo (registro confidencial)")
st.markdown("<div class='muted'>Cuando termines todas las preguntas, pulsa ENVIAR. Tus respuestas se guardan para evaluación interna.</div>", unsafe_allow_html=True)
if st.button("Enviar todo"):
    if not st.session_state["name"]:
        st.warning("Antes de enviar, completa tus datos con '📋 Completar mis datos'.")
    else:
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "name": st.session_state["name"],
            "dni": st.session_state["dni"],
            "cel": st.session_state["cel"],
            "email": st.session_state["email"],
            "exp": st.session_state["exp"],
            "edu": st.session_state["edu"],
            "avatar": st.session_state["avatar"],
            "owned": ",".join(st.session_state["owned"]),
            "coins": st.session_state["coins"],
            "xp": st.session_state["xp"],
            "level": st.session_state["level"],
            "answers": st.session_state["answers"],
        }
        st.session_state["submissions"].append(record)
        st.success("Tu intento ha sido registrado. Gracias 🎉")
        # show final avatar + message
        st.markdown("<div style='margin-top:12px;'><strong>Tu avatar final:</strong></div>", unsafe_allow_html=True)
        badges = " ".join([acc["emoji"] for acc in ACCESSORIES if acc["id"] in st.session_state["owned"]])
        st.markdown(f"<div class='center' style='font-size:80px'>{st.session_state['avatar']}</div>", unsafe_allow_html=True)
        if badges:
            st.markdown(f"<div class='center' style='font-size:24px'>{badges}</div>", unsafe_allow_html=True)
        st.success("Tu avatar dice: Gracias, nos vemos pronto 😊")
        # reset index to end
        st.session_state["index"] = TOTAL - 1

st.markdown('</div>', unsafe_allow_html=True)

# ---------- Admin download panel (protected) ----------
st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
st.markdown('<div class="muted">Si eres admin y quieres descargar los registros, ingresa la clave aqui:</div>', unsafe_allow_html=True)
admin_key = st.text_input("Clave admin (solo descarga)", type="password", key="admin_key_input")
if admin_key:
    if ADMIN_SECRET and admin_key == ADMIN_SECRET:
        st.success("Acceso admin verificado.")
        if st.session_state["submissions"]:
            df = pd.DataFrame(st.session_state["submissions"])
            st.markdown(csv_download_link(df, filename="submissions.csv"), unsafe_allow_html=True)
            st.markdown(f"Intentos registrados: {len(df)}")
        else:
            st.info("No hay intentos todavía.")
    else:
        st.error("Clave incorrecta.")

st.markdown('<div class="footer-small">Nota: en este prototipo los datos se almacenan solo en memoria de la app. Para producción conecta Google Sheets o una base de datos para persistencia.</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
