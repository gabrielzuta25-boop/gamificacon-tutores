# app.py (corregido: sin errores NameError, sin st.button() dentro de forms,
# con guardado de borrador en data/drafts.json y envíos en data/submissions.json)

import streamlit as st
import pandas as pd
from datetime import datetime
import json, os, base64, random

# ---------- Config y CSS ----------
st.set_page_config(page_title="Gamificación — Selección de Tutores", layout="wide")
st.markdown("""
<style>
:root{--bg:#0b1220;--card:linear-gradient(180deg,#0f1724,#0c1320);--muted:#9aa7bf;
--accent:#7c3aed;--text:#e6eef8;--glass:rgba(255,255,255,0.02)}
html,body,[class*="css"]{background:var(--bg);color:var(--text)}
.container{max-width:1200px;margin:18px auto;font-family:Inter,system-ui,sans-serif}
.card{background:var(--card);padding:16px;border-radius:12px;box-shadow:0 8px 28px rgba(2,6,23,0.6);border:1px solid rgba(255,255,255,0.03)}
.title{font-size:22px;font-weight:700;color:var(--text);margin-bottom:6px}
.muted{color:var(--muted);font-size:13px;margin-bottom:10px}
.row{display:flex;gap:18px;align-items:flex-start}
.col-2{flex:2}.col-1{flex:1}
.avatar{font-size:56px;display:inline-block;padding:10px;border-radius:10px;background:var(--glass)}
.small{font-size:13px;color:var(--muted)}
.progress-steps{display:flex;gap:8px;align-items:center;margin-top:6px}
.step-dot{width:12px;height:12px;border-radius:6px;background:#1f2937;border:1px solid rgba(255,255,255,0.03)}
.step-dot.done{background:var(--accent);box-shadow:0 0 8px rgba(124,58,237,0.12)}
.question-area{min-height:160px;margin-top:8px}
.buttons{display:flex;gap:8px;margin-top:12px}
.btn{background:#111827;color:var(--text);padding:8px 12px;border-radius:8px;border:1px solid rgba(255,255,255,0.03)}
.shop-item{display:flex;justify-content:space-between;align-items:center;padding:8px;border-radius:8px;background:rgba(255,255,255,0.02);margin-bottom:8px}
.final-avatar{text-align:center}
.footer-note{color:var(--muted);font-size:12px;margin-top:8px}
</style>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
DATA_DIR = "data"
DRAFTS_FILE = os.path.join(DATA_DIR, "drafts.json")
SUBMISSIONS_FILE = os.path.join(DATA_DIR, "submissions.json")
os.makedirs(DATA_DIR, exist_ok=True)

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def csv_download_link_from_df(df, filename="submissions.csv"):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Descargar CSV</a>'

# ---------- Contenido: preguntas ----------
QUESTIONS = [
    {"id":"o1","type":"open","title":"Opinión 1","prompt":"¿Cuál crees que es la característica más importante en un tutor preuniversitario?"},
    {"id":"o2","type":"open","title":"Opinión 2","prompt":"Describe tu estilo de enseñanza en 2-3 frases."},
    {"id":"o3","type":"open","title":"Opinión 3","prompt":"¿Qué método usas para mantener la atención en clase?"},
    {"id":"o4","type":"open","title":"Opinión 4","prompt":"¿Cómo organizas una sesión para un tema difícil?"},
    {"id":"o5","type":"open","title":"Opinión 5","prompt":"¿Qué diferencias harías entre explicar a nivel escolar y preuniversitario?"},
    {"id":"c1","type":"case","title":"Caso 1","prompt":"Un alumno está frustrado y evita participar. Describe cómo lo abordarías paso a paso."},
    {"id":"c2","type":"case","title":"Caso 2","prompt":"El grupo es heterogéneo: algunos avanzan rápido, otros no. ¿Cómo organizarías la clase?"},
    {"id":"c3","type":"case","title":"Caso 3","prompt":"Hay un conflicto entre dos estudiantes que afecta la dinámica. ¿Qué medidas tomarías?"},
    {"id":"p1","type":"puzzle","title":"Puzzle 1","prompt":"Ordena: A) Actividad práctica, B) Objetivos claros, C) Evaluación inicial. (ej: B,C,A)","correct":["B","C","A"]},
    {"id":"p2","type":"puzzle","title":"Puzzle 2","prompt":"Ordena: A) Resumen, B) Retroalimentación, C) Tarea sugerida. (ej: A,B,C)","correct":["A","B","C"]},
]
TOTAL = len(QUESTIONS)

# ---------- Estado de la sesión (inicializar) ----------
ss = st.session_state
if "idx" not in ss:
    ss.idx = 0
if "answers" not in ss:
    ss.answers = [""] * TOTAL
if "name" not in ss:
    ss.name = ""
if "dni" not in ss:
    ss.dni = ""
if "cel" not in ss:
    ss.cel = ""
if "email" not in ss:
    ss.email = ""
if "exp" not in ss:
    ss.exp = ""
if "edu" not in ss:
    ss.edu = ""
if "avatar" not in ss:
    ss.avatar = "🛡️"
if "coins" not in ss:
    ss.coins = 50
if "xp" not in ss:
    ss.xp = 0
if "level" not in ss:
    ss.level = 1
if "owned" not in ss:
    ss.owned = []
if "submissions" not in ss:
    # try to load existing submissions file
    subs = load_json(SUBMISSIONS_FILE)
    if isinstance(subs, list):
        ss.submissions = subs
    else:
        ss.submissions = []

# accessories and avatars
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

# ---------- Intentar restaurar borrador por DNI si existe ----------
drafts = load_json(DRAFTS_FILE)
if ss.get("dni") and ss.dni in drafts:
    # restore only if session answers empty (to avoid overwriting current typing)
    if not any(ss.answers):
        record = drafts[ss.dni]
        ss.answers = record.get("answers", ss.answers)
        ss.name = record.get("name", ss.name)
        ss.email = record.get("email", ss.email)
        ss.cel = record.get("cel", ss.cel)
        ss.exp = record.get("exp", ss.exp)
        ss.edu = record.get("edu", ss.edu)
        ss.avatar = record.get("avatar", ss.avatar)
        ss.coins = record.get("coins", ss.coins)
        ss.xp = record.get("xp", ss.xp)
        ss.level = record.get("level", ss.level)

# ---------- Layout principal ----------
st.markdown('<div class="container">', unsafe_allow_html=True)

# TOP: data form (visible always) + small profile
top_left, top_right = st.columns([3,1], gap="large")
with top_left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="title">🎮 Gamificación — Selección de Tutores</div>', unsafe_allow_html=True)
    st.markdown('<div class="muted">Responde con sinceridad. Tus respuestas son confidenciales y se evaluarán internamente.</div>', unsafe_allow_html=True)

    # ---- Personal form (CORRECTO: st.form + st.form_submit_button) ----
    with st.form("personal_form_v2"):
        name_in = st.text_input("Nombres y apellidos", value=ss.name)
        dni_in = st.text_input("DNI", value=ss.dni)
        cel_in = st.text_input("Celular", value=ss.cel)
        email_in = st.text_input("Correo", value=ss.email)
        exp_in = st.text_area("Experiencia (breve)", value=ss.exp, height=80)
        edu_in = st.text_area("Educación recibida (breve)", value=ss.edu, height=80)

        # avatar selection as radio (válido dentro de form)
        avatar_options = [f'{a["emoji"]}  {a["label"]}' for a in AVATARS]
        default_avatar_idx = 0
        for i,a in enumerate(AVATARS):
            if a["emoji"] == ss.avatar:
                default_avatar_idx = i
        avatar_choice = st.radio("Selecciona un avatar", avatar_options, index=default_avatar_idx)

        save_personal = st.form_submit_button("Guardar datos")
    # if submitted, store in session_state AND save draft file
    if save_personal:
        ss.name = name_in
        ss.dni = dni_in
        ss.cel = cel_in
        ss.email = email_in
        ss.exp = exp_in
        ss.edu = edu_in
        ss.avatar = avatar_choice.split()[0]
        st.success("Datos guardados ✔️")

        # save draft to disk keyed by DNI (si hay DNI)
        if ss.dni:
            drafts = load_json(DRAFTS_FILE)
            drafts[ss.dni] = {
                "timestamp": datetime.utcnow().isoformat(),
                "name": ss.name,
                "dni": ss.dni,
                "cel": ss.cel,
                "email": ss.email,
                "exp": ss.exp,
                "edu": ss.edu,
                "avatar": ss.avatar,
                "answers": ss.answers,
                "coins": ss.coins,
                "xp": ss.xp,
                "level": ss.level
            }
            save_json(DRAFTS_FILE, drafts)

    st.markdown('</div>', unsafe_allow_html=True)

with top_right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"<div style='display:flex;align-items:center;gap:12px'><div class='avatar'>{ss.avatar}</div><div><strong style='font-size:16px'>{ss.name or '(Sin nombre)'}</strong><div class='small'>Nivel {ss.level} • XP {ss.xp}</div></div></div>", unsafe_allow_html=True)
    st.markdown("<div style='margin-top:12px'><strong>Coins</strong></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:20px'>{ss.coins} 💰</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Main question area + right shop/progress ----------
main_col, side_col = st.columns([3,1], gap="large")

with main_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    idx = ss.idx
    q = QUESTIONS[idx]
    st.markdown(f"### Paso {idx+1} de {TOTAL} — {q['title']}")
    st.markdown(f"**{q['prompt']}**")
    st.markdown('<div class="question-area">', unsafe_allow_html=True)

    # input
    if q["type"] in ("open","case"):
        val = st.text_area("Tu respuesta (confidencial):", value=ss.answers[idx], key=f"answer_{idx}", height=160)
        ss.answers[idx] = val
    elif q["type"] == "puzzle":
        val = st.text_input("Orden (ej: B,A,C):", value=ss.answers[idx], key=f"answer_{idx}")
        ss.answers[idx] = val

    st.markdown('</div>', unsafe_allow_html=True)

    # navigation buttons (NO buttons inside other forms)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("← Anterior"):
            if ss.idx > 0:
                ss.idx -= 1
    with c2:
        if st.button("Guardar y siguiente →"):
            # require name
            if not ss.name:
                st.warning("Guarda tus datos personales arriba antes de continuar.")
            else:
                # reward and autosave draft by DNI
                ss.coins += 7
                ss.xp += 12
                if ss.xp >= ss.level * 100:
                    ss.level += 1
                    ss.coins += 30
                    st.success(f"¡Subiste al nivel {ss.level}! +30 coins")
                # save draft
                if ss.dni:
                    drafts = load_json(DRAFTS_FILE)
                    drafts[ss.dni] = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "name": ss.name,
                        "dni": ss.dni,
                        "cel": ss.cel,
                        "email": ss.email,
                        "exp": ss.exp,
                        "edu": ss.edu,
                        "avatar": ss.avatar,
                        "answers": ss.answers,
                        "coins": ss.coins,
                        "xp": ss.xp,
                        "level": ss.level
                    }
                    save_json(DRAFTS_FILE, drafts)
                # advance
                if ss.idx < TOTAL - 1:
                    ss.idx += 1
                else:
                    st.success("Has llegado al final. Pulsa ENVIAR todo cuando quieras.")
    with c3:
        if st.button("Reiniciar intento"):
            ss.idx = 0
            ss.answers = [""] * TOTAL
            ss.coins = 50
            ss.xp = 0
            ss.level = 1
            ss.owned = []
            st.success("Intento reiniciado.")

    st.markdown('</div>', unsafe_allow_html=True)

with side_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    # progress dots
    dots_html = "<div class='progress-steps'>"
    for i in range(TOTAL):
        cls = "step-dot done" if i <= ss.idx else "step-dot"
        dots_html += f"<div class='{cls}' title='Paso {i+1}'></div>"
    dots_html += "</div>"
    st.markdown(dots_html, unsafe_allow_html=True)
    st.markdown(f"<div class='small'>Paso {ss.idx+1} de {TOTAL}</div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<strong>🛍️ Tienda</strong>", unsafe_allow_html=True)
    st.markdown("<div class='small'>Personaliza tu avatar con accesorios (emoji).</div>", unsafe_allow_html=True)
    for item in ACCESSORIES:
        cols = st.columns([2,1])
        with cols[0]:
            st.markdown(f"{item['emoji']} <strong>{item['label']}</strong> <span class='small'>- {item['price']} coins</span>", unsafe_allow_html=True)
        with cols[1]:
            if item["id"] in ss.owned:
                st.button("Comprado", key=f"owned_{item['id']}", disabled=True)
            else:
                if st.button("Comprar", key=f"buy_{item['id']}"):
                    if ss.coins >= item['price']:
                        ss.coins -= item['price']
                        ss.owned.append(item['id'])
                        st.success(f"Compraste {item['label']} ✅")
                    else:
                        st.error("No tienes suficientes coins.")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Enviar final ----------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### ✅ Enviar todo (registro confidencial)")
st.markdown('<div class="small">Cuando termines todas las preguntas, pulsa ENVIAR. Nosotros evaluamos internamente; tus respuestas no se muestran a otros usuarios.</div>', unsafe_allow_html=True)
if st.button("Enviar todo"):
    if not ss.name:
        st.warning("Por favor, completa tus datos personales arriba.")
    else:
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "name": ss.name,
            "dni": ss.dni,
            "cel": ss.cel,
            "email": ss.email,
            "exp": ss.exp,
            "edu": ss.edu,
            "avatar": ss.avatar,
            "owned": ",".join(ss.owned),
            "coins": ss.coins,
            "xp": ss.xp,
            "level": ss.level,
            "answers": ss.answers
        }
        # Append to submissions in session and save to disk
        ss.submissions.append(record)
        save_json(SUBMISSIONS_FILE, ss.submissions)
        # Remove draft for this DNI (if exists)
        drafts = load_json(DRAFTS_FILE)
        if ss.dni and ss.dni in drafts:
            drafts.pop(ss.dni)
            save_json(DRAFTS_FILE, drafts)
        st.success("Tu intento ha sido registrado. ¡Gracias! 🎉")
        # show final avatar + accessories
        badges = " ".join([a["emoji"] for a in ACCESSORIES if a["id"] in ss.owned])
        st.markdown(f"<div class='final-avatar'><div style='font-size:120px'>{ss.avatar}</div><div style='font-size:28px'>{badges}</div><div style='margin-top:8px;font-weight:600'>Gracias, nos vemos pronto 😊</div></div>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ---------- Admin download panel (protegido con secret) ----------
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
        if ss.submissions:
            df = pd.DataFrame(ss.submissions)
            st.markdown(csv_download_link_from_df(df, "submissions.csv"), unsafe_allow_html=True)
            st.markdown(f"Intentos registrados: {len(df)}")
        else:
            st.info("No hay intentos registrados aún.")
    else:
        st.error("Clave incorrecta.")

st.markdown('<div class="footer-note">Nota: guardado de borrador se hace en data/drafts.json y envíos en data/submissions.json. En Streamlit Cloud el filesystem puede ser efímero; para persistencia real usa Google Sheets o una DB. Puedo integrar eso si quieres.</div>', unsafe_allow_html=True)

# End container
st.markdown('</div>', unsafe_allow_html=True)

