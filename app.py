# app.py — Salas UCEN 2026 · Versión producción
#
# ARQUITECTURA:
#   ┌─────────────────────────────────────────────┐
#   │  DATA ACCESS LAYER (DAL)                    │
#   │  Funciones puras que devuelven DataFrames   │
#   │  tipados y listos. La UI no hace lógica.    │
#   ├─────────────────────────────────────────────┤
#   │  PRESENTATION LAYER (UI)                    │
#   │  Solo consume funciones del DAL.            │
#   │  Cada tab aislado con guarded_tab().        │
#   │  Un fallo en un tab no rompe los demás.     │
#   └─────────────────────────────────────────────┘

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io, base64, re
from contextlib import contextmanager

from data_source import (
    b,
    FAC_SHORT, ED_SHORT,
    MODULOS, MODULOS_FULL,
    RANGO_ORDER, EFCAT_ORDER, DIAS_ORDER,
)

st.set_page_config(page_title="Salas UCEN 2026", layout="wide", page_icon="🏫")

st.markdown("""
<style>
html,body{background-color:#0d1117!important}
[data-testid="stApp"]{background-color:#0d1117!important}
[data-testid="stAppViewContainer"]{background-color:#0d1117!important}
[data-testid="stAppViewContainer"]>.main{background-color:#0d1117!important}
.main .block-container{background-color:#0d1117!important;padding-top:.5rem}
[data-testid="stSidebar"]{background-color:#161b22!important;border-right:1px solid #30363d!important}
[data-testid="stHeader"]{background-color:#0d1117!important;border-bottom:1px solid #30363d!important}
footer{display:none!important}
html,body,*,p,span,label,div,li,td,th,h1,h2,h3,h4,h5,h6{color:#ffffff!important}
[data-testid="stSidebar"] *{color:#ffffff!important}
[data-testid="stMarkdownContainer"] *{color:#ffffff!important}
[data-testid="metric-container"]{background:#161b22!important;border:1px solid #30363d!important;border-radius:10px!important;padding:12px 16px!important}
[data-testid="metric-container"] label{color:#c9d1d9!important;font-size:12px!important}
[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#58a6ff!important;font-size:24px!important;font-weight:600!important}
[data-testid="metric-container"] [data-testid="stMetricDelta"]{color:#3fb950!important;font-size:12px!important}
[data-testid="stTabs"] button{color:#c9d1d9!important;background:transparent!important;border-bottom:2px solid transparent!important;font-size:13px!important}
[data-testid="stTabs"] button[aria-selected="true"]{color:#ffffff!important;border-bottom:2px solid #58a6ff!important;font-weight:600!important}
[data-testid="stTabContent"]{background-color:#0d1117!important}
[data-testid="stSelectbox"]>div>div{background-color:#1c2128!important;border:1px solid #444c56!important;border-radius:6px!important}
[data-testid="stSelectbox"] *{color:#ffffff!important}
[data-testid="stSelectbox"] svg{fill:#ffffff!important}
[data-testid="stMultiSelect"]>div>div{background-color:#1c2128!important;border:1px solid #444c56!important;border-radius:6px!important}
[data-testid="stMultiSelect"] *{color:#ffffff!important}
[data-testid="stMultiSelect"] [data-baseweb="tag"]{background-color:#2d333b!important;border:1px solid #444c56!important}
[data-testid="stMultiSelect"] svg{fill:#ffffff!important}
[data-baseweb="popover"] *{background-color:#1c2128!important;color:#ffffff!important}
[data-baseweb="menu"]{background-color:#1c2128!important;border:1px solid #444c56!important}
[data-baseweb="menu"] li{background-color:#1c2128!important;color:#ffffff!important}
[data-baseweb="menu"] li:hover{background-color:#2d333b!important}
[data-baseweb="option"]{background-color:#1c2128!important;color:#ffffff!important}
[data-baseweb="select"]>div{background-color:#1c2128!important;border-color:#444c56!important}
ul[role="listbox"]{background-color:#1c2128!important}
ul[role="listbox"] li{color:#ffffff!important;background-color:#1c2128!important}
ul[role="listbox"] li:hover{background-color:#2d333b!important}
[data-testid="stTextInput"] input{background-color:#1c2128!important;border:1px solid #444c56!important;border-radius:6px!important;color:#ffffff!important}
[data-testid="stTextInput"] input::placeholder{color:#768390!important}
[data-testid="stSlider"] *{color:#ffffff!important}
[data-testid="stDataFrame"]{border:1px solid #30363d!important;border-radius:8px!important;overflow:hidden}
[data-testid="stDataFrame"] *{color:#ffffff!important}
iframe{color-scheme:dark!important}
[data-testid="stDownloadButton"] button{background-color:#1c2128!important;border:1px solid #444c56!important;color:#58a6ff!important;border-radius:6px!important;font-weight:500!important}
[data-testid="stDownloadButton"] button:hover{border-color:#58a6ff!important;background-color:#2d333b!important}
[data-testid="stAlert"] *{color:#ffffff!important}
hr{border-color:#30363d!important}
[data-testid="stCaptionContainer"] *{color:#c9d1d9!important}
.legend-box{background-color:#161b22;border:1px solid #30363d;border-left:3px solid #58a6ff;border-radius:6px;padding:10px 14px;margin-top:8px;font-size:12px;line-height:1.8}
.legend-box b{color:#58a6ff!important}
.update-badge{position:fixed;top:60px;right:16px;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:6px 12px;font-size:11px;color:#c9d1d9!important;z-index:9999;text-align:right}
.update-badge span{color:#58a6ff!important;font-weight:600}
.periodo-banner{background:linear-gradient(90deg,#1e3a5f,#1d4e89);border:1px solid #2563a8;border-radius:8px;padding:10px 16px;margin-bottom:1rem;font-size:14px;font-weight:600}
</style>
""", unsafe_allow_html=True)

st.markdown(
    f'<div class="update-badge">🕐 Última actualización<br><span>{b.get("update_dt", "—")}</span></div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTES DE PLOTLY
# ══════════════════════════════════════════════════════════════════════════════
PTMPL    = "plotly_dark"
PLOT_BG  = "#0d1117"
PAPER_BG = "#0d1117"
GRID_CLR = "#30363d"
FONT_CLR = "#ffffff"
MULTI    = ["#58a6ff","#3fb950","#f78166","#d2a8ff","#ffa657","#76e3ea","#ff7b72"]
BLUES    = ["#1e3a5f","#1d4e89","#2563a8","#3b82c4","#58a6ff","#79b8ff","#a5d0ff"]
GREEN    = "#3fb950"; RED = "#f85149"; ORANGE = "#e3b341"; CYAN = "#58a6ff"; PURPLE = "#d2a8ff"

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS DE UI  (capa de presentación pura — sin lógica de datos)
# ══════════════════════════════════════════════════════════════════════════════

def dl(fig, h=380):
    fig.update_layout(
        template=PTMPL, height=h, plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        font=dict(color=FONT_CLR, size=12), margin=dict(t=40, b=20, l=10, r=10),
        legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1, font=dict(color="#ffffff")),
        xaxis=dict(gridcolor=GRID_CLR, linecolor="#30363d", tickfont=dict(color="#ffffff"), title_font=dict(color="#ffffff")),
        yaxis=dict(gridcolor=GRID_CLR, linecolor="#30363d", tickfont=dict(color="#ffffff"), title_font=dict(color="#ffffff")),
    )
    return fig

def leg(txt):
    st.markdown('<div class="legend-box">📖 ' + txt + '</div>', unsafe_allow_html=True)

