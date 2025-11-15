# app.py
# Prototipo GAMIFICACIÓN — Selección de Tutores (versión profesional, sin sidebar)
import streamlit as st
from PIL import Image, ImageOps
import io, csv, base64, random, textwrap
from datetime import datetime
import pandas as pd
import requests
import os

# ---------- Config ----------
st.set_page_config(page_title="Gamificación — Selección de Tutores", layout="wide")
st.markdown(
    """
    <style>
    /* Page background + card style */
    body { background: #f6f8fb; }
    .card { background: #fff; border-radius: 14px; padding: 18px; box-shadow: 0 10px 30px rgba(15,23,42,0.06); }
    .title { font-size: 28px; font-weight:700; margin-bottom: 6px; }
    .muted { color: #6b7280; font-size:13px; }
    .avatar-float { animation: float 3s ease-in-out infinite; display:block; margin:auto; }
    @keyframes float {
      0% { transform: translateY(0px); }
      50% { transform: translateY(-6px); }
      100% { transform: translateY(0px); }
    }
    .progress-steps { display:flex; gap:12px; align-items:center; justify-content:flex-start; }
    .step-dot { width:18px; height:18px; border-radius:9px; background:#e6e9ef; display:inline-block; }
    .step-dot.done { background:#4f46e5; }
    .step-label { font-size:12px; color:#6b7280; }
    .question-area { min-height:260px; }
    .shop-item { border-radius:10px; padding:10px; background:#fbfbff; text-align:center; }
    .final-avatar { text-align:center; }
    .footer-admin { font-size:12px; color:#9ca3af; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Helpers ----------
def fetch_image(url, size=None, as_rgba=False):
    """Fetch image from URL and return PIL image (or None)."""
    try:
        r = requests.get(url, timeout=6)
        img = Image.open(io.BytesIO(r.content))
        if size:
            img = img.resize(size, Image.NEAREST)
        if as_rgba:
            img = img.convert("RGBA")
        return img
    except Exception:
        return None

def compose_avatar(avatar_img, accessories):
    """Compose avatar base image with accessory images (list of urls or PILs)."""
    try:
        base = avatar_img.convert("RGBA")
        w, h = base.size
        canvas = Image.new("RGBA", base.size)
        canvas.paste(base, (0,0))
        # simple placement: top-right for glasses/hat, bottom-left for book, center for medal
        for acc in accessories:
            if isinstance(acc, Image.Image):
                aimg = acc.convert("RGBA")
            else:
                aimg = fetch_image(acc, size=(int(w*0.35), int(h*0.35)), as_rgba=True)
            if not aimg:
                continue
            # place according to simple heuristic by filename
            a_lower = getattr(acc, 'id', '') if hasattr(acc, 'id') else ""
            # try to place above head
            canvas.paste(aimg, (int(w*0.55), int(h*0.02)), aimg)
        return canvas
    except Exception:
        return avatar_img

def csv_download_link_from_df(df, filename="submissions.csv"):
    csv_str = df.to_csv(index=False)
    b64 = base64.b64encode(csv_str.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Descargar CSV</a>'

# ---------- Assets (3 avatars + accessories + case images) ----------
# Avatars: use DiceBear pixel-art but with larger size, and add simple unique images for differentiation.
AVATAR_SEEDS = ["nova", "milo", "aurora"]
AVATAR_URLS = {s: f"https://avatars.dicebear.com/api/pixel-art/{s}.png?size=256" for s in AVATAR_SEEDS}

# Accessories: small PNG URLs or emoji placeholders (we'll render as small colored badges)
ACCESSORIES_META = [
    {"id":"gafas","label":"Gafas", "price":30, "img": None},
    {"id":"gorra","label":"Gorra", "price":20, "img": None},
    {"id":"libro","label":"Libro", "price":40, "img": None},
]

# Case images for 3 case questions (royalty-free placeholders)
CASE_IMAGES = [
    "https://images.unsplash.com/photo-1584697964409-9e6b6f0b3c86?w=800&q=60&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1586281380399-2bcd8a2f2b8b?w=800&q=60&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1523580846011-d3a5bc25702b?w=800&q=60&auto=format&fit=crop",
]

# ---------- Questionnaire content ----------
# 5 opinion (open), 3 cases (with image), 2 puzzles (order)
QUESTIONS = [
    # 5 opinion
    {"id":"o1","type":"open","title":"Opinión 1","prompt":"¿Cuál crees que es la característica más importante en un tutor preuniversitario?"},
    {"id":"o2","type":"open","title":"Opinión 2","prompt":"Describe tu estilo de enseñanza en 2-3 frases."},
    {"id":"o3","type":"open","title":"Opinión 3","prompt":"¿Qué método usas para mantener la atención en clase?"},
    {"id":"o4","type":"open","title":"Opinión 4","prompt":"¿Cómo organizas una sesión para un tema difícil?"},
    {"id":"o5","type":"open","title":"Opinión 5","prompt":"¿Qué diferencias harías entre explicar a nivel escolar y preuniversitario?"},
    # 3 cases (with images)
    {"id":"c1","type":"case","title":"Caso 1","prompt":"Revisa la imagen: Un estudiante distraído. ¿Cómo lo abordarías?","image": CASE_IMAGES[0]},
    {"id":"c2","type":"case","title":"Caso 2","prompt":"Revisa la imagen: Estudiante con dudas sobre un ejercicio. ¿Qué haces?", "image": CASE_IMAGES[1]},
    {"id":"c3","type":"case","title":"Caso 3","prompt":"Revisa la imagen: Grupo con baja motivación. ¿Qué plan propones?", "image": CASE_IMAGES[2]},
    # 2 puzzles (order)
    {"id":"p1","type":"puzzle","title":"Puzzle 1","prompt":"Ordena estas acciones para preparar una clase: (A) Practica, (B) Objetivos claros, (C) Evaluación inicial.", "correct":["B","C","A"]},
    {"id":"p2","type":"puzzle","title":"Puzzle 2","prompt":"Ordena para cerrar una sesión: (A) Resumen, (B) Retroalimentación, (C) Tarea sugerida.", "correct":["A","B","C"]},
]

TOTAL_STEPS = len(QUESTIONS)

# ---------- Session initialization ----------
if "step_index" not in st.session_state:
    st.session_state["step_index"] = 0
if "answers" not in st.session_state:
    st.session_state["answers"] = [""] * TOTAL_STEPS
if "coins" not in st.session_state:
    st.session_state["coins"] = 50
if "xp" not in st.session_state:
    st.session_state["xp"] = 0
if "level" not in st.session_state:
    st.session_state["level"] = 1
if "owned" not in st.session_state:
    st.session_state["owned"] = []
if "avatar" not in st.session_state:
    st.session_state["avatar"] = AVATAR_SEEDS[0]
if "name" not in st.session_state:
    st.session_state["name"] = ""
if "dni" not in st.session_state:
    st.session_state["dni"] = ""
if "celular" not in st.session_state:
    st.session_state["celular"] = ""
if "correo" not in st.session_state:
    st.session_state["correo"] = ""
if "experiencia" not in st.session_state:
    st.session_state["experiencia"] = ""
if "educacion" not in st.session_state:
    st.session_state["educacion"] = ""
if "submitted_records" not in st.session_state:
    st.session_state["submitted_records"] = []

# ---------- Top bar: Title and CTA to open modal for personal data ----------
container_top = st.container()
with container_top:
    col1, col2 = st.columns([3,1])
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="title">Gamificación — Selección de Tutores</div>', unsafe_allow_html=True)
        st.markdown('<div class="muted">Responde con sinceridad. Tus respuestas serán evaluadas internamente.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        # Button to open modal for personal data
        if st.button("📋 Completar mis datos"):
            # show modal/expander
            if hasattr(st, "modal"):
                modal = st.modal("Tus datos (confidencial)")
                with modal:
                    with st.form("form_personal"):
                        n = st.text_input("Nombres y apellidos", value=st.session_state.get("name",""))
                        dni_in = st.text_input("DNI", value=st.session_state.get("dni",""))
                        cel = st.text_input("Celular", value=st.session_state.get("celular",""))
                        mail = st.text_input("Correo", value=st.session_state.get("correo",""))
                        exp = st.text_area("Experiencia (breve)", value=st.session_state.get("experiencia",""), height=80)
                        edu = st.text_area("Educación recibida (breve)", value=st.session_state.get("educacion",""), height=80)
                        av_cols = st.columns(3)
                        st.markdown("**Elige un avatar**")
                        for i, seed in enumerate(AVATAR_SEEDS):
                            img = fetch_image(AVATAR_URLS[seed], size=(100,100))
                            if img:
                                with av_cols[i]:
                                    st.image(img, caption=f"Avatar {i+1}", use_column_width=False, output_format="PNG", clamp=False)
                                    if st.button(f"Elegir {i+1}", key=f"pick_{seed}"):
                                        st.session_state["avatar"] = seed
                        submitted = st.form_submit_button("Guardar y cerrar")
                        if submitted:
                            st.session_state["name"] = n
                            st.session_state["dni"] = dni_in
                            st.session_state["celular"] = cel
                            st.session_state["correo"] = mail
                            st.session_state["experiencia"] = exp
                            st.session_state["educacion"] = edu
                            st.experimental_rerun()
            else:
                with st.expander("Tus datos (confidencial)"):
                    with st.form("form_personal"):
                        n = st.text_input("Nombres y apellidos", value=st.session_state.get("name",""))
                        dni_in = st.text_input("DNI", value=st.session_state.get("dni",""))
                        cel = st.text_input("Celular", value=st.session_state.get("celular",""))
                        mail = st.text_input("Correo", value=st.session_state.get("correo",""))
                        exp = st.text_area("Experiencia (breve)", value=st.session_state.get("experiencia",""), height=80)
                        edu = st.text_area("Educación recibida (breve)", value=st.session_state.get("educacion",""), height=80)
                        av_cols = st.columns(3)
                        st.markdown("**Elige un avatar**")
                        for i, seed in enumerate(AVATAR_SEEDS):
                            img = fetch_image(AVATAR_URLS[seed], size=(100,100))
                            if img:
                                with av_cols[i]:
                                    st.image(img, caption=f"Avatar {i+1}", use_column_width=False, output_format="PNG", clamp=False)
                                    if st.button(f"Elegir {i+1}", key=f"pick2_{seed}"):
                                        st.session_state["avatar"] = seed
                        submitted = st.form_submit_button("Guardar y cerrar")
                        if submitted:
                            st.session_state["name"] = n
                            st.session_state["dni"] = dni_in
                            st.session_state["celular"] = cel
                            st.session_state["correo"] = mail
                            st.session_state["experiencia"] = exp
                            st.session_state["educacion"] = edu
                            st.experimental_rerun()

# ---------- Main layout: large central question area + right column for store/progress path ----------
main_col, side_col = st.columns([3,1])

with main_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    # show avatar and small message on left of question
    top_row = st.columns([1,4])
    with top_row[0]:
        av_img = fetch_image(AVATAR_URLS[st.session_state["avatar"]], size=(140,140))
        if av_img:
            st.image(av_img, use_column_width=False, output_format="PNG", caption="Tu avatar",
                     clamp=False, channels="RGBA")
    with top_row[1]:
        st.markdown(f"### {QUESTIONS[st.session_state['step_index']]['title']}")
        st.markdown(f"**{QUESTIONS[st.session_state['step_index']]['prompt']}**")
        # show case image if present
        if QUESTIONS[st.session_state['step_index']].get("image"):
            img_url = QUESTIONS[st.session_state['step_index']]["image"]
            img = fetch_image(img_url, size=(760,320))
            if img:
                st.image(img, use_column_width=True)

    st.write("")  # spacing
    # question input area
    q = QUESTIONS[st.session_state['step_index']]
    st.markdown('<div class="question-area">', unsafe_allow_html=True)
    idx = st.session_state['step_index']
    if q["type"] == "open" or q["type"] == "case":
        prev = st.session_state["answers"][idx]
        ans = st.text_area("Tu respuesta (confidencial):", value=prev, height=160, placeholder="Escribe tu respuesta...")
        st.session_state["answers"][idx] = ans
    elif q["type"] == "puzzle":
        prev = st.session_state["answers"][idx]
        hint = "Ingresa el orden usando letras separadas por comas. Ej: B,A,C"
        order = st.text_input(f"Orden (ej: B,A,C):", value=prev, placeholder=hint)
        st.session_state["answers"][idx] = order

    st.markdown('</div>', unsafe_allow_html=True)

    # Navigation & gamified buttons (no immediate judgement)
    nav1, nav2, nav3 = st.columns([1,1,1])
    with nav1:
        if st.button("← Anterior"):
            if st.session_state['step_index'] > 0:
                st.session_state['step_index'] -= 1
    with nav2:
        if st.button("Guardar y siguiente →"):
            # require at least name
            if not st.session_state.get("name"):
                st.warning("Primero completa tus datos (botón '📋 Completar mis datos').")
            else:
                # reward and progress
                st.session_state["coins"] += 8
                st.session_state["xp"] += 12
                # level up if xp threshold
                if st.session_state["xp"] >= st.session_state["level"] * 120:
                    st.session_state["level"] += 1
                    st.session_state["coins"] += 40
                    st.success(f"¡Subiste al nivel {st.session_state['level']}! Recibiste 40 coins.")
                if st.session_state['step_index'] < TOTAL_STEPS - 1:
                    st.session_state['step_index'] += 1
                else:
                    st.success("Has completado todas las preguntas. Pulsa 'Enviar todo' abajo cuando estés listo.")
    with nav3:
        if st.button("Marcar para revisar"):
            st.success("Marcado para revisión interna.")

    st.markdown("</div>", unsafe_allow_html=True)

with side_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    # Progress path visualization (small icons)
    st.markdown("### Progreso")
    step_cols = st.columns(TOTAL_STEPS if TOTAL_STEPS <= 10 else 10)
    progress_index = st.session_state['step_index']
    # render as row of small dots and miniature avatars on completed
    dots_html = "<div class='progress-steps'>"
    for i in range(TOTAL_STEPS):
        cls = "step-dot done" if i <= progress_index else "step-dot"
        dots_html += f"<div title='Paso {i+1}' class='{cls}'></div>"
    dots_html += "</div>"
    st.markdown(dots_html, unsafe_allow_html=True)
    st.markdown(f"Paso {progress_index+1} de {TOTAL_STEPS}")

    st.write("---")
    st.markdown("### Estado")
    st.markdown(f"**Nombre:** {st.session_state.get('name','(no ingresado)')}")
    st.markdown(f"**Nivel:** {st.session_state['level']}  •  **XP:** {st.session_state['xp']}")
    st.markdown(f"**Coins:** {st.session_state['coins']}")

    st.write("---")
    st.markdown("### Tienda (personalización)")
    for item in ACCESSORIES_META:
        cols_t = st.columns([2,1])
        with cols_t[0]:
            st.markdown(f"**{item['label']}**")
            st.markdown(f"<span class='muted'>Precio: {item['price']} coins</span>", unsafe_allow_html=True)
        with cols_t[1]:
            if item["id"] in st.session_state["owned"]:
                st.button("Comprado", key=f"owned_{item['id']}", disabled=True)
            else:
                if st.button(f"Comprar {item['label']}", key=f"buy_{item['id']}"):
                    if st.session_state["coins"] >= item['price']:
                        st.session_state["coins"] -= item['price']
                        st.session_state["owned"].append(item['id'])
                        st.success(f"Compraste {item['label']}.")
                    else:
                        st.error("No tienes suficientes coins.")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Final submission area ----------
st.write("")  # spacing
st.markdown('<div class="card">', unsafe_allow_html=True)
st.header("Enviar todo (registro confidencial)")
st.markdown("Cuando hayas terminado todas las preguntas, pulsa ENVIAR para registrar tu intento. Tus respuestas se guardan y ustedes (equipo) las descargarán para evaluar internamente.")

if st.button("Enviar todo"):
    if not st.session_state.get("name"):
        st.warning("Antes de enviar, completa tus datos personales (botón '📋 Completar mis datos').")
    else:
        # Build record
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "name": st.session_state.get("name"),
            "dni": st.session_state.get("dni"),
            "celular": st.session_state.get("celular"),
            "correo": st.session_state.get("correo"),
            "experiencia": st.session_state.get("experiencia"),
            "educacion": st.session_state.get("educacion"),
            "avatar": st.session_state.get("avatar"),
            "owned": ",".join(st.session_state.get("owned", [])),
            "coins": st.session_state.get("coins"),
            "xp": st.session_state.get("xp"),
            "level": st.session_state.get("level"),
            "answers": st.session_state.get("answers"),
        }
        st.session_state["submitted_records"].append(record)
        st.success("Gracias — tu intento ha sido registrado. Volverás a la pantalla final.")
        st.balloons()
        # move to final summary view
        st.session_state["step_index"] = TOTAL_STEPS - 1  # push to end
        st.experimental_rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ---------- Final screen: show avatar composition & farewell if submitted ----------
if st.session_state["submitted_records"]:
    st.write("")  # spacing
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Resultado final — tu avatar")
    # Compose avatar with simple accessory overlay (we use emoji badges as text)
    base_img = fetch_image(AVATAR_URLS[st.session_state["avatar"]], size=(220,220), as_rgba=True)
    # Build a simple composite visually: for prototype we'll show base and list accessories as badges
    colf1, colf2 = st.columns([1,2])
    with colf1:
        if base_img:
            st.image(base_img, width=220)
    with colf2:
        st.markdown("**Accesorios comprados:**")
        if st.session_state["owned"]:
            for oid in st.session_state["owned"]:
                label = next((x["label"] for x in ACCESSORIES_META if x["id"]==oid), oid)
                st.markdown(f"- {label}")
        else:
            st.markdown("_No compraste accesorios._")
        st.markdown("")
        st.markdown("**Mensaje del avatar:**")
        st.success("¡Gracias por participar! Nos vemos pronto 😊")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Admin download (hidden in footer, unlocking requires secret) ----------
st.write("")  # spacing
col_a, col_b, col_c = st.columns([1,2,1])
with col_b:
    st.markdown("<div class='muted center'>Si eres administrador y deseas descargar los intentos, ingresa tu clave abajo.</div>", unsafe_allow_html=True)
    admin_key = st.text_input("Clave admin (solo para descarga)", type="password", key="admin_download_key")
    if admin_key:
        # check against secret if present
        ADMIN_SECRET = None
        try:
            ADMIN_SECRET = st.secrets.get("ADMIN_PASS", None)
        except Exception:
            ADMIN_SECRET = os.getenv("ADMIN_PASS", None)
        if ADMIN_SECRET and admin_key == ADMIN_SECRET:
            st.success("Acceso admin verificado. Descargas disponibles.")
            df = pd.DataFrame(st.session_state["submitted_records"])
            if not df.empty:
                st.markdown(csv_download_link_from_df(df, filename="submissions.csv"), unsafe_allow_html=True)
                st.markdown("Número de intentos: " + str(len(df)))
            else:
                st.info("No hay intentos registrados aún.")
        else:
            if admin_key:
                st.error("Clave admin incorrecta.")

# footer small note
st.markdown("<div class='muted footer-admin'>Los datos recogidos se almacenan en la app para este prototipo; para producción conecta Google Sheets o una DB. No se muestran las respuestas a otros usuarios.</div>", unsafe_allow_html=True)

