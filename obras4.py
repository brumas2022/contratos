import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client

# -----------------------------------------------------------------------------
# Configuração Inicial da Página
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Consulta Contratos de Obra", layout="wide")

# -----------------------------------------------------------------------------
# Estilização CSS Customizada
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #E8F5E9;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------------------------------------------
# Conexão e Leitura do Supabase
# -----------------------------------------------------------------------------
@st.cache_resource
def init_supabase() -> Client:
    # Busca credenciais com fallback preventivo
    ##url = st.secrets.get("SUPABASE_URL")
    ##key = st.secrets.get("SUPABASE_KEY")
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    if not url or not key:
        st.error("⚠️ Configuração ausente: Verifique se 'SUPABASE_URL' e 'SUPABASE_KEY' estão definidas no secrets.toml.")
        st.stop()
        
    return create_client(url, key)

@st.cache_data(ttl=300)
def carregar_medicoes_supabase():
    try:
        supabase = init_supabase()
        response = supabase.table("bdmedicaonova").select("*").execute()
        df = pd.DataFrame(response.data)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar medições do Supabase: {e}")
        return pd.DataFrame()

# -----------------------------------------------------------------------------
# Leitura e Cache dos Dados do Google Sheets
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def carregar_google_sheets():
    SHEET_ID = "1ANxy7fkVPYlldx7_N3Ywm8J8J5aBIX5mKFBpy4E_h_Y"
    
    # GIDs obtidos do seu código original
    GID_PLANILHA1 = "1888864733"
    GID_PLANILHA5 = "228487117"
    
    # Formatação das URLs exportando os dados limpos em CSV via endpoint gviz/tq
    url_planilha1 = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID_PLANILHA1}"
    url_planilha5 = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID_PLANILHA5}"

    try:
        df_contratos = pd.read_csv(url_planilha1)
        df_aditivo = pd.read_csv(url_planilha5)
        return df_contratos, df_aditivo
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame()

# Carregamento Unificado dos Dados
try:
    df_contratos, df_aditivo = carregar_google_sheets()
    df_medicao = carregar_medicoes_supabase()
