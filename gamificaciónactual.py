# app.py
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io, csv, base64, textwrap, random
from datetime import datetime
import pandas as pd
import requests
import os

# ---------- Config ----------
st.set_page_config(page_title="Gamificación — Selección de Tutores", layout="wide")
st.markdown("""
<style>
/* Minimal, card-like UI */
.app-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 18px;
  box-shadow: 0 6px 20px rgba(15,23,42,0.06);
}
.header-title { font-size: 28px; font-weight:700; }
.small-muted { color: #6b7280; font-size:13px; }
.progress-avatar { display:flex; align-items:center; gap:12px; }
.center { text-align:center; }
.shop-item { border-radius:8px; padding:10px; border:1px solid #eee; }
</style>
""", unsafe_allow_html=True)

# ---------- Utilities ----------
def download_csv_string(csv_string, filename="resultados.csv"):
    b64 = base64.b64encode(csv_string.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Descargar CSV</a>'
    return href

def fetch_image(url, size=None):
    try:
        r = requests.get(url, timeout=5)
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        if size:
            img = img.resize(size, Image.NEAREST)
        return img
    except:
        return None

# ---------- Admin auth ----------
# Read secret from Streamlit secrets or environment
ADMIN_PASS = None
try:
    ADMIN_PASS = st.secrets.get("ADMIN_PASS", None)
except Exception:
    ADMIN_PASS = os.getenv("ADMIN_PASS", None)

st.sidebar.markdown("### 🔧 Admin (opcional)")
admin_try = st.sidebar.text_input("Clave admin para editar/descargar:", type="password")
is_admin = admin_try and ADMIN_PASS and admin_try == ADMIN_PASS
if is_admin:
    st.sidebar.success("Autenticado como admin ✅")
elif admin_try:
    st.sidebar.error("Clave incorrecta ❌")

# ---------- Avatares (DiceBear pixel-art) ----------
AVATAR_SEEDS = [
    "hawk","luna","milo","nova","zephyr","pixelkid","aurora","tiger","sable","echo"
]
AVATAR_URLS = {s: f"https://avatars.dicebear.com/api/pixel-art/{s}.png?size=128" for s in AVATAR_SEEDS}
ACCESSORIES = [
    {"id":"gafas","label":"🕶️ Gafas","price":30},
    {"id":"gorra","label":"🧢 Gorra","price":20},
    {"id":"libro","label":"📚 Libro","price":40},
    {"id":"estrella","label":"⭐ Medalla","price":60}
]

# ---------- Default questions (editable) ----------
default_questions = [
    {"id":"q1","type":"case","title":"Caso 1","prompt":"Un estudiante no alcanza el objetivo de la sesión. ¿Qué harías tú como tutor?","points":10},
    {"id":"q2","type":"mcq","title":"Mini-Quiz: Estrategia","prompt":"¿Cuál estrategia priorizas para explicar un concepto abstracto?","options":["Teoría larga","Ejemplos y analogías","Más tarea"],"points":10},
    {"id":"q3","type":"open","title":"Situación abierta","prompt":"Describe cómo motivarías a un grupo con baja asistencia.","points":15},
    {"id":"q4","type":"puzzle","title":"Puzzle","prompt":"Ordena la planificación: A) Evaluación inicial, B) Actividad práctica, C) Objetivos claros","correct_order":["C","A","B"],"points":10}
]

if "questions" not in st.session_state:
    st.session_state["questions"] = default_questions.copy()

# ---------- Storage for submissions (in-memory for this prototype) ----------
if "submissions" not in st.session_state:
    st.session_state["submissions"] = []

# ---------- Player/session state ----------
if "current_index" not in st.session_state:
    st.session_state["current_index"] = 0
if "answers" not in st.session_state:
    st.session_state["answers"] = [""] * len(st.session_state["questions"])
if "coins" not in st.session_state:
    st.session_state["coins"] = 50  # starting coins for demo
if "xp" not in st.session_state:
    st.session_state["xp"] = 0
if "level" not in st.session_state:
    st.session_state["level"] = 1
if "owned" not in st.session_state:
    st.session_state["owned"] = []  # accessory ids
if "avatar_choice" not in st.session_state:
    st.session_state["avatar_choice"] = AVATAR_SEEDS[0]
if "name" not in st.session_state:
    st.session_state["name"] = ""

# ---------- Header UI ----------
left, right = st.columns([3,1])
with left:
    st.markdown("<div class='app-card'>", unsafe_allow_html=True)
    st.markdown("<div class='header-title'>🎮 Gamificación — Selección de Tutores</div>", unsafe_allow_html=True)
    st.markdown("<div class='small-muted'>Prototipo interactivo. Responde libremente; las respuestas no se muestran como 'correctas' al instante.</div>", unsafe_allow_html=True)
with right:
    # Show avatar + coins + level
    avatar_url = AVATAR_URLS.get(st.session_state["avatar_choice"])
    if avatar_url:
        img = fetch_image(avatar_url, size=(96,96))
        if img:
            st.image(img)
    st.markdown(f"**Nivel**: {st.session_state['level']}  \n**XP**: {st.session_state['xp']}  \n**Coins**: {st.session_state['coins']}")

st.markdown("</div>", unsafe_allow_html=True)

st.write("")  # spacing

# ---------- Main interactive card ----------
col_main, col_side = st.columns([3,1])
with col_main:
    st.markdown("<div class='app-card'>", unsafe_allow_html=True)
    st.header("Misión: Demuestra tu potencial como tutor")
    st.markdown("Avanza pregunta a pregunta. Ganas **XP** por participar y **Coins** por completar niveles. Con las Coins podrás personalizar tu avatar en la Tienda.")
    st.write("---")

    # Progress / level bar
    total_q = len(st.session_state["questions"])
    progress = int((st.session_state["current_index"] / max(1,total_q)) * 100)
    st.progress(progress)
    st.markdown(f"Pregunta {st.session_state['current_index']+1} de {total_q}")

    q = st.session_state["questions"][st.session_state["current_index"]]
    st.subheader(f"{q.get('title','Pregunta')}")
    st.markdown(f"**{q.get('prompt','')}**")

    # Dynamic area for question types — no immediate correctness feedback
    if q.get("type") == "mcq":
        opts = q.get("options", [])
        prev = st.session_state["answers"][st.session_state["current_index"]]
        sel = st.radio("Elige una opción:", opts, index= opts.index(prev) if prev in opts else 0)
        st.session_state["answers"][st.session_state["current_index"]] = sel

    elif q.get("type") == "case" or q.get("type") == "open":
        prev = st.session_state["answers"][st.session_state["current_index"]]
        txt = st.text_area("Tu respuesta (escribe con claridad):", value=prev, height=180)
        st.session_state["answers"][st.session_state["current_index"]] = txt

    elif q.get("type") == "puzzle":
        prev = st.session_state["answers"][st.session_state["current_index"]]
        order = st.text_input("Ingresa el orden (ej: C,A,B):", value=prev)
        st.session_state["answers"][st.session_state["current_index"]] = order

    # Optional hint / motivation (avatar gives short encouragement)
    hints = [
        "Tu avatar cree en ti: respira hondo y responde con calma.",
        "Recuerda: explicar con ejemplos facilita el aprendizaje.",
        "Enfócate en la estrategia: ¿cómo guías al estudiante paso a paso?"
    ]
    st.info(random.choice(hints))

    # Navigation buttons (no immediate judgement)
    nav_col1, nav_col2, nav_col3 = st.columns(3)
    with nav_col1:
        if st.button("← Anterior") and st.session_state["current_index"] > 0:
            st.session_state["current_index"] -= 1
    with nav_col2:
        if st.button("Guardar y siguiente →"):
            # reward small coins for progressing
            st.session_state["coins"] += 5
            st.session_state["xp"] += 10
            # level up logic
            if st.session_state["xp"] >= st.session_state["level"] * 100:
                st.session_state["level"] += 1
                st.success(f"¡Subiste al nivel {st.session_state['level']}! +50 coins")
                st.session_state["coins"] += 50
            if st.session_state["current_index"] < total_q - 1:
                st.session_state["current_index"] += 1
            else:
                st.success("Has llegado al final. Pulsa Enviar para registrar tus respuestas.")
    with nav_col3:
        if st.button("🚩 Marcar para revisar después"):
            st.session_state.setdefault("flagged", []).append(q.get("id"))

    st.markdown("</div>", unsafe_allow_html=True)

with col_side:
    st.markdown("<div class='app-card'>", unsafe_allow_html=True)
    st.subheader("🎯 Estado del jugador")
    st.markdown(f"**Nombre:** {st.session_state.get('name','(sin nombre)')}")
    st.markdown(f"**Avatar:** {st.session_state.get('avatar_choice')}")
    st.markdown(f"**Level:** {st.session_state['level']}  •  **XP:** {st.session_state['xp']}")
    st.markdown(f"**Coins:** {st.session_state['coins']}")

    st.write("---")
    st.subheader("👕 Tienda de accesorios")
    st.markdown("Compra accesorios para tu avatar con las Coins ganadas.")
    for item in ACCESSORIES:
        col_a, col_b = st.columns([2,1])
        with col_a:
            st.markdown(f"**{item['label']}** — {item['price']} coins")
        with col_b:
            if item["id"] in st.session_state["owned"]:
                st.button("Poseído", key=f"owned_{item['id']}", disabled=True)
            else:
                if st.button("Comprar", key=f"buy_{item['id']}"):
                    if st.session_state["coins"] >= item["price"]:
                        st.session_state["coins"] -= item["price"]
                        st.session_state["owned"].append(item["id"])
                        st.success(f"Compraste {item['label']} ✅")
                    else:
                        st.error("No tienes suficientes Coins.")

    st.write("---")
    st.subheader("🖼 Elegir avatar")
    cols = st.columns(3)
    for i, seed in enumerate(AVATAR_SEEDS):
        url = AVATAR_URLS[seed]
        try:
            img = fetch_image(url, size=(72,72))
            if cols[i % 3].button(seed, key=f"choose_{seed}"):
                st.session_state["avatar_choice"] = seed
                st.success(f"Avatar seleccionado: {seed}")
            cols[i % 3].image(img)
        except:
            cols[i % 3].write(seed)

    st.write("---")
    st.subheader("💬 Mensajes motivadores")
    if st.button("Recibir mensaje"):
        motivational = [
            "Sigue así — la práctica mejora la enseñanza.",
            "Pequeños pasos: cada respuesta es aprendizaje.",
            "Buen trabajo: sé claro, paciente y empático."
        ]
        st.success(random.choice(motivational))

    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Submit / Save final results ----------
st.write("")  # spacing
st.markdown("<div class='app-card'>", unsafe_allow_html=True)
st.header("✅ Enviar respuestas (registro final)")
st.markdown("Cuando termines, envía tu intento. Tú decides cuándo está listo. Nosotros descargamos los resultados para evaluar.")

with st.expander("Vista previa de tus respuestas (tus respuestas NO se califican automáticamente)"):
    summary = []
    for i, qq in enumerate(st.session_state["questions"]):
        ans = st.session_state["answers"][i] if i < len(st.session_state["answers"]) else ""
        st.markdown(f"**{qq.get('title')}** — {ans if ans else '*Sin respuesta*'}")
        summary.append(ans)

col_send1, col_send2 = st.columns([1,1])
with col_send1:
    if st.button("Enviar mi intento (guardar registro)"):
        # Basic validation: require name and at least one answer
        if not st.session_state.get("name"):
            st.warning("Antes de enviar, escribe tu nombre en la barra lateral (campo Nombre).")
        else:
            now = datetime.now().isoformat()
            row = {
                "timestamp": now,
                "name": st.session_state.get("name"),
                "dni": st.session_state.get("dni",""),
                "avatar": st.session_state.get("avatar_choice",""),
                "coins": st.session_state["coins"],
                "level": st.session_state["level"],
                "xp": st.session_state["xp"],
                "answers": summary
            }
            # Append to in-memory submissions
            st.session_state["submissions"].append(row)
            st.success("Intento registrado. Gracias — pronto revisaremos las respuestas.")
with col_send2:
    if st.button("Reiniciar sesión (nuevo intento)"):
        # Reset player progress but keep questions
        st.session_state["current_index"] = 0
        st.session_state["answers"] = [""] * len(st.session_state["questions"])
        st.session_state["coins"] = 50
        st.session_state["xp"] = 0
        st.session_state["level"] = 1
        st.session_state["owned"] = []
        st.success("Listo para un nuevo intento.")

st.markdown("</div>", unsafe_allow_html=True)

# ---------- Admin panel (only visible with correct secret) ----------
if is_admin:
    st.markdown("---")
    st.header("🔐 Panel Admin")
    st.markdown("Desde aquí puedes editar preguntas, descargar todos los registros y resetear el historial.")

    # Edit questions inline
    for i, q in enumerate(st.session_state["questions"]):
        st.markdown(f"**Pregunta {i+1} ({q.get('type')})**")
        new_title = st.text_input(f"Título {i}", q.get("title",""), key=f"adm_title_{i}")
        new_prompt = st.text_input(f"Prompt {i}", q.get("prompt",""), key=f"adm_prompt_{i}")
        st.session_state["questions"][i]["title"] = new_title
        st.session_state["questions"][i]["prompt"] = new_prompt
        if q.get("type") == "mcq":
            opts = st.text_input(f"Opciones (separadas por ,) {i}", ",".join(q.get("options",[])), key=f"adm_opts_{i}")
            st.session_state["questions"][i]["options"] = [o.strip() for o in opts.split(",") if o.strip()]
        st.write("---")

    if st.button("Guardar cambios (admin)"):
        st.success("Cambios guardados.")

    # Download submissions as CSV
    if st.session_state["submissions"]:
        df = pd.DataFrame(st.session_state["submissions"])
        csv_txt = df.to_csv(index=False)
        st.markdown(download_csv_string(csv_txt, filename="submissions.csv"), unsafe_allow_html=True)
    else:
        st.info("No hay registros aún.")

    if st.button("Resetear historial (borrar registros)"):
        st.session_state["submissions"] = []
        st.success("Historial borrado.")

# ---------- Footer ----------
st.markdown("---")
st.caption("Prototipo gamificado para selección de tutores — versión demo. Para almacenar resultados permanentemente conecta Google Sheets o una base de datos.")
