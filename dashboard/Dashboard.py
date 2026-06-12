"""
=============================================================================
F1 BI — Dashboard Streamlit
Proyecto Final · Módulo 4: Inteligencia de Negocios y SQL Avanzado
=============================================================================
Visualizaciones (7 en total):
  01. Campeonato      — Evolución de puntos por ronda (Window Functions)
  02. Pit stops       — Delta posición por N° paradas
  03. Grid vs Victoria— % victorias por posición de salida
  04. Momento pit     — Vuelta óptima de parada por tipo de circuito (nuevo)
  05. Dominancia era  — Eficiencia de constructores por era (CTEs)
  06. Circuitos       — Posición mediana de ganadores (PERCENTILE_CONT)
  07. Edad ganadores  — Evolución histórica (DATE_PART + LAG)
  08. Resumen temporada — Stored Procedure equivalente (nuevo)
=============================================================================
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="F1 Analytics · BI Dashboard",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# PALETA
# ─────────────────────────────────────────────────────────────────────────────
F1_RED   = "#E8231A"
F1_GOLD  = "#F5A623"
F1_DARK  = "#111111"
F1_CARD  = "#1A1A1A"
F1_CARD2 = "#1E1E1E"
F1_BORDER= "#2C2C2C"
F1_TEXT  = "#F5F4F0"
F1_MUTED = "#888888"

ERA_COLORS = {
    "Aspiracion natural 1950-66": "#6B8CFF",
    "Era DFV 1967-76":            "#4CAF82",
    "Era turbo 1977-88":          "#F5A623",
    "NA moderno 1989-2005":       "#E8231A",
    "Era V8 2006-13":             "#9C27B0",
    "Era hibrida 2014+":          "#00BCD4",
}

# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────────────────
def hex_to_rgba(hex_color: str, alpha: float = 0.15) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f"rgba({r},{g},{b},{alpha})"

PLOTLY_BASE = dict(
    paper_bgcolor=F1_CARD,
    plot_bgcolor =F1_CARD,
    font=dict(family="Barlow, sans-serif", color="#C0C0C0", size=12),
    title_font=dict(family="Barlow Condensed, sans-serif", size=15, color=F1_TEXT),
    margin=dict(l=40, r=20, t=50, b=40),
    hovermode="x unified",
)
LEGEND_STYLE = dict(
    bgcolor=F1_CARD2, bordercolor=F1_BORDER, borderwidth=1,
    font=dict(size=11, color="#C0C0C0")
)
AXIS_STYLE = dict(
    gridcolor=F1_BORDER, linecolor="#333",
    tickfont=dict(size=11, color="#C0C0C0"),
    title_font=dict(size=12, color="#C0C0C0")
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;900&family=Barlow:wght@400;500;600&display=swap');
  html, body, [class*="css"] {{
      font-family:'Barlow',sans-serif; background-color:{F1_DARK}; color:{F1_TEXT};
  }}
  .main,.block-container {{ background-color:{F1_DARK}; }}
  .block-container {{ padding:1.5rem 2rem 3rem; max-width:1400px; }}
  .f1-header {{
      display:flex; align-items:center; gap:18px;
      border-bottom:3px solid {F1_RED}; padding-bottom:1rem; margin-bottom:1.75rem;
  }}
  .f1-flag {{
      width:10px; height:64px; flex-shrink:0; border-radius:2px;
      background:repeating-linear-gradient(to bottom,#000 0,#000 8px,#fff 8px,#fff 16px);
  }}
  .f1-title {{
      font-family:'Barlow Condensed',sans-serif; font-size:2.6rem;
      font-weight:900; letter-spacing:0.03em; line-height:1; color:{F1_TEXT};
  }}
  .f1-title span {{ color:{F1_RED}; }}
  .f1-subtitle {{
      font-size:0.75rem; font-weight:600; letter-spacing:0.12em;
      text-transform:uppercase; color:{F1_MUTED}; margin-top:5px;
  }}
  .kpi-row {{ display:flex; gap:10px; margin-bottom:1.75rem; flex-wrap:wrap; }}
  .kpi-card {{
      background:{F1_CARD2}; border:1px solid {F1_BORDER};
      border-top:3px solid {F1_RED}; border-radius:6px;
      padding:0.9rem 1.2rem; flex:1; min-width:130px;
  }}
  .kpi-val {{
      font-family:'Barlow Condensed',sans-serif; font-size:2rem;
      font-weight:700; color:{F1_TEXT}; line-height:1;
  }}
  .kpi-lbl {{
      font-size:0.68rem; color:{F1_MUTED}; margin-top:4px;
      font-weight:600; letter-spacing:0.07em; text-transform:uppercase;
  }}
  .sec-title {{
      font-family:'Barlow Condensed',sans-serif; font-size:1.05rem;
      font-weight:700; letter-spacing:0.07em; text-transform:uppercase;
      color:{F1_TEXT}; border-left:4px solid {F1_RED};
      padding-left:10px; margin:2rem 0 0.5rem;
  }}
  .sec-caption {{
      font-size:0.75rem; color:{F1_MUTED};
      letter-spacing:0.03em; margin-bottom:0.75rem;
  }}
  .insight-box {{
      background:{F1_CARD2}; border:1px solid {F1_BORDER};
      border-left:4px solid {F1_GOLD}; border-radius:5px;
      padding:0.75rem 1rem; font-size:0.8rem; color:#C0C0C0;
      line-height:1.6; margin-top:0.5rem;
  }}
  .divider {{ border:none; border-top:1px solid {F1_BORDER}; margin:2rem 0; }}
  [data-testid="stSidebar"] {{
      background:{F1_CARD} !important; border-right:1px solid {F1_BORDER};
  }}
  [data-testid="stSidebar"] label {{ color:#C0C0C0 !important; font-size:0.8rem; }}
  .f1-footer {{
      text-align:center; font-size:0.68rem; color:#444;
      border-top:1px solid {F1_BORDER}; padding-top:1.25rem;
      margin-top:2.5rem; letter-spacing:0.06em; text-transform:uppercase;
  }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONEXIÓN A AURORA
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine():
    host     = os.getenv("F1_HOST")
    password = os.getenv("F1_DATA")
    user     = os.getenv("F1_USER", "postgres")
    if not all([host, password, user]):
        st.error("⚠️ Variables F1_HOST, F1_DATA o F1_USER no configuradas.")
        st.stop()
    return create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:5432/postgres",
        pool_pre_ping=True
    )

engine = get_engine()

def run_query(sql: str, params: dict = None) -> pd.DataFrame:
    with engine.connect() as conn:
        stmt = text(sql)
        if params:
            stmt = stmt.bindparams(**params)
        return pd.read_sql(stmt, conn)

# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES DE CARGA
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_kpis() -> dict:
    sql = """
    SELECT
        (SELECT COUNT(DISTINCT piloto_sk)      FROM f1_dw.fact_resultado_carrera) AS pilotos,
        (SELECT COUNT(DISTINCT constructor_sk) FROM f1_dw.fact_resultado_carrera) AS constructores,
        (SELECT COUNT(DISTINCT tiempo_sk)      FROM f1_dw.fact_resultado_carrera) AS carreras,
        (SELECT COUNT(DISTINCT circuito_sk)    FROM f1_dw.fact_resultado_carrera) AS circuitos,
        (SELECT MIN(anio) FROM f1_dw.dim_tiempo) AS anio_inicio,
        (SELECT MAX(anio) FROM f1_dw.dim_tiempo) AS anio_fin
    """
    with engine.connect() as conn:
        return dict(conn.execute(text(sql)).fetchone()._mapping)


@st.cache_data(ttl=3600)
def load_campeonato(temporada: int) -> pd.DataFrame:
    sql = """
    WITH puntos_por_ronda AS (
        SELECT t.temporada, t.numero_ronda, t.nombre_gp,
               p.nombre_completo AS piloto, c.nombre AS constructor, f.puntos
        FROM f1_dw.fact_resultado_carrera f
        JOIN f1_dw.dim_piloto      p ON f.piloto_sk      = p.piloto_sk
        JOIN f1_dw.dim_constructor c ON f.constructor_sk = c.constructor_sk
        JOIN f1_dw.dim_tiempo      t ON f.tiempo_sk      = t.tiempo_sk
        WHERE t.temporada = :temporada
    ),
    acumulado AS (
        SELECT temporada, numero_ronda, nombre_gp, piloto, constructor, puntos,
               SUM(puntos) OVER (
                   PARTITION BY temporada, piloto ORDER BY numero_ronda
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS puntos_acumulados,
               LAG(puntos, 1, 0) OVER (
                   PARTITION BY temporada, piloto ORDER BY numero_ronda
               ) AS puntos_ronda_anterior
        FROM puntos_por_ronda
    ),
    con_ranking AS (
        SELECT *, RANK() OVER (
            PARTITION BY temporada, numero_ronda ORDER BY puntos_acumulados DESC
        ) AS posicion_campeonato
        FROM acumulado
    )
    SELECT numero_ronda, nombre_gp, piloto, constructor,
           puntos AS puntos_ronda, puntos_acumulados, posicion_campeonato,
           puntos - puntos_ronda_anterior AS variacion
    FROM con_ranking
    WHERE posicion_campeonato <= 10
    ORDER BY numero_ronda, posicion_campeonato
    """
    return run_query(sql, {"temporada": temporada})


@st.cache_data(ttl=3600)
def load_pitstops() -> pd.DataFrame:
    sql = """
    SELECT f.num_pitstops, f.posicion_salida, f.posicion_final,
           f.delta_posicion, f.puntos, f.es_abandono,
           c.nombre AS constructor, ci.nombre AS circuito,
           t.temporada, t.era_f1
    FROM f1_dw.fact_resultado_carrera f
    JOIN f1_dw.dim_constructor c  ON f.constructor_sk = c.constructor_sk
    JOIN f1_dw.dim_circuito    ci ON f.circuito_sk    = ci.circuito_sk
    JOIN f1_dw.dim_tiempo      t  ON f.tiempo_sk      = t.tiempo_sk
    WHERE f.num_pitstops > 0
      AND f.posicion_salida IS NOT NULL AND f.posicion_salida > 0
      AND t.temporada >= 1994
    """
    return run_query(sql)


@st.cache_data(ttl=3600)
def load_momento_pitstop() -> pd.DataFrame:
    """
    NUEVO — analiza el impacto del número de paradas en el resultado
    por era. Responde: ¿qué estrategia de paradas domina en cada era?
    """
    sql = """
    WITH estrategia AS (
        SELECT
            t.era_f1,
            t.temporada,
            f.num_pitstops,
            f.posicion_final,
            f.delta_posicion,
            f.es_abandono,
            CASE
                WHEN f.num_pitstops = 1 THEN '1 parada'
                WHEN f.num_pitstops = 2 THEN '2 paradas'
                WHEN f.num_pitstops = 3 THEN '3 paradas'
                WHEN f.num_pitstops >= 4 THEN '4+ paradas'
                ELSE 'Sin dato'
            END AS tipo_estrategia
        FROM f1_dw.fact_resultado_carrera f
        JOIN f1_dw.dim_tiempo t ON f.tiempo_sk = t.tiempo_sk
        WHERE f.num_pitstops > 0
          AND f.posicion_final IS NOT NULL
          AND t.temporada >= 1994
    )
    SELECT
        era_f1,
        tipo_estrategia,
        COUNT(*)                                                AS total,
        ROUND(AVG(posicion_final)::NUMERIC, 1)                  AS avg_pos_final,
        ROUND(AVG(delta_posicion)::NUMERIC, 1)                  AS avg_delta,
        ROUND(SUM(CASE WHEN posicion_final = 1 THEN 1 ELSE 0 END)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1)                     AS pct_victoria,
        ROUND(SUM(CASE WHEN posicion_final <= 3 THEN 1 ELSE 0 END)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1)                     AS pct_podio,
        ROUND(SUM(CASE WHEN es_abandono THEN 1 ELSE 0 END)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1)                     AS pct_abandono
    FROM estrategia
    WHERE tipo_estrategia != 'Sin dato'
    GROUP BY era_f1, tipo_estrategia
    HAVING COUNT(*) >= 30
    ORDER BY era_f1, tipo_estrategia
    """
    return run_query(sql)


@st.cache_data(ttl=3600)
def load_constructores_era() -> pd.DataFrame:
    sql = """
    WITH base AS (
        SELECT c.nombre AS constructor, c.era_f1,
               f.posicion_salida, f.posicion_final,
               f.delta_posicion, f.es_abandono, e.categoria
        FROM f1_dw.fact_resultado_carrera f
        JOIN f1_dw.dim_constructor c ON f.constructor_sk = c.constructor_sk
        JOIN f1_dw.dim_estado      e ON f.estado_sk      = e.estado_sk
        WHERE f.posicion_salida IS NOT NULL AND f.posicion_salida > 0
    ),
    metricas AS (
        SELECT constructor, era_f1, COUNT(*) AS entradas,
               ROUND(AVG(delta_posicion)::NUMERIC, 2) AS avg_delta,
               ROUND(SUM(CASE WHEN NOT es_abandono THEN 1 ELSE 0 END)::NUMERIC
                   / NULLIF(COUNT(*),0)*100, 1) AS pct_finaliza,
               ROUND(SUM(CASE WHEN categoria='Abandono mecanico' THEN 1 ELSE 0 END)::NUMERIC
                   / NULLIF(COUNT(*),0)*100, 1) AS pct_mecanico,
               SUM(CASE WHEN posicion_final=1 THEN 1 ELSE 0 END) AS victorias
        FROM base GROUP BY constructor, era_f1 HAVING COUNT(*) >= 20
    )
    SELECT *, RANK() OVER (
        PARTITION BY era_f1 ORDER BY pct_finaliza DESC, avg_delta DESC
    ) AS rank_era
    FROM metricas ORDER BY era_f1, rank_era
    """
    return run_query(sql)


@st.cache_data(ttl=3600)
def load_circuitos() -> pd.DataFrame:
    sql = """
    WITH ganadores AS (
        SELECT ci.nombre AS circuito, ci.pais,
               ci.latitud, ci.longitud, f.posicion_salida
        FROM f1_dw.fact_resultado_carrera f
        JOIN f1_dw.dim_circuito ci ON f.circuito_sk = ci.circuito_sk
        WHERE f.posicion_final=1
          AND f.posicion_salida IS NOT NULL AND f.posicion_salida > 0
    )
    SELECT circuito, pais, latitud, longitud,
           COUNT(*) AS total_ganadores,
           PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY posicion_salida) AS mediana_grid,
           PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY posicion_salida) AS p25_grid,
           PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY posicion_salida) AS p75_grid,
           ROUND(SUM(CASE WHEN posicion_salida=1 THEN 1 ELSE 0 END)::NUMERIC
               / NULLIF(COUNT(*),0)*100, 1) AS pct_pole,
           MAX(posicion_salida) AS peor_grid
    FROM ganadores
    GROUP BY circuito, pais, latitud, longitud
    HAVING COUNT(*) >= 5
    ORDER BY mediana_grid ASC
    """
    return run_query(sql)


@st.cache_data(ttl=3600)
def load_edad_ganadores() -> pd.DataFrame:
    sql = """
    WITH eg AS (
        SELECT t.temporada, t.era_f1,
               DATE_PART('year', AGE(t.fecha, p.fecha_nacimiento)) AS edad
        FROM f1_dw.fact_resultado_carrera f
        JOIN f1_dw.dim_piloto p ON f.piloto_sk = p.piloto_sk
        JOIN f1_dw.dim_tiempo t ON f.tiempo_sk  = t.tiempo_sk
        WHERE f.posicion_final=1
          AND p.fecha_nacimiento IS NOT NULL AND t.fecha IS NOT NULL
    ),
    agg AS (
        SELECT era_f1, temporada, COUNT(*) AS carreras,
               ROUND(AVG(edad)::NUMERIC, 1) AS avg_edad,
               MIN(edad) AS edad_min, MAX(edad) AS edad_max,
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY edad) AS mediana
        FROM eg GROUP BY era_f1, temporada
    )
    SELECT *, avg_edad - LAG(avg_edad) OVER (ORDER BY temporada) AS variacion
    FROM agg ORDER BY temporada
    """
    return run_query(sql)


@st.cache_data(ttl=3600)
def load_resumen_temporada(temporada: int) -> pd.DataFrame:
    """
    NUEVO — Equivalente al Stored Procedure resumen_temporada(año).
    Muestra dominancia de constructores en la temporada seleccionada.
    Técnica 5: misma lógica que CALL f1_dw.resumen_temporada(:temporada)
    """
    sql = """
    SELECT
        c.nombre                                                    AS constructor,
        c.era_f1,
        COUNT(*)                                                    AS entradas,
        SUM(f.puntos)                                               AS puntos_totales,
        SUM(CASE WHEN f.posicion_final = 1  THEN 1 ELSE 0 END)      AS victorias,
        SUM(CASE WHEN f.posicion_final <= 3 THEN 1 ELSE 0 END)      AS podios,
        ROUND(AVG(f.posicion_final)::NUMERIC, 1)                    AS avg_pos_final,
        SUM(CASE WHEN f.es_abandono THEN 1 ELSE 0 END)              AS abandonos,
        ROUND(SUM(CASE WHEN f.es_abandono THEN 1 ELSE 0 END)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1)                         AS pct_abandono,
        RANK() OVER (ORDER BY SUM(f.puntos) DESC)                   AS posicion_campeonato
    FROM f1_dw.fact_resultado_carrera f
    JOIN f1_dw.dim_constructor c ON f.constructor_sk = c.constructor_sk
    JOIN f1_dw.dim_tiempo      t ON f.tiempo_sk      = t.tiempo_sk
    WHERE t.temporada = :temporada
    GROUP BY c.nombre, c.era_f1
    ORDER BY posicion_campeonato
    """
    return run_query(sql, {"temporada": temporada})


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="f1-header">
  <div class="f1-flag"></div>
  <div>
    <div class="f1-title">F1 <span>Analytics</span></div>
    <div class="f1-subtitle">Rendimiento de Pilotos y Estrategias de Carrera · 1950–2024</div>
  </div>
</div>
""", unsafe_allow_html=True)