except Exception as e:
    st.error(f"Erro ao integrar fontes de dados: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# Mapeamento e Dinamização de Contratos
# -----------------------------------------------------------------------------
if not df_contratos.empty and "contrato" in df_contratos.columns:
    LISTA_CONTRATOS = df_contratos["contrato"].dropna().unique().tolist()
else:
    LISTA_CONTRATOS = []

# -----------------------------------------------------------------------------
# Funções de Visão e Renderização
# -----------------------------------------------------------------------------
def exibir_vencimentos():
    st.subheader("🗓️ Contratos a Vencer")
    try:
        contratos_vencer = pd.read_excel("abril-2026.xlsx", sheet_name=0)
        st.dataframe(contratos_vencer, use_container_width=True)
    except Exception as e:
        st.info("Nenhum arquivo de vencimentos pendentes localizado.")

def exibir_dados_gerais(nro_contrato):
    df_filtrado = df_contratos[df_contratos["contrato"] == nro_contrato]
    if df_filtrado.empty:
        st.warning("Dados do contrato não encontrados.")
        return
        
    linha = df_filtrado.iloc[0]
    
    valor_bruto = linha.get("valor", 0)
    try:
        valor_bruto = float(valor_bruto)
    except (ValueError, TypeError):
        valor_bruto = 0.0

    valor_fmt = f"R$ {valor_bruto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    dt_inicio = pd.to_datetime(linha.get("inicio"), errors='coerce').strftime("%d/%m/%Y") if pd.notna(linha.get("inicio")) else "-"
    dt_fim = pd.to_datetime(linha.get("fim"), errors='coerce').strftime("%d/%m/%Y") if pd.notna(linha.get("fim")) else "-"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**CONTRATO:** {linha.get('contrato', '-')}")
        st.markdown(f"**EMPRESA:** {linha.get('empresa', '-')}")
        st.markdown(f"**OBJETO:** {linha.get('objeto', '-')}")
        st.markdown(f"**VALOR ORIGINAL:** {valor_fmt}")
    with col2:
        st.markdown(f"**FISCAL:** {linha.get('fiscal', '-')}")
        st.markdown(f"**INÍCIO:** {dt_inicio}")
        st.markdown(f"**FIM:** {dt_fim}")
        st.markdown(f"**SITUAÇÃO:** {linha.get('situacao', '-')}")

def exibir_aditivos(nro_contrato):
    st.subheader("📑 Aditivos do Contrato")
    if df_aditivo.empty or "CONTRATO" not in df_aditivo.columns:
        st.info("Tabela de aditivos vazia ou mal formatada.")
        return

    df_filtrado = df_aditivo[df_aditivo["CONTRATO"] == nro_contrato].copy()
    
    if df_filtrado.empty:
        st.info("Nenhum aditivo registrado para este contrato.")
        return

    st.dataframe(
        df_filtrado,
        hide_index=True,
        use_container_width=True,
        column_config={
            "DATA": st.column_config.DatetimeColumn("DATA", format="DD/MM/YYYY"),
            "EXECUCAO INICIA": st.column_config.DatetimeColumn("EXECUÇÃO INICIAL", format="DD/MM/YYYY"),
            "EXECUCAO FINAL": st.column_config.DatetimeColumn("EXECUÇÃO FINAL", format="DD/MM/YYYY"),
            "VIGENCIA INICIAL": st.column_config.DatetimeColumn("VIGÊNCIA INICIAL", format="DD/MM/YYYY"),
            "VIGENCIA FINAL": st.column_config.DatetimeColumn("VIGÊNCIA FINAL", format="DD/MM/YYYY"),
            "VALOR": st.column_config.NumberColumn("VALOR (R$)", format="R$ %.2f")
        }
    )

def exibir_medicoes(nro_contrato):
    st.subheader("📏 Medições Realizadas")
    
    if df_medicao.empty or "CONTRATO" not in df_medicao.columns:
        st.info("Nenhum dado de medição disponível no Supabase.")
        return

    df_selecao = df_medicao[df_medicao["CONTRATO"] == nro_contrato].copy()
    
    df_c = df_contratos[df_contratos["contrato"] == nro_contrato]
    valor_contrato_orig = float(df_c.iloc[0].get("valor", 0)) if not df_c.empty else 0.0
    
    valor_aditivos = 0.0
    if not df_aditivo.empty and "CONTRATO" in df_aditivo.columns:
        df_ad_filtrado = df_aditivo[
            (df_aditivo["CONTRATO"] == nro_contrato) & 
            (df_aditivo["TIPO"] == "ADITIVO DE VALOR")
        ]
        if not df_ad_filtrado.empty:
            valor_aditivos = pd.to_numeric(df_ad_filtrado["VALOR"], errors='coerce').sum()
    
    valor_total_contrato = valor_contrato_orig + valor_aditivos
    
    if not df_selecao.empty:
        df_selecao["VALOR"] = pd.to_numeric(df_selecao["VALOR"], errors='coerce').fillna(0)
        df_selecao["% ACUMULADO"] = df_selecao["VALOR"].cumsum()
        df_selecao["% EXECUTADO DO CONTRATO"] = (df_selecao["% ACUMULADO"] / valor_total_contrato * 100) if valor_total_contrato > 0 else 0
        
        st.dataframe(
            df_selecao,
            hide_index=True,
            use_container_width=True,
            column_config={
                "DATA MEDICAO": st.column_config.DatetimeColumn("DATA MEDIÇÃO", format="DD/MM/YYYY"),
                "DATA NF": st.column_config.DatetimeColumn("DATA NF", format="DD/MM/YYYY"),
                "DATA PAGTO": st.column_config.DatetimeColumn("DATA PAGTO", format="DD/MM/YYYY"),
                "VALOR": st.column_config.NumberColumn("VALOR MEDIDO", format="R$ %.2f"),
                "% EXECUTADO DO CONTRATO": st.column_config.NumberColumn("% CONTRATO", format="%.2f %%")
            }
        )

    total_medido = df_selecao["VALOR"].sum() if not df_selecao.empty else 0.0
    saldo = valor_total_contrato - total_medido
    porcento = (total_medido / valor_total_contrato * 100) if valor_total_contrato > 0 else 0.0

    st.markdown("---")
    st.markdown("### 📊 Resumo Financeiro")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Medido", f"R$ {total_medido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Percentual Executado", f"{porcento:.2f} %")
    c3.metric("Saldo do Contrato + Aditivos", f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

def exibir_graficos(nro_contrato):
    st.subheader("📈 Evolução das Medições")
    if df_medicao.empty or "CONTRATO" not in df_medicao.columns:
        st.info("Sem dados de medição suficientes para gerar gráficos.")
        return

    df_selecao = df_medicao[df_medicao["CONTRATO"] == nro_contrato]
    
    if df_selecao.empty:
        st.info("Sem dados de medição suficientes para gerar gráficos.")
        return
        
    valores = pd.to_numeric(df_selecao['VALOR'], errors='coerce').fillna(0).tolist()
    st.bar_chart(valores, use_container_width=True)

# -----------------------------------------------------------------------------
# Interface Sidebar
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 Gestão de Contratos")

opcoes_menu = ["-- Selecione um Contrato --", "🗓️ Ver Vencimentos"] + LISTA_CONTRATOS
escolha = st.sidebar.selectbox("Escolha uma opção:", opcoes_menu)

# -----------------------------------------------------------------------------
# Painel Principal (Roteamento de Telas)
# -----------------------------------------------------------------------------
if escolha == "-- Selecione um Contrato --":
    st.title("📋 Painel de Consulta de Contratos de Obra")
    st.info("Utilize o menu lateral para selecionar um contrato específico ou consultar vencimentos.")

elif escolha == "🗓️ Ver Vencimentos":
    exibir_vencimentos()

else:
    nro_contrato = escolha

    st.title(f"Contrato: {escolha}")
    
    aba_dados, aba_medicoes, aba_aditivos, aba_grafico = st.tabs([
        "📋 Dados do Contrato", 
        "📏 Medições", 
        "📑 Aditivos", 
        "📈 Gráfico"
    ])
    
    with aba_dados:
        exibir_dados_gerais(nro_contrato)
        
    with aba_medicoes:
        exibir_medicoes(nro_contrato)
        
    with aba_aditivos:
        exibir_aditivos(nro_contrato)
        
    with aba_grafico:
        exibir_graficos(nro_contrato)
