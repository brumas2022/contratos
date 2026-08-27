import streamlit as st
import pandas as pd
import datetime

# -----------------------------------------------------------------------------
# Configuração Inicial da Página
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Consulta Contratos de Obra", layout="wide")

# -----------------------------------------------------------------------------
# Estilização CSS Customizada (Fundo Verde Claro)
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Cor de fundo da área principal da aplicação */
    .stApp {
        background-color: #E8F5E9; /* Verde claro suave (pode usar #F0F9F0 para ainda mais claro) */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------------------------------------------
# Leitura e Cache de Dados
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def carregar_dados():
    df_contratos = pd.read_excel("DADOS_CONTRATOS.xlsx")
    df_medicao = pd.read_excel("NOVA_MEDICAO.xlsx", sheet_name=0)
    df_aditivo = pd.read_excel("NOVA_MEDICAO.xlsx", sheet_name=1)
    return df_contratos, df_medicao, df_aditivo

try:
    df_contratos, df_medicao, df_aditivo = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar os arquivos de dados (.xlsx): {e}")
    st.stop()

# -----------------------------------------------------------------------------
# Mapeamento de Contratos (Nome de Exibição -> Índice na Planilha DADOS_CONTRATOS)
# -----------------------------------------------------------------------------
MAPA_CONTRATOS = {
    "MASTER - 034/2022": 13,
    "MASTER - 028/2023": 10,
    "ALPHA": 0,
    "CONSTRUTORA MENEGUETI - VG": 24,
    "TECNBOMBAS - 007/2024": 22,
    "TECNOBOMBAS - 004/2023": 11,
    "SPARTACUS - 024/2024": 30,
    "MILLENIUM - 009/2023": 16,
    "MILLENIUM - 003/2024": 17,
    "MILLENIUM - 017/2024": 37,
    "MILLENIUM - 008/2023": 15,
    "COOMSER OBRA": 34,
    "SPARTACUS - 013/2024": 23,
    "SM7 - TANKS BR": 4,
    "ENRON": 45,
    "RONDOFONE": 46,
    "SOLOS": 47,
    "R.SANTANA": 48
}

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

def exibir_dados_gerais(idx):
    linha = df_contratos.iloc[idx]
    
    # Formatação de valor
    valor_bruto = linha.get("valor", 0)
    valor_fmt = f"R$ {valor_bruto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    # Formatação das datas
    dt_inicio = pd.to_datetime(linha.get("inicio")).strftime("%d/%m/%Y") if pd.notna(linha.get("inicio")) else "-"
    dt_fim = pd.to_datetime(linha.get("fim")).strftime("%d/%m/%Y") if pd.notna(linha.get("fim")) else "-"

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
    df_filtrado = df_aditivo[df_aditivo["CONTRATO"] == nro_contrato]
    
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

def exibir_medicoes(idx, nro_contrato):
    st.subheader("📏 Medições Realizadas")
    df_selecao = df_medicao[df_medicao["CONTRATO"] == nro_contrato].copy()
    
    valor_contrato_orig = float(df_contratos.iloc[idx].get("valor", 0))
    
    # Soma de aditivos de valor
    valor_aditivos = df_aditivo[
        (df_aditivo["CONTRATO"] == nro_contrato) & 
        (df_aditivo["TIPO"] == "ADITIVO DE VALOR")
    ]["VALOR"].sum()
    
    valor_total_contrato = valor_contrato_orig + valor_aditivos
    
    if not df_selecao.empty:
        df_selecao["% ACUMULADO"] = df_selecao["VALOR"].cumsum()
        df_selecao["% EXECUTADO DO CONTRATO"] = (df_selecao["% ACUMULADO"] / valor_total_contrato) * 100
        
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

    # Exibição dos Totais e Saldos
    st.markdown("---")
    st.markdown("### 📊 Resumo Financeiro")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Medido", f"R$ {total_medido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Percentual Executado", f"{porcento:.2f} %")
    c3.metric("Saldo do Contrato + Aditivos", f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

def exibir_graficos(nro_contrato):
    st.subheader("📈 Evolução das Medições")
    df_selecao = df_medicao[df_medicao["CONTRATO"] == nro_contrato]
    
    if df_selecao.empty:
        st.info("Sem dados de medição suficientes para gerar gráficos.")
        return
        
    valores = df_selecao['VALOR'].tolist()
    st.bar_chart(valores, use_container_width=True)

# -----------------------------------------------------------------------------
# Interface Sidebar
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 Gestão de Contratos")

opcoes_menu = ["-- Selecione um Contrato --", "🗓️ Ver Vencimentos"] + list(MAPA_CONTRATOS.keys())
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
    idx_contrato = MAPA_CONTRATOS[escolha]
    nro_contrato = str(df_contratos.iloc[idx_contrato, 1])

    st.title(f"Contrato: {escolha}")
    
    aba_dados, aba_medicoes, aba_aditivos, aba_grafico = st.tabs([
        "📋 Dados do Contrato", 
        "📏 Medições", 
        "📑 Aditivos", 
        "📈 Gráfico"
    ])
    
    with aba_dados:
        exibir_dados_gerais(idx_contrato)
        
    with aba_medicoes:
        exibir_medicoes(idx_contrato, nro_contrato)
        
    with aba_aditivos:
        exibir_aditivos(nro_contrato)
        
    with aba_grafico:
        exibir_graficos(nro_contrato)