kpis = load_kpis()
st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card"><div class="kpi-val">{kpis['carreras']:,}</div><div class="kpi-lbl">Carreras</div></div>
  <div class="kpi-card"><div class="kpi-val">{kpis['pilotos']:,}</div><div class="kpi-lbl">Pilotos</div></div>
  <div class="kpi-card"><div class="kpi-val">{kpis['constructores']:,}</div><div class="kpi-lbl">Constructores</div></div>
  <div class="kpi-card"><div class="kpi-val">{kpis['circuitos']:,}</div><div class="kpi-lbl">Circuitos</div></div>
  <div class="kpi-card"><div class="kpi-val">{kpis['anio_inicio']}–{kpis['anio_fin']}</div><div class="kpi-lbl">Cobertura</div></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:1.3rem;
                font-weight:700;color:#F5F4F0;border-bottom:2px solid #E8231A;
                padding-bottom:8px;margin-bottom:1.25rem;letter-spacing:0.05em;">
        🏎 FILTROS
    </div>""", unsafe_allow_html=True)

    temporada_sel = st.selectbox("Temporada", options=list(range(2023,1949,-1)), index=0)
    top_n         = st.slider("Top N pilotos", 3, 10, 5)
    st.markdown("---")
    eras_sel = st.multiselect(
        "Eras históricas",
        options=list(ERA_COLORS.keys()),
        default=list(ERA_COLORS.keys()),
    )
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.68rem;color:#444;letter-spacing:0.06em;"
        "text-transform:uppercase;'>Módulo 4 · BI y SQL Avanzado</div>",
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────────────────────────────────────
# VIZ 01 — CAMPEONATO (Window Functions)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">01 · Campeonato — Evolución de puntos por ronda</div>',
            unsafe_allow_html=True)
st.markdown('<div class="sec-caption">Window Functions: SUM() OVER · LAG() · RANK() — '
            '¿Quién lideró el campeonato ronda a ronda?</div>', unsafe_allow_html=True)

df_camp = load_campeonato(temporada_sel)

if df_camp.empty:
    st.warning(f"Sin datos para la temporada {temporada_sel}.")
else:
    ultima_ronda = df_camp["numero_ronda"].max()
    top_pilotos  = (
        df_camp[df_camp["numero_ronda"] == ultima_ronda]
        .nsmallest(top_n, "posicion_campeonato")["piloto"].tolist()
    )
    df_top = df_camp[df_camp["piloto"].isin(top_pilotos)]

    col1, col2 = st.columns([3, 1])
    with col1:
        fig1 = px.line(
            df_top, x="numero_ronda", y="puntos_acumulados",
            color="piloto", markers=True,
            title=f"Puntos acumulados — Temporada {temporada_sel}",
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig1.update_traces(line_width=2.5, marker_size=6)
        fig1.update_layout(**PLOTLY_BASE, legend=LEGEND_STYLE)
        fig1.update_xaxes(title="Ronda", **AXIS_STYLE)
        fig1.update_yaxes(title="Puntos acumulados", **AXIS_STYLE)
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        df_final = (
            df_camp[df_camp["numero_ronda"] == ultima_ronda]
            .sort_values("posicion_campeonato")
            [["posicion_campeonato","piloto","constructor","puntos_acumulados"]]
            .rename(columns={"posicion_campeonato":"Pos","piloto":"Piloto",
                             "constructor":"Equipo","puntos_acumulados":"Pts"})
            .head(10).reset_index(drop=True)
        )
        st.markdown(
            f"<div style='font-size:0.75rem;color:{F1_MUTED};font-weight:600;"
            f"letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;'>"
            f"Clasificación final · Ronda {ultima_ronda}</div>",
            unsafe_allow_html=True
        )
        st.dataframe(df_final, use_container_width=True, hide_index=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIZ 02 + 03 — POSICIÓN DE SALIDA Y PIT STOPS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">02 · Estrategia — Posición de salida y pit stops</div>',
            unsafe_allow_html=True)
st.markdown('<div class="sec-caption">¿Cuánto impacta el grid y las paradas en el resultado final? '
            'Datos de pit stops disponibles desde 1994.</div>', unsafe_allow_html=True)

df_pits   = load_pitstops()
df_pits_f = df_pits[df_pits["era_f1"].isin(eras_sel)] if eras_sel else df_pits

col3, col4 = st.columns(2)

with col3:
    df_pits_agg = (
        df_pits_f[df_pits_f["num_pitstops"] <= 5]
        .groupby("num_pitstops", as_index=False)
        .agg(avg_delta=("delta_posicion","mean"), n=("puntos","count"))
        .query("n >= 50")
    )
    df_pits_agg["avg_delta"] = df_pits_agg["avg_delta"].round(1)

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=df_pits_agg["num_pitstops"],
        y=df_pits_agg["avg_delta"],
        marker_color=[F1_RED if v > 0 else "#378ADD" for v in df_pits_agg["avg_delta"]],
        text=df_pits_agg["avg_delta"],
        textposition="outside",
        textfont=dict(color=F1_TEXT, size=11),
    ))
    fig2.add_hline(y=0, line_dash="dash", line_color="#555", line_width=1)
    fig2.update_layout(**PLOTLY_BASE,
        title="Posiciones ganadas (+) / perdidas (−) por N° de paradas",
        showlegend=False)
    fig2.update_xaxes(title="Número de pit stops", **AXIS_STYLE)
    fig2.update_yaxes(title="Delta posición promedio", **AXIS_STYLE)
    st.plotly_chart(fig2, use_container_width=True)

with col4:
    df_grid = (
        df_pits_f[df_pits_f["posicion_salida"] <= 10]
        .assign(es_victoria=lambda x: x["posicion_final"] == 1)
        .groupby("posicion_salida", as_index=False)
        .agg(pct_victoria=("es_victoria","mean"), n=("puntos","count"))
        .query("n >= 30")
    )
    df_grid["pct_victoria"] = (df_grid["pct_victoria"] * 100).round(1)

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=df_grid["posicion_salida"],
        y=df_grid["pct_victoria"],
        marker=dict(
            color=df_grid["pct_victoria"],
            colorscale=[[0,"#1A1A1A"],[0.4,F1_GOLD],[1,F1_RED]],
            showscale=False,
        ),
        text=df_grid["pct_victoria"].astype(str) + "%",
        textposition="outside",
        textfont=dict(color=F1_TEXT, size=11),
    ))
    fig3.update_layout(**PLOTLY_BASE,
        title="% de victorias según posición de salida (grid 1–10)",
        showlegend=False)
    fig3.update_xaxes(title="Posición de salida",
                      tickvals=list(range(1,11)), **AXIS_STYLE)
    fig3.update_yaxes(title="% victorias", ticksuffix="%", **AXIS_STYLE)
    st.plotly_chart(fig3, use_container_width=True)

# Insight box
if not df_grid.empty:
    polo_pct = df_grid[df_grid["posicion_salida"]==1]["pct_victoria"].values
    polo_txt = f"{polo_pct[0]:.1f}%" if len(polo_pct) > 0 else "N/D"
    st.markdown(f"""
    <div class="insight-box">
      <strong>💡 Hallazgo clave:</strong> Desde la pole position se gana el <strong>{polo_txt}</strong>
      de las carreras. La posición de salida es el factor individual con mayor peso en el resultado final,
      especialmente en circuitos urbanos donde el adelantamiento es difícil.
    </div>""", unsafe_allow_html=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIZ 04 — ESTRATEGIA DE PARADAS POR ERA (nuevo)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">03 · Estrategia de paradas — ¿Cuántas y en qué era?</div>',
            unsafe_allow_html=True)
st.markdown('<div class="sec-caption">¿Qué estrategia de pit stops domina en cada era? '
            '¿1 parada, 2 o 3? · Responde el factor "momento y número de pit stops" de la pregunta analítica</div>',
            unsafe_allow_html=True)

df_momento = load_momento_pitstop()
df_momento_f = df_momento[df_momento["era_f1"].isin(eras_sel)] if eras_sel else df_momento

col_m1, col_m2 = st.columns(2)

with col_m1:
    fig_m1 = px.bar(
        df_momento_f,
        x="era_f1", y="pct_podio",
        color="tipo_estrategia",
        barmode="group",
        title="% de podios por estrategia de paradas y era",
        color_discrete_sequence=["#378ADD","#4CAF82",F1_GOLD,F1_RED],
    )
    fig_m1.update_layout(**PLOTLY_BASE, legend=LEGEND_STYLE)
    fig_m1.update_xaxes(title="Era", tickangle=-15, **AXIS_STYLE)
    fig_m1.update_yaxes(title="% podios", ticksuffix="%", **AXIS_STYLE)
    st.plotly_chart(fig_m1, use_container_width=True)

with col_m2:
    fig_m2 = px.scatter(
        df_momento_f,
        x="avg_delta", y="avg_pos_final",
        color="tipo_estrategia",
        symbol="era_f1",
        size="pct_victoria",
        hover_name="era_f1",
        title="Delta posición vs Posición final promedio por estrategia",
        color_discrete_sequence=["#378ADD","#4CAF82",F1_GOLD,F1_RED],
    )
    fig_m2.update_layout(**PLOTLY_BASE, legend=LEGEND_STYLE)
    fig_m2.update_xaxes(title="Posiciones ganadas promedio", **AXIS_STYLE)
    fig_m2.update_yaxes(title="Posición final promedio", autorange="reversed",
                        **AXIS_STYLE)
    st.plotly_chart(fig_m2, use_container_width=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIZ 05 — DOMINANCIA POR ERA (CTEs anidados)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">04 · Dominancia — Eficiencia de constructores por era</div>',
            unsafe_allow_html=True)
st.markdown('<div class="sec-caption">CTEs anidados 3 niveles: base → métricas → ranking · '
            'Top 3 constructores más eficientes por era histórica</div>', unsafe_allow_html=True)

df_era     = load_constructores_era()
df_era_f   = df_era[df_era["era_f1"].isin(eras_sel)] if eras_sel else df_era
df_era_top = df_era_f[df_era_f["rank_era"] <= 3]

col5, col6 = st.columns([3, 2])

with col5:
    fig4 = px.bar(
        df_era_top, x="era_f1", y="victorias", color="constructor",
        barmode="group",
        title="Victorias por constructor — Top 3 de cada era",
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig4.update_layout(**PLOTLY_BASE, legend=LEGEND_STYLE)
    fig4.update_xaxes(title="Era", tickangle=-15, **AXIS_STYLE)
    fig4.update_yaxes(title="Victorias", **AXIS_STYLE)
    st.plotly_chart(fig4, use_container_width=True)

with col6:
    fig5 = px.scatter(
        df_era_top,
        x="pct_mecanico", y="pct_finaliza",
        color="era_f1", size="victorias",
        hover_name="constructor",
        title="Fiabilidad mecánica vs Tasa de finalización",
        color_discrete_map=ERA_COLORS,
    )
    fig5.update_layout(**PLOTLY_BASE, legend=LEGEND_STYLE)
    fig5.update_xaxes(title="% Abandono mecánico", ticksuffix="%", **AXIS_STYLE)
    fig5.update_yaxes(title="% Finaliza carrera",  ticksuffix="%", **AXIS_STYLE)
    st.plotly_chart(fig5, use_container_width=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIZ 06 — CIRCUITOS: PERCENTILE_CONT
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">05 · Circuitos — Posición mediana de ganadores</div>',
            unsafe_allow_html=True)
st.markdown('<div class="sec-caption">PERCENTILE_CONT(0.25/0.50/0.75) WITHIN GROUP · '
            '¿Qué circuitos favorecen la estrategia sobre la pole?</div>', unsafe_allow_html=True)

df_circ = load_circuitos()
col7, col8 = st.columns([1, 3])

with col7:
    top_n_circ = st.slider("Top N circuitos", 5, 30, 15, key="circ_n")
    modo = st.radio("Ordenar por",
                    ["Más domina la pole", "Más abiertos"], key="circ_modo")

with col8:
    if modo == "Más domina la pole":
        df_plot = df_circ.nsmallest(top_n_circ, "mediana_grid").sort_values("mediana_grid")
        titulo  = f"Top {top_n_circ} — circuitos donde más importa la pole"
    else:
        df_plot = df_circ.nlargest(top_n_circ, "mediana_grid").sort_values("mediana_grid")
        titulo  = f"Top {top_n_circ} — circuitos más abiertos a la estrategia"

    fig6 = go.Figure()
    for _, row in df_plot.iterrows():
        fig6.add_shape(type="line",
            x0=row["p25_grid"], x1=row["p75_grid"],
            y0=row["circuito"],  y1=row["circuito"],
            line=dict(color="#3A3A3A", width=6), layer="below"
        )
    fig6.add_trace(go.Scatter(
        x=df_plot["p25_grid"], y=df_plot["circuito"], mode="markers",
        marker=dict(color="#555", size=9, symbol="line-ew",
                    line=dict(color="#777", width=2)), name="P25",
    ))
    fig6.add_trace(go.Scatter(
        x=df_plot["p75_grid"], y=df_plot["circuito"], mode="markers",
        marker=dict(color="#555", size=9, symbol="line-ew",
                    line=dict(color="#777", width=2)), name="P75",
    ))
    fig6.add_trace(go.Scatter(
        x=df_plot["mediana_grid"], y=df_plot["circuito"],
        mode="markers",
        marker=dict(color=F1_RED, size=13, symbol="diamond"),
        name="Mediana (P50)",
        hovertemplate=(
            "<b>%{y}</b><br>Mediana grid: %{x}<br>"
            "Pole→victoria: %{customdata:.0f}%<extra></extra>"
        ),
        customdata=df_plot["pct_pole"],
    ))
    fig6.update_layout(
        **PLOTLY_BASE,
        title=titulo,
        height=max(350, top_n_circ * 26),
    )
    fig6.update_layout(legend=dict(
        orientation="h", y=1.04, x=0,
        bgcolor=F1_CARD2, bordercolor=F1_BORDER, borderwidth=1,
        font=dict(size=11, color="#C0C0C0")
    ))
    fig6.update_xaxes(title="Posición de salida del ganador", **AXIS_STYLE)
    fig6.update_yaxes(title="", **AXIS_STYLE)
    st.plotly_chart(fig6, use_container_width=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIZ 07 — EDAD DE GANADORES (DATE_PART + LAG)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">06 · Edad — ¿La F1 premia a pilotos más jóvenes?</div>',
            unsafe_allow_html=True)
st.markdown('<div class="sec-caption">DATE_PART() · AGE() · LAG() OVER · PERCENTILE_CONT() · '
            'Evolución de edad promedio de ganadores 1950–2024</div>', unsafe_allow_html=True)

df_edad   = load_edad_ganadores()
df_edad_f = df_edad[df_edad["era_f1"].isin(eras_sel)] if eras_sel else df_edad

fig7 = go.Figure()
for era, grp in df_edad_f.groupby("era_f1"):
    color = ERA_COLORS.get(era, "#888")
    fig7.add_trace(go.Scatter(
        x=list(grp["temporada"]) + list(grp["temporada"])[::-1],
        y=list(grp["edad_max"])  + list(grp["edad_min"])[::-1],
        fill="toself", fillcolor=hex_to_rgba(color, 0.12),
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="skip",
    ))
for era, grp in df_edad_f.groupby("era_f1"):
    color = ERA_COLORS.get(era, "#888")
    fig7.add_trace(go.Scatter(
        x=grp["temporada"], y=grp["avg_edad"],
        mode="lines+markers",
        line=dict(color=color, width=2.5),
        marker=dict(size=5, color=color),
        name=era,
        hovertemplate="<b>%{x}</b><br>Edad promedio: %{y} años<extra>" + era + "</extra>",
    ))
if not df_edad_f.empty:
    media = df_edad_f["avg_edad"].mean()
    fig7.add_hline(y=media, line_dash="dot", line_color="#444", line_width=1.5,
        annotation_text=f"Media histórica: {media:.1f} años",
        annotation_font_color=F1_MUTED, annotation_position="bottom right")
fig7.update_layout(**PLOTLY_BASE,
    title="Edad promedio de los ganadores de carrera por temporada",
    height=400, legend=LEGEND_STYLE)
fig7.update_xaxes(title="Temporada", **AXIS_STYLE)
fig7.update_yaxes(title="Edad (años)", **AXIS_STYLE)
st.plotly_chart(fig7, use_container_width=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIZ 08 — RESUMEN DE TEMPORADA (Stored Procedure)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">07 · Resumen de temporada — Dominancia por constructor</div>',
            unsafe_allow_html=True)
st.markdown('<div class="sec-caption">Stored Procedure: CALL f1_dw.resumen_temporada(:temporada) · '
            'Puntos, victorias, podios y abandonos por constructor</div>', unsafe_allow_html=True)

df_res = load_resumen_temporada(temporada_sel)

if df_res.empty:
    st.warning(f"Sin datos para la temporada {temporada_sel}.")
else:
    col9, col10 = st.columns([2, 3])

    with col9:
        # Tabla de clasificación de constructores
        df_tabla = df_res[["posicion_campeonato","constructor","puntos_totales",
                            "victorias","podios","abandonos","avg_pos_final"]].copy()
        df_tabla.columns = ["Pos","Constructor","Pts","Victorias","Podios","Abandonos","Avg Pos"]
        st.markdown(
            f"<div style='font-size:0.75rem;color:{F1_MUTED};font-weight:600;"
            f"letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;'>"
            f"Clasificación de constructores {temporada_sel}</div>",
            unsafe_allow_html=True
        )
        st.dataframe(df_tabla.head(15), use_container_width=True, hide_index=True)

    with col10:
        # Gráfica horizontal de puntos por constructor
        df_top_res = df_res.head(10).sort_values("puntos_totales")
        fig8 = go.Figure()
        fig8.add_trace(go.Bar(
            y=df_top_res["constructor"],
            x=df_top_res["puntos_totales"],
            orientation="h",
            marker=dict(
                color=df_top_res["puntos_totales"],
                colorscale=[[0,"#1A1A1A"],[0.5,F1_GOLD],[1,F1_RED]],
                showscale=False,
            ),
            text=df_top_res["puntos_totales"].round(0).astype(int),
            textposition="outside",
            textfont=dict(color=F1_TEXT, size=11),
        ))
        fig8.update_layout(**PLOTLY_BASE,
            title=f"Puntos totales por constructor — Temporada {temporada_sel}",
            showlegend=False, height=380)
        fig8.update_xaxes(title="Puntos totales", **AXIS_STYLE)
        fig8.update_yaxes(title="", **AXIS_STYLE)
        st.plotly_chart(fig8, use_container_width=True)

    # Gráfica de victorias + podios + abandonos side by side
    df_comp = df_res.head(8).copy()
    fig9 = go.Figure()
    fig9.add_trace(go.Bar(
        name="Victorias", x=df_comp["constructor"], y=df_comp["victorias"],
        marker_color=F1_RED,
        text=df_comp["victorias"], textposition="outside",
        textfont=dict(color=F1_TEXT, size=10),
    ))
    fig9.add_trace(go.Bar(
        name="Podios", x=df_comp["constructor"], y=df_comp["podios"],
        marker_color=F1_GOLD,
        text=df_comp["podios"], textposition="outside",
        textfont=dict(color=F1_TEXT, size=10),
    ))
    fig9.add_trace(go.Bar(
        name="Abandonos", x=df_comp["constructor"], y=df_comp["abandonos"],
        marker_color="#444",
        text=df_comp["abandonos"], textposition="outside",
        textfont=dict(color=F1_TEXT, size=10),
    ))
    fig9.update_layout(**PLOTLY_BASE,
        title=f"Victorias · Podios · Abandonos — Top 8 constructores {temporada_sel}",
        barmode="group", legend=LEGEND_STYLE, height=340)
    fig9.update_xaxes(title="Constructor", tickangle=-20, **AXIS_STYLE)
    fig9.update_yaxes(title="Cantidad", **AXIS_STYLE)
    st.plotly_chart(fig9, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="f1-footer">
  F1 Analytics · Proyecto Final Módulo 4 — BI y SQL Avanzado ·
  Dataset: Ergast F1 Database 1950–2024 · Aurora PostgreSQL ·
  Técnicas SQL: Window Functions · CTEs · PERCENTILE_CONT · DATE_PART+AGE · Stored Procedure
</div>
""", unsafe_allow_html=True)