def to_xlsx(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Datos")
    buf.seek(0)
    return buf.read()

@contextmanager
def guarded_tab(nombre: str):
    """Aísla fallos por pestaña.
    Si el contenido de un tab lanza cualquier excepción, muestra un mensaje
    limpio y deja el resto de la aplicación funcionando con normalidad."""
    try:
        yield
    except Exception as exc:
        st.warning(
            f"⚠️ La sección **{nombre}** no pudo cargarse correctamente. "
            "Los datos de esta hoja pueden estar incompletos o ausentes en la fuente."
        )
        with st.expander("Ver detalle técnico"):
            st.code(f"{type(exc).__name__}: {exc}", language="text")


# ══════════════════════════════════════════════════════════════════════════════
#  DATA ACCESS LAYER (DAL)
#  Toda la lógica de transformación, tipado y enriquecimiento vive aquí.
#  La UI solo llama funciones de esta sección y recibe DataFrames listos.
# ══════════════════════════════════════════════════════════════════════════════

def _safe_decode(key: str) -> pd.DataFrame:
    """Decodifica Base64 → DataFrame. Lanza ValueError con mensaje limpio."""
    try:
        raw = base64.b64decode(b[key])
        return pd.read_csv(io.StringIO(raw.decode("utf-8")), low_memory=False)
    except KeyError:
        raise ValueError(f"Clave '{key}' no encontrada en data_source.py")
    except (base64.binascii.Error, UnicodeDecodeError) as e:
        raise ValueError(f"Dato corrompido en '{key}': {e}")
    except Exception as e:
        raise ValueError(f"Error inesperado en '{key}': {e}")


@st.cache_data(show_spinner=False)
def load_period(p: str) -> dict[str, pd.DataFrame]:
    """Carga todos los DataFrames de un período desde el diccionario b.
    Cada clave se decodifica de forma independiente; un fallo en una no
    impide que las demás se carguen correctamente."""
    keys = ["res","det","fac","doc","pd_fac","pd_det",
            "conf_doc","conf_sala","ef_fac","ef_ed","ef_det",
            "opt","conc_mod","conc_fac_mod","conc_turno","prox"]
    result: dict[str, pd.DataFrame] = {}
    for k in keys:
        full_key = f"{p}_{k}"
        try:
            df = _safe_decode(full_key)
            if "Capacidad" in df.columns:
                df["Capacidad"] = pd.to_numeric(df["Capacidad"], errors="coerce").fillna(0).astype(int)
            result[k] = df
        except ValueError:
            result[k] = pd.DataFrame()   # fallo aislado — DataFrame vacío
    return result


@st.cache_data(show_spinner=False)
def load_rev() -> pd.DataFrame:
    try:
        return _safe_decode("rev")
    except ValueError:
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def get_merged(periodos: tuple, key: str, col_periodo: bool = True) -> pd.DataFrame:
    """Combina DataFrames de uno o dos períodos. Hasheable por tuple."""
    dfs = []
    for p in periodos:
        df = load_period(p).get(key, pd.DataFrame()).copy()
        if not df.empty and col_periodo:
            df["Periodo"] = "2026-01" if p == "202601" else "2026-02"
        dfs.append(df)
    non_empty = [d for d in dfs if not d.empty]
    return pd.concat(non_empty, ignore_index=True) if non_empty else pd.DataFrame()


# ── Funciones del DAL que enriquecen DataFrames base ─────────────────────────

@st.cache_data(show_spinner=False)
def dal_res(periodos: tuple) -> pd.DataFrame:
    """df_res con Ed_corto tipado y Dia como Categorical ordenado."""
    df = get_merged(periodos, "res")
    if df.empty:
        return df
    df["Ed_corto"] = df["Edificio"].map(ED_SHORT).fillna(df["Edificio"])
    df["Dia"]      = pd.Categorical(df["Dia"], categories=DIAS_ORDER, ordered=True)
    return df


@st.cache_data(show_spinner=False)
def dal_det(periodos: tuple) -> pd.DataFrame:
    """df_det con Ed_corto, Dia Categorical y Capacidad int garantizado."""
    df = get_merged(periodos, "det")
    if df.empty:
        return df
    df["Ed_corto"]  = df["Edificio"].map(ED_SHORT).fillna(df["Edificio"])
    df["Dia"]       = pd.Categorical(df["Dia"], categories=DIAS_ORDER, ordered=True)
    df["Capacidad"] = pd.to_numeric(df.get("Capacidad", 0), errors="coerce").fillna(0).astype(int)
    return df


@st.cache_data(show_spinner=False)
def dal_fac(periodos: tuple) -> pd.DataFrame:
    """df_fac con Fac_corto mapeado."""
    df = get_merged(periodos, "fac")
    if df.empty:
        return df
    df["Fac_corto"] = df["Facultad"].map(FAC_SHORT).fillna(df["Facultad"])
    return df


@st.cache_data(show_spinner=False)
def dal_doc(periodos: tuple) -> pd.DataFrame:
    """df_doc con Fac_corto mapeado (sin columna Periodo — es anual)."""
    df = get_merged(periodos, "doc", col_periodo=False)
    if df.empty:
        return df
    df["Fac_corto"] = df["Facultad"].map(FAC_SHORT).fillna(df["Facultad"])
    return df


@st.cache_data(show_spinner=False)
def compute_global(periodos: tuple):
    """Calcula métricas globales de ocupación. Cacheado por firma de períodos."""
    df_res = dal_res(periodos)
    if df_res.empty:
        return pd.DataFrame(), 0, 0, 0.0
    ocup_ed = (
        df_res
        .drop_duplicates(["Edificio","Periodo"] if "Periodo" in df_res.columns else ["Edificio"])
        [["Ed_corto","Pct_Global_Edificio","Bloques_Posibles_Ed","Bloques_Ocupados_Ed"]]
        .groupby("Ed_corto", as_index=False).first()
    )
    ocp = ocup_ed["Bloques_Ocupados_Ed"].sum()
    pos = ocup_ed["Bloques_Posibles_Ed"].sum()
    pct = round(ocp / pos * 100, 1) if pos > 0 else 0.0
    return ocup_ed, int(ocp), int(pos), pct


def rng(c) -> str:
    """Clasifica capacidad en rango de cupo. Definida a nivel módulo."""
    c = int(c)
    if c <= 20: return "≤20 pax"
    if c <= 30: return "21-30 pax"
    if c <= 40: return "31-40 pax"
    if c <= 50: return "41-50 pax"
    return "51+ pax"


# ══════════════════════════════════════════════════════════════════════════════
#  PRESENTATION LAYER — SELECTOR DE PERÍODO
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(
    '<div style="display:flex;align-items:center;gap:14px;margin-bottom:8px;margin-right:200px">'
    '<span style="font-size:34px">🏫</span>'
    '<div><h1 style="margin:0;font-size:24px;color:#ffffff;">Disponibilidad de Salas · UCEN · Santiago</h1>'
    '<p style="margin:0;color:#c9d1d9;font-size:12px;">Salas de clases y laboratorios · Diurno L–V · Módulos 1–7</p>'
    '</div></div>',
    unsafe_allow_html=True,
)

periodo_opts = ["2026-01 (Primer semestre)", "2026-02 (Segundo semestre)", "Anual 2026 (Comparativo)"]
sel_periodo  = st.radio("📅 Periodo", periodo_opts, horizontal=True, label_visibility="collapsed")

if sel_periodo.startswith("2026-01"):
    periodos_list = ["202601"]; label_periodo = "2026-01"
elif sel_periodo.startswith("2026-02"):
    periodos_list = ["202602"]; label_periodo = "2026-02"
else:
    periodos_list = ["202601","202602"]; label_periodo = "Anual 2026"

periodos = tuple(periodos_list)

st.markdown('<div class="periodo-banner">📊 Analizando: <b>' + label_periodo + '</b></div>', unsafe_allow_html=True)

# Precarga silenciosa de períodos
for p in periodos:
    load_period(p)

# Obtener DataFrames enriquecidos desde el DAL
df_res     = dal_res(periodos)
df_det     = dal_det(periodos)
df_fac_raw = dal_fac(periodos)
df_doc_raw = dal_doc(periodos)
ocup_ed, global_ocp, global_pos, PCT_GLOBAL = compute_global(periodos)

# ── SIDEBAR FILTROS ───────────────────────────────────────────────────────────
st.sidebar.markdown("## 🔎 Filtros de saturación")
st.sidebar.caption("Solo afectan la sección de saturación global de salas.")
edificios_opts = list(ED_SHORT.values())
sel_ed   = st.sidebar.multiselect("Edificio", edificios_opts, default=edificios_opts)
sel_dias = st.sidebar.multiselect("Día", DIAS_ORDER, default=DIAS_ORDER)
sel_mods = st.sidebar.multiselect("Módulo", list(MODULOS.keys()), format_func=lambda x: MODULOS_FULL[x], default=list(MODULOS.keys()))

# Filtros aplicados a copias — la UI no muta los DataFrames del DAL
if not df_res.empty:
    fr = df_res[df_res["Ed_corto"].isin(sel_ed) & df_res["Dia"].isin(sel_dias) & df_res["Modulo"].isin(sel_mods)].copy()
else:
    fr = pd.DataFrame()

if not df_det.empty:
    fd = df_det[df_det["Ed_corto"].isin(sel_ed) & df_det["Dia"].isin(sel_dias) & df_det["Modulo"].isin(sel_mods)].copy()
else:
    fd = pd.DataFrame()

# ── KPIs GLOBALES ─────────────────────────────────────────────────────────────
st.markdown("### 📌 Ocupación global horario diurno")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Ocupación global",  f"{PCT_GLOBAL}%", delta=f"{round(100-PCT_GLOBAL,1)}% disponible", delta_color="inverse")
k2.metric("Bloques posibles",  f"{global_pos:,}")
k3.metric("Bloques ocupados",  f"{global_ocp:,}")
k4.metric("Bloques libres",    f"{global_pos-global_ocp:,}")
k5.metric("Disponibilidad",    f"{round(100-PCT_GLOBAL,1)}%")

col_g1, col_g2 = st.columns([1,2])
with col_g1:
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number", value=PCT_GLOBAL,
        title={"text":"% Ocupación global","font":{"size":13,"color":"#ffffff"}},
        number={"font":{"color":"#58a6ff","size":36}},
        gauge={"axis":{"range":[0,100],"tickcolor":"#ffffff","tickfont":{"color":"#ffffff"}},
               "bar":{"color":"#58a6ff"},"bgcolor":"#161b22","bordercolor":"#30363d",
               "steps":[{"range":[0,50],"color":"#0d2818"},{"range":[50,75],"color":"#1a2f1a"},
                         {"range":[75,90],"color":"#2d2000"},{"range":[90,100],"color":"#3d0f0f"}],
               "threshold":{"line":{"color":RED,"width":3},"thickness":0.75,"value":90}},
    ))
    fig_g.update_layout(height=250,paper_bgcolor=PLOT_BG,plot_bgcolor=PLOT_BG,
                        font=dict(color="#ffffff"),margin=dict(t=40,b=10,l=10,r=10))
    st.plotly_chart(fig_g, use_container_width=True)
