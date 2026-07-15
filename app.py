"""
Auvix Industrial AI Assistant - Interfaz Streamlit
Asistente inteligente para consultas técnicas, telemetría, financiero y documentación.

Sistema visual: cada rama del grafo (rag / financiero / telemetria / schema_api)
tiene un color propio que se propaga por badge, borde de burbuja y tarjeta de
módulo activa en el sidebar -- la interfaz refleja el enrutamiento real del agente.
"""

import streamlit as st
import uuid
import time
import datetime
import sys
import os

# Asegurar que src/ esté en el path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.graph.build import crear_app
from src.graph.state import Ruta

# ---------- CONFIGURACIÓN DE PÁGINA ----------
st.set_page_config(
    page_title="Auvix Industrial AI",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- CONSTANTES DE PERSONALIZACIÓN ----------
AVATAR_USER = "🧑‍🔧"
AVATAR_ASSISTANT = "🛰️"

# Color propio por rama -- se usa en badge, borde de burbuja y sidebar
RUTA_META = {
    "rag":         {"color": "#3B82C4", "label": "Documentación", "icon": "📚"},
    "financiero":  {"color": "#1F9E6B", "label": "Financiero",    "icon": "💰"},
    "telemetria":  {"color": "#FF6B35", "label": "Telemetría",    "icon": "📡"},
    "schema_api":  {"color": "#7C5CBF", "label": "Esquema API",   "icon": "🔌"},
    "desconocida": {"color": "#8A94A6", "label": "Sin clasificar", "icon": "❔"},
}

def meta_ruta(ruta: str) -> dict:
    return RUTA_META.get(ruta, RUTA_META["desconocida"])

# Mensaje de bienvenida -- se muestra una sola vez, al iniciar una sesión
# nueva (no se envía al grafo, es puramente informativo para la UI).
MENSAJE_BIENVENIDA = """### 👷 ¡Hola! Soy el Asistente Industrial de Auvix

Estoy diseñado para ayudarte con consultas sobre **telemetría IoT**, **finanzas**, **esquemas de API** y **documentación técnica**.
A continuación te muestro el tipo de preguntas que puedes hacerme en cada área:

---

#### 📡 **Telemetría de nodos IoT**
- ¿Cuál es el estado actual del **NODO-L4-01**?
- ¿Qué nodos tienen o han tenido **alertas**?
- Dame el **promedio de temperatura** del NODO-L4-02.
- ¿Cuál fue la **lectura más alta de consumo**?
- **Resumen general** de todos los nodos.

#### 💰 **Financiero**
- ¿Cuánto ha gastado el departamento de **Infraestructura**?
- ¿Cuál fue el **gasto total en Hardware**?
- Muéstrame las **transacciones pendientes**.
- Dame un **resumen financiero** completo.
- ¿Cuál fue la **compra más cara**?

#### 🔌 **Esquema de API (sensores IoT)**
- ¿Qué **endpoints** tiene la API de telemetría?
- ¿Qué **campos** necesito enviar al endpoint de **motores**?
- ¿Cuáles son los **campos obligatorios** del endpoint de environment?
- Dame un **ejemplo de payload** para el endpoint de motores.
- ¿Qué significa un código **503** en el endpoint de motores?
- ¿En qué endpoints aparece el campo **'rpm'**?

#### 📚 **Documentación técnica (RAG)**
- Cualquier pregunta sobre manuales, protocolos, o especificaciones de equipos industriales.
  *Ejemplo: ¿Cómo se calcula la ganancia crítica en el método de Ziegler‑Nichols?*

---

✏️ **Escribe tu consulta en lenguaje natural** y yo me encargaré de derivarla al módulo adecuado.
Recuerda que puedo mantener el contexto de la conversación, así que puedes hacer preguntas de seguimiento."""

def render_bienvenida(contenedor):
    """Bloque de bienvenida: mismo estilo de burbuja que el asistente,
    pero con acento navy en vez de color de rama (no es una respuesta
    del grafo, es un mensaje puramente informativo de la UI)."""
    contenedor.markdown(
        f'<div class="chat-bubble-assistant" style="--ruta-color:#0B1F3B;">\n\n{MENSAJE_BIENVENIDA}\n\n</div>',
        unsafe_allow_html=True
    )

# ---------- ESTILOS ----------
def aplicar_estilo_industrial():
    st.markdown("""
    <style>
        /* ===== FUENTES ===== */
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

        :root {
            --navy-900: #0B1F3B;
            --navy-700: #16324F;
            --steel-100: #F4F6F8;
            --orange-500: #FF6B35;
            --signal-green: #1FCB8C;
            --text-900: #1A2332;
            --text-500: #5C6B7A;
            --border: #DDE3E9;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: var(--text-900);
        }

        .stApp {
            background-color: var(--steel-100);
            background-image:
                linear-gradient(rgba(11,31,59,0.025) 1px, transparent 1px),
                linear-gradient(90deg, rgba(11,31,59,0.025) 1px, transparent 1px);
            background-size: 28px 28px;
        }

        h1, h2, h3, .space-grotesk {
            font-family: 'Space Grotesk', sans-serif;
        }

        .mono {
            font-family: 'IBM Plex Mono', monospace;
        }

        /* ===== BARRA LATERAL — PANEL DE CONTROL ===== */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--navy-900) 0%, var(--navy-700) 100%);
            border-right: 1px solid rgba(255,255,255,0.08);
        }
        [data-testid="stSidebar"] * {
            color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] .stButton>button {
            background-color: var(--orange-500);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            font-family: 'Space Grotesk', sans-serif;
            transition: all 0.2s;
        }
        [data-testid="stSidebar"] .stButton>button:hover {
            background-color: #E55A26;
            box-shadow: 0 4px 14px rgba(255,107,53,0.35);
        }
        [data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,0.12);
        }

        .sidebar-wordmark {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 4px 0 2px 0;
        }
        .sidebar-wordmark .mark {
            width: 34px; height: 34px;
            background: var(--orange-500);
            border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            font-size: 1.1rem;
            color: var(--navy-900);
        }
        .sidebar-wordmark .name {
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            font-size: 1.15rem;
            letter-spacing: 0.5px;
        }
        .sidebar-subtitle {
            font-size: 0.7rem;
            letter-spacing: 1.2px;
            color: rgba(255,255,255,0.55) !important;
            text-transform: uppercase;
            margin-top: -6px;
        }

        .session-id {
            font-size: 0.78rem;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 6px;
            padding: 6px 10px;
            display: inline-block;
        }

        /* Tarjetas de módulo (rama) en el sidebar */
        .modulo-card {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 10px;
            border-radius: 8px;
            margin-bottom: 6px;
            border: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.03);
            transition: all 0.2s;
        }
        .modulo-card.activo {
            border-color: var(--modulo-color, var(--orange-500));
            background: color-mix(in srgb, var(--modulo-color, var(--orange-500)) 18%, transparent);
        }
        .modulo-dot {
            width: 8px; height: 8px;
            border-radius: 50%;
            background: var(--modulo-color, var(--signal-green));
            box-shadow: 0 0 0 0 var(--modulo-color, var(--signal-green));
            animation: pulse 2s infinite;
            flex-shrink: 0;
        }
        @keyframes pulse {
            0%   { box-shadow: 0 0 0 0 color-mix(in srgb, var(--modulo-color, var(--signal-green)) 55%, transparent); }
            70%  { box-shadow: 0 0 0 6px transparent; }
            100% { box-shadow: 0 0 0 0 transparent; }
        }
        .modulo-label {
            font-size: 0.85rem;
            font-weight: 500;
        }

        /* ===== BARRA DE ESTADO SUPERIOR ===== */
        .status-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--navy-900);
            border-radius: 12px;
            padding: 14px 22px;
            margin-bottom: 22px;
            box-shadow: 0 4px 16px rgba(11,31,59,0.15);
        }
        .status-bar .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .status-bar .brand .mark {
            width: 38px; height: 38px;
            background: var(--orange-500);
            border-radius: 9px;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            color: var(--navy-900);
            font-size: 1.2rem;
        }
        .status-bar .brand .title {
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            font-size: 1.25rem;
            color: #FFFFFF;
            line-height: 1.1;
        }
        .status-bar .brand .subtitle {
            font-size: 0.7rem;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            color: rgba(255,255,255,0.55);
        }
        .status-bar .meta {
            display: flex;
            align-items: center;
            gap: 18px;
            color: rgba(255,255,255,0.85);
            font-size: 0.8rem;
        }
        .status-bar .meta .dot-online {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .status-bar .meta .dot-online::before {
            content: "";
            width: 8px; height: 8px;
            border-radius: 50%;
            background: var(--signal-green);
            box-shadow: 0 0 0 0 var(--signal-green);
            animation: pulse-green 2s infinite;
        }
        @keyframes pulse-green {
            0%   { box-shadow: 0 0 0 0 rgba(31,203,140,0.55); }
            70%  { box-shadow: 0 0 0 6px transparent; }
            100% { box-shadow: 0 0 0 0 transparent; }
        }

        /* ===== BURBUJAS DE CHAT ===== */
        .chat-bubble-user {
            background: linear-gradient(135deg, var(--navy-900), var(--navy-700));
            color: #FFFFFF;
            border-radius: 16px 16px 4px 16px;
            padding: 14px 18px;
            margin: 8px 0;
            box-shadow: 0 2px 10px rgba(11,31,59,0.15);
            font-size: 0.95rem;
            line-height: 1.55;
        }

        .chat-bubble-assistant {
            background: #FFFFFF;
            color: var(--text-900);
            border: 1px solid var(--border);
            border-left: 4px solid var(--ruta-color, var(--orange-500));
            border-radius: 4px 14px 14px 14px;
            padding: 14px 18px;
            margin: 8px 0;
            box-shadow: 0 2px 10px rgba(11,31,59,0.06);
            font-size: 0.95rem;
            line-height: 1.55;
        }

        .chat-bubble-assistant table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-size: 0.88rem;
        }
        .chat-bubble-assistant th {
            background-color: var(--navy-900);
            color: white;
            padding: 8px 12px;
            text-align: left;
            font-weight: 600;
            font-size: 0.8rem;
            font-family: 'IBM Plex Mono', monospace;
        }
        .chat-bubble-assistant td {
            border-bottom: 1px solid var(--border);
            padding: 8px 12px;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.85rem;
        }

        /* ===== BADGE DE RAMA (color dinámico vía --ruta-color) ===== */
        .ruta-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background-color: color-mix(in srgb, var(--ruta-color, var(--orange-500)) 14%, white);
            color: var(--ruta-color, var(--navy-900));
            font-family: 'IBM Plex Mono', monospace;
            font-weight: 600;
            font-size: 0.72rem;
            padding: 4px 12px;
            border-radius: 6px;
            letter-spacing: 0.6px;
            margin-bottom: 8px;
            text-transform: uppercase;
            border: 1px solid color-mix(in srgb, var(--ruta-color, var(--orange-500)) 40%, white);
        }

        /* ===== INPUT DE CHAT ===== */
        .stChatInput textarea {
            background-color: #FFFFFF !important;
            border: 2px solid var(--border) !important;
            border-radius: 14px !important;
            padding: 12px 20px !important;
            font-size: 0.95rem;
            transition: border-color 0.2s;
        }
        .stChatInput textarea:focus {
            border-color: var(--orange-500) !important;
            box-shadow: 0 0 0 3px rgba(255,107,53,0.15) !important;
        }

        [data-testid="stChatInput"] textarea {
            background: #FFFFFF !important;
            color: #1A2332 !important;
            caret-color: #1A2332 !important;
        }

        [data-testid="stChatInput"] textarea::placeholder {
            color: #8A94A6 !important;
        }

        /* ===== BOTONES GENERALES ===== */
        .stButton>button {
            background-color: var(--navy-900);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            font-family: 'Space Grotesk', sans-serif;
            padding: 8px 16px;
            transition: all 0.2s;
        }
        .stButton>button:hover {
            background-color: var(--orange-500);
            box-shadow: 0 4px 12px rgba(255,107,53,0.25);
        }

        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .nuevo-mensaje {
            animation: fadeInUp 0.3s ease-out;
        }

        @media (prefers-reduced-motion: reduce) {
            .nuevo-mensaje, .modulo-dot, .dot-online::before { animation: none !important; }
        }

        .stMarkdown p { margin-bottom: 0.5rem; }
        hr { border-color: var(--border) !important; }
        .stSpinner > div { border-top-color: var(--orange-500) !important; }
    </style>
    """, unsafe_allow_html=True)

# ---------- FUNCIONES AUXILIARES ----------
def inicializar_sesion():
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"session-{uuid.uuid4().hex[:8]}"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "ultima_ruta" not in st.session_state:
        st.session_state.ultima_ruta = None
    if "app" not in st.session_state:
        with st.spinner("⚙️ Conectando con el núcleo industrial..."):
            st.session_state.app = crear_app()

def nuevo_chat():
    st.session_state.thread_id = f"session-{uuid.uuid4().hex[:8]}"
    st.session_state.messages = []
    st.session_state.ultima_ruta = None
    st.rerun()

def contiene_tabla_markdown(texto: str) -> bool:
    return "|" in texto and "---" in texto

def render_burbuja_assistant(contenedor, texto: str, ruta: str):
    """Renderiza el texto Markdown dentro de una burbuja de asistente,
    con el borde izquierdo coloreado según la rama que generó la respuesta."""
    color = meta_ruta(ruta)["color"]
    contenedor.markdown(
        f'<div class="chat-bubble-assistant" style="--ruta-color:{color};">\n\n{texto}\n\n</div>',
        unsafe_allow_html=True
    )

def render_badge_ruta(contenedor, ruta: str):
    info = meta_ruta(ruta)
    contenedor.markdown(
        f'<span class="ruta-badge" style="--ruta-color:{info["color"]};">{info["icon"]} {info["label"]}</span>',
        unsafe_allow_html=True
    )

def reproducir_sonido():
    st.markdown(
        """
        <audio autoplay style="display:none">
            <source src="https://actions.google.com/sounds/v1/notifications/positive_notification.ogg" type="audio/ogg">
        </audio>
        """,
        unsafe_allow_html=True
    )

# ---------- INTERFAZ PRINCIPAL ----------
def main():
    aplicar_estilo_industrial()
    inicializar_sesion()

    # ========== BARRA LATERAL — PANEL DE CONTROL ==========
    with st.sidebar:
        st.markdown("""
            <div class="sidebar-wordmark">
                <div class="mark">A</div>
                <div class="name">AUVIX</div>
            </div>
            <div class="sidebar-subtitle">Industrial AI · Smart Grid & IoT</div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(f'<span class="session-id mono">SESIÓN {st.session_state.thread_id}</span>', unsafe_allow_html=True)
        st.button("🔄 Nuevo análisis", on_click=nuevo_chat)

        st.markdown("---")
        st.markdown("**MÓDULOS DEL SISTEMA**")

        for clave, info in RUTA_META.items():
            if clave == "desconocida":
                continue
            activo = (st.session_state.ultima_ruta == clave)
            clase = "modulo-card activo" if activo else "modulo-card"
            st.markdown(f"""
                <div class="{clase}" style="--modulo-color:{info['color']};">
                    <span class="modulo-dot"></span>
                    <span class="modulo-label">{info['icon']} {info['label']}</span>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.caption("Auvix S.L. · Asistente Industrial Inteligente")

    # ========== BARRA DE ESTADO SUPERIOR ==========
    hora_actual = datetime.datetime.now().strftime("%H:%M")
    st.markdown(f"""
        <div class="status-bar">
            <div class="brand">
                <div class="mark">A</div>
                <div>
                    <div class="title">Auvix Industrial AI</div>
                    <div class="subtitle">Consultas técnicas · Financieras · Telemetría · API</div>
                </div>
            </div>
            <div class="meta">
                <span class="dot-online">Sistema en línea</span>
                <span class="mono">{hora_actual}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ========== BIENVENIDA (solo si aún no hay conversación) ==========
    if not st.session_state.messages:
        with st.chat_message("assistant", avatar=AVATAR_ASSISTANT):
            render_bienvenida(st)

    # ========== HISTORIAL DE CHAT ==========
    for i, msg in enumerate(st.session_state.messages):
        es_ultimo = (i == len(st.session_state.messages) - 1)
        clase_extra = "nuevo-mensaje" if es_ultimo else ""

        if msg["role"] == "user":
            with st.chat_message("user", avatar=AVATAR_USER):
                st.markdown(f'<div class="chat-bubble-user {clase_extra}">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            with st.chat_message("assistant", avatar=AVATAR_ASSISTANT):
                ruta_msg = msg.get("ruta", "desconocida")
                render_badge_ruta(st, ruta_msg)
                render_burbuja_assistant(st, msg["content"], ruta_msg)

    # ========== ENTRADA DEL USUARIO ==========
    if prompt := st.chat_input("Escribe tu consulta industrial..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=AVATAR_USER):
            st.markdown(f'<div class="chat-bubble-user">{prompt}</div>', unsafe_allow_html=True)

        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        graph = st.session_state.app

        with st.spinner("🔎 Procesando consulta..."):
            try:
                estado_final = graph.invoke(
                    {"messages": [("user", prompt)]},
                    config=config
                )
            except Exception as e:
                st.error(f"⚠️ Error al procesar: {e}")
                return

        mensajes_estado = estado_final.get("messages", [])
        if not mensajes_estado:
            respuesta = "**No se pudo obtener una respuesta.**"
            ruta = "desconocida"
        else:
            ultimo_mensaje = mensajes_estado[-1]
            respuesta = getattr(ultimo_mensaje, "content", "") or ultimo_mensaje.get("content", "")
            if not respuesta:
                respuesta = "*El sistema no generó contenido.*"
            ruta = estado_final.get("ruta", "desconocida")

        st.session_state.ultima_ruta = ruta

        with st.chat_message("assistant", avatar=AVATAR_ASSISTANT):
            render_badge_ruta(st, ruta)

            if contiene_tabla_markdown(respuesta):
                render_burbuja_assistant(st, respuesta, ruta)
            else:
                color = meta_ruta(ruta)["color"]
                placeholder = st.empty()
                texto_mostrado = ""
                palabras = respuesta.split()
                sleep_time = 0.015 if len(palabras) > 80 else 0.03
                chunk_size = 2 if len(palabras) > 80 else 1

                for i in range(0, len(palabras), chunk_size):
                    chunk = " ".join(palabras[i:i+chunk_size]) + " "
                    texto_mostrado += chunk
                    placeholder.markdown(
                        f'<div class="chat-bubble-assistant" style="--ruta-color:{color};">\n\n{texto_mostrado}\n\n</div>',
                        unsafe_allow_html=True
                    )
                    time.sleep(sleep_time)
                render_burbuja_assistant(placeholder, texto_mostrado, ruta)

            reproducir_sonido()

        st.session_state.messages.append({
            "role": "assistant",
            "content": respuesta,
            "ruta": str(ruta)
        })

if __name__ == "__main__":
    main()