with col_g2:
    if not ocup_ed.empty:
        ocup_s = ocup_ed.sort_values("Pct_Global_Edificio", ascending=True)
        fig_e  = px.bar(ocup_s, x="Pct_Global_Edificio", y="Ed_corto", orientation="h",
                        color="Pct_Global_Edificio",
                        color_continuous_scale=[[0,"#1e3a5f"],[0.5,"#2563a8"],[0.9,ORANGE],[1,RED]],
                        range_color=[0,100], text="Pct_Global_Edificio",
                        labels={"Pct_Global_Edificio":"% Ocupación","Ed_corto":""})
        fig_e.update_traces(texttemplate="%{text}%",textposition="outside",textfont=dict(color="#ffffff",size=12))
        fig_e.add_vline(x=90,line_dash="dash",line_color=RED,line_width=1.5,
                        annotation_text="90%",annotation_font=dict(color=RED,size=11))
        dl(fig_e,230); fig_e.update_layout(coloraxis_showscale=False,xaxis_range=[0,115])
        st.plotly_chart(fig_e, use_container_width=True)

leg("<b>Bloques posibles:</b> combinaciones sala×día×módulo disponibles. <b>Bloques ocupados:</b> cuántos tienen al menos una clase. <b>Ocupación global = ocupados / posibles × 100.</b>")
st.divider()

if not fr.empty:
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Bloques analizados",    len(fr))
    c2.metric("Ocupación prom.",       f"{fr['Pct_Ocupacion'].mean():.1f}%")
    c3.metric("Salas libres prom.",    f"{fr['Libres'].mean():.1f}")
    c4.metric("Bloques críticos ≥90%", int((fr["Pct_Ocupacion"]>=90).sum()))
    c5.metric("Bloques holgados ≤30%", int((fr["Pct_Ocupacion"]<=30).sum()))
st.divider()

tabs = st.tabs(["📊 Saturación","📅 Por día","🪑 Cupos","🎓 Facultades",
                "👨‍🏫 Carga docente","📝 Por designar","🚨 Próximas a iniciar",
                "⚠️ Conflictos","📐 Eficiencia","🕐 Concentración","📋 Reservas","🔍 Detalle salas"])

# ══════════════════════════════════════════════════════════════════════════════
#  TABS — cada uno envuelto en guarded_tab() para aislamiento de fallos
# ══════════════════════════════════════════════════════════════════════════════

# ── TAB 1: SATURACIÓN ────────────────────────────────────────────────────────
with tabs[0]:
    with guarded_tab("Saturación"):
        if fr.empty:
            st.info("Sin datos de saturación para el período seleccionado.")
        else:
            if label_periodo == "Anual 2026" and "Periodo" in fr.columns:
                fig = px.bar(
                    fr.groupby(["Ed_corto","Modulo","Periodo"])["Pct_Ocupacion"].mean().reset_index()
                      .assign(ML=lambda x: x["Modulo"].map(MODULOS)),
                    x="ML",y="Pct_Ocupacion",color="Ed_corto",barmode="group",facet_col="Periodo",
                    color_discrete_sequence=MULTI,labels={"ML":"","Pct_Ocupacion":"% Ocupación","Ed_corto":"Edificio"})
            else:
                p2 = fr.groupby(["Ed_corto","Modulo"])["Pct_Ocupacion"].mean().reset_index()
                p2["ML"] = p2["Modulo"].map(MODULOS)
                fig = px.bar(p2,x="ML",y="Pct_Ocupacion",color="Ed_corto",barmode="group",
                             color_discrete_sequence=MULTI,labels={"ML":"","Pct_Ocupacion":"% Ocupación","Ed_corto":"Edificio"})
            fig.add_hline(y=90,line_dash="dash",line_color=RED,line_width=1.5,annotation_text="90%",annotation_font=dict(color=RED))
            fig.add_hline(y=70,line_dash="dot",line_color=ORANGE,line_width=1,annotation_text="70%",annotation_font=dict(color=ORANGE))
            dl(fig,380); fig.update_layout(yaxis_range=[0,105])
            st.plotly_chart(fig,use_container_width=True)
            leg("<b>% Ocupación por módulo:</b> promedio de salas ocupadas sobre total disponibles. <b>Línea 90%:</b> umbral crítico.")

            hm = fr.groupby(["Ed_corto","Modulo"])["Pct_Ocupacion"].mean().unstack("Modulo")
            hm.columns = [MODULOS[c] for c in hm.columns]
            fig2 = px.imshow(hm,text_auto=".1f",
                             color_continuous_scale=[[0,"#0d2818"],[0.5,"#1d4e89"],[0.9,ORANGE],[1,RED]],
                             zmin=0,zmax=100,aspect="auto")
            fig2.update_traces(textfont=dict(color="#ffffff",size=11)); fig2.update_xaxes(tickangle=-20); dl(fig2,260)
            st.plotly_chart(fig2,use_container_width=True)
            leg("<b>Heatmap:</b> verde oscuro = disponibilidad, rojo = saturación.")

            p3 = fr.groupby("Modulo")[["Libres","Ocupadas"]].mean().reset_index(); p3["ML"] = p3["Modulo"].map(MODULOS)
            fig3 = px.bar(p3.melt(id_vars="ML",value_vars=["Libres","Ocupadas"]),
                          x="ML",y="value",color="variable",barmode="stack",
                          color_discrete_map={"Libres":GREEN,"Ocupadas":RED},
                          labels={"ML":"","value":"Salas","variable":""})
            dl(fig3,300); st.plotly_chart(fig3,use_container_width=True)
            leg("<b>Salas libres vs ocupadas:</b> promedio por módulo sumando todos los edificios.")

# ── TAB 2: POR DÍA ───────────────────────────────────────────────────────────
with tabs[1]:
    with guarded_tab("Por día"):
        if fr.empty:
            st.info("Sin datos para el período seleccionado.")
        else:
            sel2 = st.selectbox("Edificio",sel_ed if sel_ed else edificios_opts,key="ed2")
            fr2  = fr[fr["Ed_corto"]==sel2]
            if fr2.empty:
                st.info("Sin datos para el edificio seleccionado.")
            else:
                if label_periodo == "Anual 2026" and "Periodo" in fr2.columns:
                    c1,c2 = st.columns(2)
                    for i,(per,grp) in enumerate(fr2.groupby("Periodo")):
                        p3b = grp.groupby(["Dia","Modulo"])["Libres"].mean().reset_index()
                        p3b["ML"]  = p3b["Modulo"].map(MODULOS)
                        p3b["Dia"] = pd.Categorical(p3b["Dia"],categories=DIAS_ORDER,ordered=True)
                        fig4 = px.bar(p3b.sort_values("Dia"),x="Dia",y="Libres",color="ML",barmode="group",
                                      color_discrete_sequence=BLUES,title=f"Salas libres — {per}",
                                      labels={"Dia":"","Libres":"Salas libres","ML":"Módulo"})
                        dl(fig4,320); [c1,c2][i].plotly_chart(fig4,use_container_width=True)
                else:
                    p3b = fr2.groupby(["Dia","Modulo"])["Libres"].mean().reset_index()
                    p3b["ML"]  = p3b["Modulo"].map(MODULOS)
                    p3b["Dia"] = pd.Categorical(p3b["Dia"],categories=DIAS_ORDER,ordered=True)
                    fig4 = px.bar(p3b.sort_values("Dia"),x="Dia",y="Libres",color="ML",barmode="group",
                                  color_discrete_sequence=BLUES,labels={"Dia":"","Libres":"Salas libres","ML":"Módulo"})
                    dl(fig4,360); st.plotly_chart(fig4,use_container_width=True)
                leg("<b>Salas libres por día y módulo:</b> disponibilidad en ese edificio para cada combinación día-módulo.")
                tbl = p3b.pivot(index="Dia",columns="ML",values="Libres").round(1)
                st.dataframe(tbl,use_container_width=True)
                p4b = fr2.groupby(["Dia","Modulo"])["Pct_Ocupacion"].mean().reset_index()
                p4b["ML"]  = p4b["Modulo"].map(MODULOS)
                p4b["Dia"] = pd.Categorical(p4b["Dia"],categories=DIAS_ORDER,ordered=True)
                fig5 = px.line(p4b.sort_values("Dia"),x="Dia",y="Pct_Ocupacion",color="ML",markers=True,
                               color_discrete_sequence=MULTI,labels={"Dia":"","Pct_Ocupacion":"% Ocupación","ML":"Módulo"})
                fig5.add_hline(y=90,line_dash="dash",line_color=RED,line_width=1.5)
                dl(fig5,300); fig5.update_layout(yaxis_range=[0,105])
                st.plotly_chart(fig5,use_container_width=True)
                leg("<b>Evolución semanal:</b> cómo varía la ocupación de cada módulo a lo largo de la semana.")

# ── TAB 3: CUPOS ─────────────────────────────────────────────────────────────
with tabs[2]:
    with guarded_tab("Cupos"):
        if fd.empty:
            st.info("Sin datos de detalle para el período seleccionado.")
        else:
            ca,cb = st.columns(2)
            with ca: sel3e = st.selectbox("Edificio",sel_ed if sel_ed else edificios_opts,key="ed3")
            with cb: sel3d = st.selectbox("Día",sel_dias if sel_dias else DIAS_ORDER,key="dia3")
            fd3 = fd[(fd["Ed_corto"]==sel3e)&(fd["Dia"]==sel3d)].copy()
            if fd3.empty:
                st.info("Sin salas disponibles con los filtros seleccionados.")
            else:
                fd3["Rango"] = pd.Categorical(fd3["Capacidad"].apply(rng),categories=RANGO_ORDER,ordered=True)
                cnt = fd3.groupby(["Modulo","Rango"],observed=True).size().reset_index(name="Cant")
                cnt["ML"] = cnt["Modulo"].map(MODULOS)
                fig6 = px.bar(cnt,x="ML",y="Cant",color="Rango",barmode="stack",
                              color_discrete_sequence=[GREEN,CYAN,PURPLE,ORANGE,RED],
                              category_orders={"Rango":RANGO_ORDER},labels={"ML":"","Cant":"Salas libres","Rango":"Cupo"})
                dl(fig6,360); st.plotly_chart(fig6,use_container_width=True)
                leg("<b>Distribución de cupos:</b> salas libres clasificadas por rango de capacidad.")
                c1,c2 = st.columns(2)
                with c1:
                    tc = fd3.groupby(["Modulo","Tipo"]).size().reset_index(name="Cant"); tc["ML"] = tc["Modulo"].map(MODULOS)
                    fig7 = px.bar(tc,x="ML",y="Cant",color="Tipo",barmode="group",
                                  color_discrete_map={"SALA DE CLASES":CYAN,"LABORATORIO DE COMPUTACION":ORANGE})
                    dl(fig7,280); st.plotly_chart(fig7,use_container_width=True)
                    leg("<b>SC vs Laboratorio:</b> no son intercambiables.")
                with c2:
                    cm = fd3.groupby("Modulo")["Capacidad"].sum().reset_index(); cm["ML"] = cm["Modulo"].map(MODULOS)
                    fig8 = px.bar(cm,x="ML",y="Capacidad",color="Capacidad",
                                  color_continuous_scale=[[0,"#1e3a5f"],[1,CYAN]])
                    dl(fig8,280); fig8.update_layout(coloraxis_showscale=False)
                    st.plotly_chart(fig8,use_container_width=True)
                    leg("<b>Cupos totales:</b> suma de capacidad de salas libres por módulo.")

# ── TAB 4: FACULTADES ────────────────────────────────────────────────────────
with tabs[3]:
    with guarded_tab("Facultades"):
        df_fac = df_fac_raw.copy()
        if df_fac.empty:
            st.info("Sin datos de facultades.")
        else:
            if label_periodo == "Anual 2026" and "Periodo" in df_fac.columns:
                c1,c2 = st.columns(2)
                for i,(per,grp) in enumerate(df_fac.groupby("Periodo")):
                    grp2 = grp.copy(); grp2["Fac_corto"] = grp2["Facultad"].map(FAC_SHORT).fillna(grp2["Facultad"])
                    fig_f = px.bar(grp2.sort_values("Bloques_sala",ascending=True),
                                   x="Bloques_sala",y="Fac_corto",orientation="h",
                                   color="Bloques_sala",color_continuous_scale=[[0,"#1e3a5f"],[1,CYAN]],text="Bloques_sala",
                                   title=f"Bloques usados — {per}",labels={"Bloques_sala":"Bloques","Fac_corto":""})
                    fig_f.update_traces(textposition="outside",textfont=dict(color="#ffffff",size=11))
                    dl(fig_f,320); fig_f.update_layout(coloraxis_showscale=False)
                    [c1,c2][i].plotly_chart(fig_f,use_container_width=True)
            else:
                f1,f2,f3 = st.columns(3)
                f1.metric("Total bloques usados",      f"{df_fac['Bloques_sala'].sum():,}")
                f2.metric("Facultades con exceso cupo",int((df_fac["Secc_exceso_cupo"]>0).sum()))
                f3.metric("Secciones totales",         f"{df_fac['Secciones'].sum():,}")
                fig_f1 = px.bar(df_fac.sort_values("Bloques_sala",ascending=True),
                                x="Bloques_sala",y="Fac_corto",orientation="h",
                                color="Bloques_sala",color_continuous_scale=[[0,"#1e3a5f"],[1,CYAN]],text="Bloques_sala",
                                labels={"Bloques_sala":"Bloques usados","Fac_corto":""})
                fig_f1.update_traces(textposition="outside",textfont=dict(color="#ffffff",size=12))
                dl(fig_f1,340); fig_f1.update_layout(coloraxis_showscale=False)
                st.plotly_chart(fig_f1,use_container_width=True)
            leg("<b>Bloques de sala usados:</b> sala ocupada en un día y módulo. <b>Exceso cupo:</b> secciones donde cupo supera capacidad.")
            c1,c2 = st.columns(2)
            with c1:
                fig_f2 = px.pie(df_fac,values="Secciones",names="Fac_corto",color_discrete_sequence=MULTI)
                dl(fig_f2,300); st.plotly_chart(fig_f2,use_container_width=True)
                leg("<b>Secciones por facultad.</b>")
            with c2:
                fig_f3 = px.scatter(df_fac,x="Cap_sala_prom",y="Cupo_prom",size="Secciones",
                                    color="Fac_corto",text="Fac_corto",color_discrete_sequence=MULTI,
                                    labels={"Cap_sala_prom":"Cap. prom.","Cupo_prom":"Cupo prom."})
                fig_f3.add_shape(type="line",x0=0,y0=0,x1=60,y1=60,line=dict(color=RED,dash="dash",width=1.5))
                fig_f3.update_traces(textposition="top center",textfont=dict(color="#ffffff"))
                dl(fig_f3,300); fig_f3.update_layout(showlegend=False)
                st.plotly_chart(fig_f3,use_container_width=True)
                leg("<b>Cupo vs capacidad sala:</b> sobre la diagonal = cupo supera sala.")
            df_ft = df_fac[["Facultad","Secciones","Bloques_sala","Salas_distintas","Cupo_prom","Cap_sala_prom","Secc_exceso_cupo"]].copy()
            df_ft.columns = ["Facultad","Secciones","Bloques sala","Salas distintas","Cupo prom","Cap. sala prom","Secc. exceso"]
            st.dataframe(df_ft.sort_values("Bloques sala",ascending=False),use_container_width=True,hide_index=True)
            st.download_button("⬇️ Descargar Excel",to_xlsx(df_ft),"facultades.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── TAB 5: CARGA DOCENTE ─────────────────────────────────────────────────────
with tabs[4]:
    with guarded_tab("Carga docente"):
        df_doc = df_doc_raw.copy()
        if df_doc.empty:
            st.info("Sin datos de docentes.")
        else:
            d1,d2,d3,d4 = st.columns(4)
            d1.metric("Docentes",        len(df_doc))
            d2.metric("Horas prom./sem.",f"{df_doc['Horas_sem'].mean():.1f}")
            d3.metric("Máx. horas/sem.", f"{df_doc['Horas_sem'].max():.1f}")
            d4.metric("Con conflictos",  int((df_doc["Conflictos_horario"]>0).sum()))
            leg("<b>Horas semanales = suma minutos / 60. Conflicto:</b> docente en 2+ clases el mismo bloque.")
            col_d1,col_d2 = st.columns(2)
            with col_d1:
                fig_d1 = px.histogram(df_doc,x="Horas_sem",nbins=30,color_discrete_sequence=[CYAN],
                                      labels={"Horas_sem":"Horas semanales","count":"Docentes"})
                dl(fig_d1,300); st.plotly_chart(fig_d1,use_container_width=True)
                leg("<b>Distribución de carga:</b> concentración alta = sobrecarga en parte del cuerpo docente.")
            with col_d2:
                hf = df_doc.groupby("Fac_corto")["Horas_sem"].mean().reset_index().sort_values("Horas_sem",ascending=True)
                fig_d2 = px.bar(hf,x="Horas_sem",y="Fac_corto",orientation="h",
                                color="Horas_sem",color_continuous_scale=[[0,"#1a2f1a"],[1,GREEN]],text="Horas_sem",
                                labels={"Horas_sem":"Horas prom.","Fac_corto":""})
                fig_d2.update_traces(texttemplate="%{text:.1f}",textposition="outside",textfont=dict(color="#ffffff",size=12))
                dl(fig_d2,300); fig_d2.update_layout(coloraxis_showscale=False)
                st.plotly_chart(fig_d2,use_container_width=True)
                leg("<b>Horas promedio por facultad.</b>")
            st.markdown("#### Top 20 docentes con mayor carga")
            top_doc = df_doc.nlargest(20,"Horas_sem")[["RUT","Docente","Fac_corto","Nivel","Secciones","Horas_sem","Dias_activos","Conflictos_horario"]].copy()
            top_doc.columns = ["RUT","Docente","Facultad","Nivel","Secciones","Horas sem.","Días activos","Conflictos"]
            st.dataframe(top_doc,use_container_width=True,hide_index=True)
            st.download_button("⬇️ Descargar Excel",to_xlsx(top_doc),"top_docentes.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            busq_doc = st.text_input("🔍 Buscar docente (nombre o RUT)",key="busq_doc")
            if busq_doc:
                safe_q = re.escape(busq_doc.strip())
                res_doc = df_doc[
                    df_doc["Docente"].str.contains(safe_q,case=False,na=False,regex=True) |
                    df_doc["RUT"].astype(str).str.contains(safe_q,na=False,regex=True)
                ]
                if not res_doc.empty:
                    sd = res_doc[["RUT","Docente","Fac_corto","Nivel","Secciones","Horas_sem","Dias_activos","Conflictos_horario"]].copy()
                    sd.columns = ["RUT","Docente","Facultad","Nivel","Secciones","Horas sem.","Días activos","Conflictos"]
                    st.dataframe(sd,use_container_width=True,hide_index=True)
                else:
                    st.warning("No se encontró ningún docente.")

# ── TAB 6: POR DESIGNAR ──────────────────────────────────────────────────────
with tabs[5]:
    with guarded_tab("Por designar"):
        st.subheader("📝 Secciones sin docente definitivo")
        if label_periodo == "Anual 2026":
            c1,c2 = st.columns(2)
            for i,p in enumerate(periodos):
                pd_data = load_period(p)
                df_pd_fac = pd_data.get("pd_fac",pd.DataFrame()).copy()
                df_pd_det = pd_data.get("pd_det",pd.DataFrame()).copy()
                if df_pd_fac.empty:
                    [c1,c2][i].info(f"Sin datos pendientes para {'2026-01' if p=='202601' else '2026-02'}.")
                    continue
                df_pd_fac["Fac_corto"] = df_pd_fac["FACULTAD"].map(FAC_SHORT).fillna(df_pd_fac["FACULTAD"])
                per_lbl = "2026-01" if p=="202601" else "2026-02"
                [c1,c2][i].metric(f"Pendientes {per_lbl}",len(df_pd_det))
                fig_pd = px.bar(df_pd_fac.sort_values("Secciones",ascending=True),
                                x="Secciones",y="Fac_corto",color="TIPO_PENDIENTE",orientation="h",barmode="stack",
                                color_discrete_map={"Por designar":ORANGE,"Sin asignar":RED},
                                title=per_lbl,labels={"Secciones":"N° secciones","Fac_corto":"","TIPO_PENDIENTE":"Estado"})
                dl(fig_pd,320); [c1,c2][i].plotly_chart(fig_pd,use_container_width=True)
        else:
            p = periodos[0]
            pd_data   = load_period(p)
            df_pd_fac = pd_data.get("pd_fac",pd.DataFrame()).copy()
            df_pd_det = pd_data.get("pd_det",pd.DataFrame()).copy()
            if df_pd_fac.empty:
                st.info("Sin datos de secciones pendientes.")
            else:
                df_pd_fac["Fac_corto"] = df_pd_fac["FACULTAD"].map(FAC_SHORT).fillna(df_pd_fac["FACULTAD"])
                total_pd = df_pd_det["TIPO_PENDIENTE"].value_counts() if not df_pd_det.empty else pd.Series(dtype=int)
                p1,p2,p3 = st.columns(3)
                p1.metric("Total pendientes",    len(df_pd_det))
                p2.metric("Con 'Por designar'",  int(total_pd.get("Por designar",0)))
                p3.metric("Sin asignar (vacío)", int(total_pd.get("Sin asignar",0)))
                fig_pd = px.bar(df_pd_fac.sort_values("Secciones",ascending=True),
                                x="Secciones",y="Fac_corto",color="TIPO_PENDIENTE",orientation="h",barmode="stack",
                                color_discrete_map={"Por designar":ORANGE,"Sin asignar":RED},
                                labels={"Secciones":"N° secciones","Fac_corto":"","TIPO_PENDIENTE":"Estado"})
                dl(fig_pd,360); st.plotly_chart(fig_pd,use_container_width=True)
                leg("<b>Por designar:</b> celda con 'POR DESIGNAR'. <b>Sin asignar:</b> celda vacía.")
                if not df_pd_det.empty:
                    fac_f  = st.multiselect("Filtrar por facultad",
                                            sorted(df_pd_det["FACULTAD"].map(FAC_SHORT).fillna(df_pd_det["FACULTAD"]).unique()),key="fac_pd")
                    tipo_f = st.multiselect("Filtrar por tipo",["Por designar","Sin asignar"],
                                            default=["Por designar","Sin asignar"],key="tipo_pd")
                    df_show = df_pd_det.copy(); df_show["Facultad"] = df_show["FACULTAD"].map(FAC_SHORT).fillna(df_show["FACULTAD"])
                    if fac_f:  df_show = df_show[df_show["Facultad"].isin(fac_f)]
                    if tipo_f: df_show = df_show[df_show["TIPO_PENDIENTE"].isin(tipo_f)]
                    show_c = df_show[["ID_ASIG","ASIGNATURA","SECCION","TIPO","Facultad","LUGAR","EDIFICIO","CUPO","TIPO_PENDIENTE"]].copy()
                    show_c.columns = ["ID Asig.","Asignatura","Secc.","Tipo","Facultad","Sala","Edificio","Cupo","Estado"]
                    st.info(f"Mostrando {len(show_c)} secciones pendientes")
                    st.dataframe(show_c,use_container_width=True,hide_index=True)
                    st.download_button("⬇️ Descargar Excel",to_xlsx(show_c),"sin_docente.xlsx",
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── TAB 7: PRÓXIMAS ──────────────────────────────────────────────────────────
with tabs[6]:
    with guarded_tab("Próximas a iniciar"):
        st.subheader("🚨 Secciones próximas a iniciar (60 días)")
        p       = periodos[-1]
        df_prox = load_period(p).get("prox",pd.DataFrame()).copy()
        if df_prox.empty:
            st.info("Sin datos de próximas secciones.")
        else:
            df_prox["Fac_corto"] = df_prox["FACULTAD"].map(FAC_SHORT).fillna(df_prox["FACULTAD"])
            dias_f  = st.slider("Días para inicio",0,60,60,key="dias_prox")
            df_p    = df_prox[df_prox["DIAS"]<=dias_f].copy()
            sin_doc = df_p[df_p["ESTADO"]=="Sin docente"]
            con_doc = df_p[df_p["ESTADO"]=="Con docente"]
            pr1,pr2,pr3,pr4 = st.columns(4)
            pr1.metric("Total secciones", len(df_p))
            pr2.metric("✅ Con docente",  len(con_doc))
            pr3.metric("⚠️ Sin docente", len(sin_doc))
            pr4.metric("% regularizadas", f"{round(len(con_doc)/len(df_p)*100,1) if len(df_p)>0 else 0}%")
            leg("<b>Próximas a iniciar:</b> primera clase dentro del rango seleccionado.")
            c1,c2 = st.columns(2)
            with c1:
                ec = df_p.groupby("ESTADO").size().reset_index(name="N")
                fig_pr1 = px.pie(ec,values="N",names="ESTADO",color="ESTADO",
                                 color_discrete_map={"Con docente":GREEN,"Sin docente":RED})
                dl(fig_pr1,280); st.plotly_chart(fig_pr1,use_container_width=True)
            with c2:
                fe = df_p.groupby(["Fac_corto","ESTADO"]).size().reset_index(name="N")
                fig_pr2 = px.bar(fe,x="N",y="Fac_corto",color="ESTADO",orientation="h",barmode="stack",
                                 color_discrete_map={"Con docente":GREEN,"Sin docente":RED},
                                 labels={"N":"Secciones","Fac_corto":"","ESTADO":"Estado"})
                dl(fig_pr2,280); st.plotly_chart(fig_pr2,use_container_width=True)
            if len(sin_doc)>0:
                st.markdown("#### Secciones sin docente próximas a iniciar")
                sd_show = sin_doc[["ID_ASIG","ASIGNATURA","SECCION","TIPO","Fac_corto","LUGAR","EDIFICIO","FECHA_STR","DIAS","CUPO"]].copy()
                sd_show.columns = ["ID Asig.","Asignatura","Secc.","Tipo","Facultad","Sala","Edificio","Fecha inicio","Días restantes","Cupo"]
                st.dataframe(sd_show.sort_values("Días restantes"),use_container_width=True,hide_index=True)
                st.download_button("⬇️ Descargar Excel",to_xlsx(sd_show),"alertas_sin_docente.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.success("✅ Todas las secciones próximas tienen docente asignado.")

# ── TAB 8: CONFLICTOS ────────────────────────────────────────────────────────
with tabs[7]:
    with guarded_tab("Conflictos"):
        p     = periodos[-1]
        pdata = load_period(p)
        df_cd = pdata.get("conf_doc",pd.DataFrame()).copy()
        df_cs = pdata.get("conf_sala",pd.DataFrame()).copy()
        cv1,cv2 = st.columns(2)
        cv1.metric("Conflictos de docente",len(df_cd))
        cv2.metric("Conflictos de sala",   len(df_cs))
        leg("<b>Conflicto de docente:</b> mismo RUT en 2+ clases al mismo tiempo. <b>Conflicto de sala:</b> misma sala con 2+ secciones en el mismo bloque.")
        if not df_cd.empty:
            st.markdown("#### Docentes con 2+ clases en el mismo bloque")
            df_cd_s = df_cd[["RUT","Docente","Dia","Hora","N_clases","IDs_Asig","Asignaturas"]].copy()
            df_cd_s.columns = ["RUT","Docente","Día","Hora","N° clases","IDs Asig.","Asignaturas"]
            st.dataframe(df_cd_s,use_container_width=True,hide_index=True)
            st.download_button("⬇️ Descargar Excel",to_xlsx(df_cd_s),"conflictos_docente.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if not df_cs.empty:
            st.markdown("#### Salas con 2+ secciones en el mismo bloque")
            df_cs_s = df_cs[["Sala","Dia","Hora","N_secciones","IDs_Asig","Asignaturas"]].copy()
            df_cs_s.columns = ["Sala","Día","Hora","N° secciones","IDs Asig.","Asignaturas"]
            st.dataframe(df_cs_s,use_container_width=True,hide_index=True)
            st.download_button("⬇️ Descargar Excel",to_xlsx(df_cs_s),"conflictos_sala.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── TAB 9: EFICIENCIA ────────────────────────────────────────────────────────
with tabs[8]:
    with guarded_tab("Eficiencia"):
        if label_periodo == "Anual 2026":
            c1,c2 = st.columns(2)
            for i,p in enumerate(periodos):
                ef_f = load_period(p).get("ef_fac",pd.DataFrame()).copy()
                if ef_f.empty:
                    [c1,c2][i].info("Sin datos de eficiencia.")
                    continue
                ef_f["Fac_corto"] = ef_f["FACULTAD"].map(FAC_SHORT).fillna(ef_f["FACULTAD"])
                per_lbl = "2026-01" if p=="202601" else "2026-02"
                ef_r = ef_f.groupby("Fac_corto").apply(
                    lambda x: (x["Registros"]*x["Ratio_prom"]).sum()/x["Registros"].sum()
                ).reset_index()
                ef_r.columns = ["Facultad","Ratio_prom"]; ef_r = ef_r.sort_values("Ratio_prom",ascending=True)
                fig_ef = px.bar(ef_r,x="Ratio_prom",y="Facultad",orientation="h",
                                color="Ratio_prom",color_continuous_scale=[[0,"#1e3a5f"],[0.7,GREEN],[1,RED]],
                                range_color=[0,120],text="Ratio_prom",title="Ratio eficiencia — "+per_lbl,
                                labels={"Ratio_prom":"Ratio (%)","Facultad":""})
                fig_ef.update_traces(texttemplate="%{text:.1f}%",textposition="outside",textfont=dict(color="#ffffff",size=11))
                fig_ef.add_vline(x=100,line_dash="dash",line_color=RED,line_width=1.5)
                dl(fig_ef,320); fig_ef.update_layout(coloraxis_showscale=False,xaxis_range=[0,135])
                [c1,c2][i].plotly_chart(fig_ef,use_container_width=True)
        else:
            p      = periodos[0]
            pdata  = load_period(p)
            ef_fac = pdata.get("ef_fac",pd.DataFrame()).copy()
            ef_ed  = pdata.get("ef_ed",pd.DataFrame()).copy()
            ef_det = pdata.get("ef_det",pd.DataFrame()).copy()
            df_opt = pdata.get("opt",pd.DataFrame()).copy()
            if ef_fac.empty:
                st.info("Sin datos de eficiencia para este período.")
            else:
                ef_fac["Fac_corto"] = ef_fac["FACULTAD"].map(FAC_SHORT).fillna(ef_fac["FACULTAD"])
                total_reg = ef_fac["Registros"].sum()
                muy_baja  = ef_fac[ef_fac["Categoria_eficiencia"]=="Muy baja (<30%)"]["Registros"].sum()
                exceso_ef = ef_fac[ef_fac["Categoria_eficiencia"]=="Óptima/Exceso (>90%)"]["Registros"].sum()
                e1,e2,e3 = st.columns(3)
                e1.metric("Total registros",              f"{total_reg:,}")
                e2.metric("Salas sobredimensionadas <30%",f"{muy_baja} ({round(muy_baja/total_reg*100,1) if total_reg else 0}%)")
                e3.metric("Uso óptimo/exceso >90%",       f"{exceso_ef} ({round(exceso_ef/total_reg*100,1) if total_reg else 0}%)")
                leg("<b>Ratio = Cupo / Capacidad × 100. Muy baja (<30%):</b> sala sobredimensionada.")
                facs_ef    = sorted(ef_fac["Fac_corto"].unique())
                sel_fac_ef = st.multiselect("🎓 Filtrar por facultad",facs_ef,key="fac_ef")
                ef_fac_f   = ef_fac[ef_fac["Fac_corto"].isin(sel_fac_ef)] if sel_fac_ef else ef_fac
                c1,c2 = st.columns(2)
                with c1:
                    cat_tot = ef_fac_f.groupby("Categoria_eficiencia")["Registros"].sum().reset_index()
                    fig_e1  = px.pie(cat_tot,values="Registros",names="Categoria_eficiencia",
                                     color_discrete_sequence=[RED,ORANGE,"#f1c40f",GREEN,CYAN])
                    dl(fig_e1,300); st.plotly_chart(fig_e1,use_container_width=True)
                with c2:
                    ef_r = ef_fac_f.groupby("Fac_corto").apply(
                        lambda x: (x["Registros"]*x["Ratio_prom"]).sum()/x["Registros"].sum()
                    ).reset_index()
                    ef_r.columns = ["Facultad","Ratio_prom"]; ef_r = ef_r.sort_values("Ratio_prom",ascending=True)
                    fig_e2 = px.bar(ef_r,x="Ratio_prom",y="Facultad",orientation="h",
                                    color="Ratio_prom",color_continuous_scale=[[0,"#1e3a5f"],[0.7,GREEN],[1,RED]],
                                    range_color=[0,120],text="Ratio_prom",labels={"Ratio_prom":"Ratio (%)","Facultad":""})
                    fig_e2.update_traces(texttemplate="%{text:.1f}%",textposition="outside",textfont=dict(color="#ffffff",size=12))
                    fig_e2.add_vline(x=100,line_dash="dash",line_color=RED,line_width=1.5)
                    dl(fig_e2,300); fig_e2.update_layout(coloraxis_showscale=False,xaxis_range=[0,135])
                    st.plotly_chart(fig_e2,use_container_width=True)
                if not ef_ed.empty:
                    ef_ed["Categoria_eficiencia"] = pd.Categorical(ef_ed["Categoria_eficiencia"],categories=EFCAT_ORDER,ordered=True)
                    fig_e3 = px.bar(ef_ed.sort_values("Categoria_eficiencia"),x="Registros",y="EDIFICIO",
                                    color="Categoria_eficiencia",orientation="h",barmode="stack",
                                    color_discrete_sequence=[RED,ORANGE,"#f1c40f",GREEN,CYAN],
                                    category_orders={"Categoria_eficiencia":EFCAT_ORDER},
                                    labels={"Registros":"N° clases","EDIFICIO":""})
                    dl(fig_e3,280); st.plotly_chart(fig_e3,use_container_width=True)
                    leg("<b>Eficiencia por edificio:</b> mucho rojo/naranja = salas demasiado grandes.")
                if not ef_det.empty:
                    st.markdown("#### Casos críticos")
                    ef_d = ef_det.copy()
                    ef_d["Edificio"] = ef_d["EDIFICIO"].map(ED_SHORT).fillna(ef_d["EDIFICIO"])
                    ef_d["Facultad"] = ef_d["FACULTAD"].map(FAC_SHORT).fillna(ef_d["FACULTAD"])
                    cat_f   = st.multiselect("Filtrar categoría",EFCAT_ORDER,default=["Muy baja (<30%)","Óptima/Exceso (>90%)"])
                    fac_ef2 = st.multiselect("Filtrar facultad",sorted(ef_d["Facultad"].unique()),key="fac_ef2")
                    ef_show = ef_d[["ID_ASIG","ASIGNATURA","SECCION","TIPO","Facultad","LUGAR","Edificio",
                                    "CUPO","CAPACIDAD","Ratio_uso","Categoria_eficiencia"]].copy()
                    ef_show.columns = ["ID Asig.","Asignatura","Secc.","Tipo","Facultad","Sala","Edificio",
                                       "Cupo","Cap.","Ratio %","Categoría"]
                    if cat_f:   ef_show = ef_show[ef_show["Categoría"].isin(cat_f)]
                    if fac_ef2: ef_show = ef_show[ef_show["Facultad"].isin(fac_ef2)]
                    st.dataframe(ef_show,use_container_width=True,hide_index=True)
                    st.download_button("⬇️ Descargar Excel",to_xlsx(ef_show),"eficiencia_critica.xlsx",
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                st.markdown("---")
                st.markdown("#### 🔄 Sugerencias de optimización de salas")
                if not df_opt.empty and "Asignatura" in df_opt.columns:
                    fac_opt    = st.multiselect("Filtrar por facultad",
                                                sorted(df_opt["Facultad"].unique()) if "Facultad" in df_opt.columns else [],key="fac_opt")
                    df_opt_show = df_opt.copy()
                    if "Facultad" in df_opt_show.columns:
                        df_opt_show["Facultad_c"] = df_opt_show["Facultad"].map(FAC_SHORT).fillna(df_opt_show["Facultad"])
                    else:
                        df_opt_show["Facultad_c"] = ""
                    if fac_opt: df_opt_show = df_opt_show[df_opt_show["Facultad_c"].isin(fac_opt)]
                    cols_opt = ["ID_Asig","Asignatura","Seccion","Tipo","Facultad_c","Edificio","Dia","Modulo",
                                "Sala_actual","Cap_actual","Cupo","Ratio_actual","Sala_sugerida","Cap_sugerida","Ratio_nuevo","Mejora_ratio"]
                    cols_exist = [c for c in cols_opt if c in df_opt_show.columns]
                    df_opt_disp = df_opt_show[cols_exist].rename(columns={
                        "ID_Asig":"ID Asig.","Seccion":"Secc.","Facultad_c":"Facultad","Dia":"Día","Modulo":"Mód.",
                        "Sala_actual":"Sala act.","Cap_actual":"Cap. act.","Ratio_actual":"Ratio act. %",
                        "Sala_sugerida":"Sala sug.","Cap_sugerida":"Cap. sug.","Ratio_nuevo":"Ratio nuevo %","Mejora_ratio":"Mejora %"
                    })
                    st.info(f"{len(df_opt_disp)} sugerencias de optimización")
                    st.dataframe(df_opt_disp,use_container_width=True,hide_index=True)
                    st.download_button("⬇️ Descargar Excel",to_xlsx(df_opt_disp),"optimizacion_salas.xlsx",
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.info("No hay sugerencias de optimización disponibles para este período.")

# ── TAB 10: CONCENTRACIÓN ────────────────────────────────────────────────────
with tabs[9]:
    with guarded_tab("Concentración"):
        if label_periodo == "Anual 2026":
            c1,c2 = st.columns(2)
            for i,p in enumerate(periodos):
                cm = load_period(p).get("conc_mod",pd.DataFrame()).copy()
                if cm.empty:
                    [c1,c2][i].info("Sin datos de concentración.")
                    continue
                cm_p = cm.dropna(subset=["MODULO"]).copy(); cm_p["ML"] = cm_p["MODULO"].astype(int).map(MODULOS)
                per_lbl = "2026-01" if p=="202601" else "2026-02"
                fig_cm = px.bar(cm_p,x="ML",y="Clases",color="Clases",
                                color_continuous_scale=[[0,"#1e3a5f"],[1,CYAN]],text="Clases",title=per_lbl)
                fig_cm.update_traces(textposition="outside",textfont=dict(color="#ffffff",size=11))
                dl(fig_cm,300); fig_cm.update_layout(coloraxis_showscale=False)
                [c1,c2][i].plotly_chart(fig_cm,use_container_width=True)
        else:
            p     = periodos[0]
            pdata = load_period(p)
            cm    = pdata.get("conc_mod",pd.DataFrame()).copy()
            cfm   = pdata.get("conc_fac_mod",pd.DataFrame()).copy()
            ct    = pdata.get("conc_turno",pd.DataFrame()).copy()
            if cm.empty:
                st.info("Sin datos de concentración.")
            else:
                if not cfm.empty:
                    cfm["Fac_corto"] = cfm["FACULTAD"].map(FAC_SHORT).fillna(cfm["FACULTAD"])
                if not ct.empty:
                    ct["Fac_corto"]  = ct["FACULTAD"].map(FAC_SHORT).fillna(ct["FACULTAD"])
                c1,c2 = st.columns(2)
                with c1:
                    cm_p = cm.dropna(subset=["MODULO"]).copy(); cm_p["ML"] = cm_p["MODULO"].astype(int).map(MODULOS)
                    fig_h1 = px.bar(cm_p,x="ML",y="Clases",color="Clases",
                                    color_continuous_scale=[[0,"#1e3a5f"],[1,CYAN]],text="Clases",
                                    labels={"ML":"","Clases":"N° clases"})
                    fig_h1.update_traces(textposition="outside",textfont=dict(color="#ffffff",size=12))
                    dl(fig_h1,300); fig_h1.update_layout(coloraxis_showscale=False)
                    st.plotly_chart(fig_h1,use_container_width=True)
                    leg("<b>Clases por módulo.</b>")
                with c2:
                    if not ct.empty:
                        fig_h2 = px.bar(ct,x="Clases",y="Fac_corto",color="TURNO",orientation="h",barmode="stack",
                                        color_discrete_map={"Diurno":CYAN,"Vespertino":ORANGE},
                                        labels={"Clases":"N° clases","Fac_corto":"","TURNO":"Turno"})
                        dl(fig_h2,300); st.plotly_chart(fig_h2,use_container_width=True)
                        leg("<b>Diurno vs vespertino.</b>")
                if not cfm.empty:
                    cfm_p = cfm.dropna(subset=["MODULO"]).copy(); cfm_p["ML"] = cfm_p["MODULO"].astype(int).map(MODULOS)
                    fig_h3 = px.bar(cfm_p,x="ML",y="Clases",color="Fac_corto",barmode="group",
                                    color_discrete_sequence=MULTI,labels={"ML":"","Clases":"N° clases","Fac_corto":"Facultad"})
                    dl(fig_h3,360); st.plotly_chart(fig_h3,use_container_width=True)
                    leg("<b>Clases por módulo y facultad.</b>")
                    hm2    = cfm_p.pivot_table(index="Fac_corto",columns="ML",values="Clases",fill_value=0)
                    fig_h4 = px.imshow(hm2,text_auto=True,
                                       color_continuous_scale=[[0,PLOT_BG],[0.3,"#1e3a5f"],[1,CYAN]],aspect="auto")
                    fig_h4.update_traces(textfont=dict(color="#ffffff",size=11)); fig_h4.update_xaxes(tickangle=-20); dl(fig_h4,300)
                    st.plotly_chart(fig_h4,use_container_width=True)
                    leg("<b>Heatmap de concentración:</b> celdas más claras = más clases en ese módulo.")

# ── TAB 11: RESERVAS ─────────────────────────────────────────────────────────
df_rev = load_rev()
with tabs[10]:
    with guarded_tab("Reservas"):
        if df_rev.empty:
            st.info("Sin datos de reservas disponibles.")
        else:
            r1,r2,r3,r4 = st.columns(4)
            with r1:
                ed_rv  = ["Todos"]+sorted(df_rev["Edificio"].dropna().unique().tolist())
                sel_er = st.selectbox("Edificio",ed_rv,key="ed_rev")
            with r2:
                dia_rv = ["Todos"]+sorted(df_rev["Dia"].dropna().unique().tolist())
                sel_dr = st.selectbox("Día",dia_rv,key="dia_rev")
            with r3:
                sel_tr = st.selectbox("Turno",["Todos","Diurno","Vespertino"],key="turno_rev")
            with r4:
                per_rv = ["Todos"]+sorted(df_rev["Periodo"].dropna().unique().tolist())
                sel_pr = st.selectbox("Período",per_rv,key="periodo_rev")
            busq_r = st.text_input("🔍 Buscar en sala o motivo",key="busq_rev")
            frv = df_rev.copy()
            if sel_er!="Todos": frv = frv[frv["Edificio"]==sel_er]
            if sel_dr!="Todos": frv = frv[frv["Dia"]==sel_dr]
            if sel_tr!="Todos": frv = frv[frv["Turno"]==sel_tr]
            if sel_pr!="Todos": frv = frv[frv["Periodo"]==sel_pr]
            if busq_r:
                safe_b = re.escape(busq_r.strip())
                frv = frv[
                    frv["Sala"].str.contains(safe_b,case=False,na=False,regex=True) |
                    frv["Motivo"].str.contains(safe_b,case=False,na=False,regex=True) |
                    frv["Descripcion"].str.contains(safe_b,case=False,na=False,regex=True)
                ]
            rv1,rv2,rv3,rv4 = st.columns(4)
            rv1.metric("Reservas",     len(frv))
            rv2.metric("Salas únicas", frv["Sala"].nunique())
            rv3.metric("Diurnas",      int((frv["Turno"]=="Diurno").sum()))
            rv4.metric("Vespertinas",  int((frv["Turno"]=="Vespertino").sum()))
            leg("<b>Reservas:</b> solicitudes puntuales fuera de la planificación semestral.")
            c1,c2 = st.columns(2)
            with c1:
                ce = frv["Edificio"].value_counts().reset_index(); ce.columns = ["Edificio","Reservas"]
                fig_r1 = px.bar(ce,x="Edificio",y="Reservas",color="Reservas",
                                color_continuous_scale=[[0,"#1e3a5f"],[1,CYAN]],text="Reservas")
                fig_r1.update_traces(textposition="outside",textfont=dict(color="#ffffff",size=12))
                dl(fig_r1,280); fig_r1.update_layout(coloraxis_showscale=False)
                st.plotly_chart(fig_r1,use_container_width=True)
            with c2:
                cd = (frv["Dia"].value_counts()
                      .reindex(["lunes","martes","miércoles","jueves","viernes","sábado"])
                      .dropna().reset_index())
                cd.columns = ["Dia","Reservas"]
                fig_r2 = px.bar(cd,x="Dia",y="Reservas",color="Reservas",
                                color_continuous_scale=[[0,"#1a1a3f"],[1,PURPLE]],text="Reservas")
                fig_r2.update_traces(textposition="outside",textfont=dict(color="#ffffff",size=12))
                dl(fig_r2,280); fig_r2.update_layout(coloraxis_showscale=False)
                st.plotly_chart(fig_r2,use_container_width=True)
            ts     = frv.groupby(["Sala","Edificio"]).size().reset_index(name="Reservas").sort_values("Reservas",ascending=False).head(15)
            fig_r3 = px.bar(ts,x="Reservas",y="Sala",orientation="h",color="Edificio",color_discrete_sequence=MULTI)
            dl(fig_r3,400); st.plotly_chart(fig_r3,use_container_width=True)
            leg("<b>Top 15 salas más reservadas.</b>")
            cs = ["Sala","Edificio","Dia","Fecha_Inicio","Fecha_Fin","Hora_Ini","Hora_Fin","Turno","Periodo","Motivo"]
            cs_exist = [c for c in cs if c in frv.columns]
            st.dataframe(frv[cs_exist].reset_index(drop=True),use_container_width=True,hide_index=True)
            st.download_button("⬇️ Descargar Excel",to_xlsx(frv[cs_exist]),"reservas.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── TAB 12: DETALLE SALAS ────────────────────────────────────────────────────
with tabs[11]:
    with guarded_tab("Detalle salas"):
        if fd.empty:
            st.info("Sin datos de detalle para el período seleccionado.")
        else:
            c1,c2,c3 = st.columns(3)
            with c1: sel4e = st.selectbox("Edificio",sel_ed if sel_ed else edificios_opts,key="ed4")
            with c2: sel4d = st.selectbox("Día",sel_dias if sel_dias else DIAS_ORDER,key="dia4")
            with c3: sel4m = st.selectbox("Módulo",sel_mods if sel_mods else list(MODULOS.keys()),
                                          format_func=lambda x: MODULOS_FULL[x],key="mod4")
            cupo_min = st.slider("Capacidad mínima",0,100,0)
            sel_tipo = st.multiselect("Tipo",["SALA DE CLASES","LABORATORIO DE COMPUTACION"],
                                      default=["SALA DE CLASES","LABORATORIO DE COMPUTACION"])
            fd4 = fd[
                (fd["Ed_corto"]==sel4e) & (fd["Dia"]==sel4d) & (fd["Modulo"]==sel4m) &
                (fd["Capacidad"].astype(int)>=cupo_min) & (fd["Tipo"].isin(sel_tipo))
            ][["Sala","Capacidad","Tipo","Salas_libres_bloque","Pct_Ocupacion"]].copy()
            fd4 = fd4.rename(columns={"Salas_libres_bloque":"Libres en bloque","Pct_Ocupacion":"% Ocup."})
            if not fd4.empty:
                st.success(f"✅ {len(fd4)} salas disponibles · {sel4e} · {sel4d} · {MODULOS_FULL[sel4m]}")
                st.dataframe(fd4,use_container_width=True,hide_index=True)
                leg("<b>Cómo usar:</b> selecciona edificio, día y módulo. Filtra por capacidad mínima según el cupo.")
                st.download_button("⬇️ Descargar Excel",to_xlsx(fd4),"salas_disponibles.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.warning("No hay salas libres con los filtros seleccionados.")
