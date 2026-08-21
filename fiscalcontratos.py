import io
import base64
import pandas as pd
import streamlit as st
from fpdf import FPDF
from datetime import datetime

# ------------------------------------------------------------------------------
# 1. Configuração da Página
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Contratos - Fiscal Marcos Brumatti",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------------------------
# 2. Carregamento de Dados (Google Sheets / Excel)
# ------------------------------------------------------------------------------
# Para conectar ao Google Sheets:
# 1. Abra sua planilha no Google Drive.
# 2. Vá em Arquivo > Compartilhar > Compartilhar com outras pessoas -> Mude para "Qualquer pessoa com o link".
# 3. Substitua O_ID_DA_SUA_PLANILHA abaixo pelo ID real (que fica na URL entre /d/ e /edit).

SHEET_ID = "1888864733"
GID_CONTRATOS = "1888864733"          # ID da aba de Contratos
GID_RELATORIOS = "12345678"  # ID da aba de Relatórios Históricos

@st.cache_data(ttl=60)
def carregar_dados_google_sheets(sheet_id, gid="0"):
    """Lê dados de uma aba específica do Google Sheets via CSV export."""
    url = f"https://docs.google.com/spreadsheets/d/1888864733/export?format=csv&gid={gid}" ## https://docs.google.com/spreadsheets/d/1ANxy7fkVPYlldx7_N3Ywm8J8J5aBIX5mKFBpy4E_h_Y/edit?gid=1888864733#gid=1888864733
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets (gid={gid}): {e}")
        return pd.DataFrame()

def carregar_dados():
    """Tenta carregar do Google Sheets; se falhar ou se não configurado, usa fallback Excel local."""
    if SHEET_ID != "SEU_SPREADSHEET_ID_AQUI":
        df_contratos = carregar_dados_google_sheets(SHEET_ID, GID_CONTRATOS)
        df_relatorio = carregar_dados_google_sheets(SHEET_ID, GID_RELATORIOS)
    else:
        # Fallback local
        try:
            df_contratos = pd.read_excel("DADOS_CONTRATOS.xlsx")
            df_relatorio = pd.read_excel("relatorio_novo.xlsx")
        except Exception:
            df_contratos = pd.DataFrame()
            df_relatorio = pd.DataFrame()
    return df_contratos, df_relatorio

df_contratos, df_relatorio = carregar_dados()

# ------------------------------------------------------------------------------
# 3. Classe do Gerador de PDF (em Memória)
# ------------------------------------------------------------------------------
class PDFRelatorioContrato(FPDF):
    def header(self):
        # Tenta carregar imagem do logotipo se existir
        try:
            self.image("contratos/Logosanear1.jpg", x=60, y=10, w=90, h=25)
        except Exception:
            pass
        self.set_font("Arial", "B", 11)
        self.set_y(38)
        self.cell(0, 10, "RELATÓRIO MENSAL DE ACOMPANHAMENTO DE CONTRATO", align="C", ln=1)

def gerar_pdf_bytes(dados_contrato, ocorrencias, diligencia, avaliacao, obs, data_relatorio_str):
    """Gera o PDF em formato de bytes em memória."""
    pdf = PDFRelatorioContrato("P", "mm", "A4")
    pdf.add_page()
    pdf.set_font("Arial", size=9)

    # Dados Básicos
    pdf.text(11, 52, f"CONTRATO Nº : {dados_contrato.get('contrato', '')}")
    pdf.text(130, 52, f"DATA DE ABERTURA: {dados_contrato.get('data_inicio_str', '')}")

    # Empresa
    pdf.rect(10, 55, 40, 10)
    pdf.rect(50, 55, 150, 10)
    pdf.text(11, 61, "CONTRATADO(A):")
    
    empresa_nome = str(dados_contrato.get('empresa', ''))
    pdf.text(52, 60, empresa_nome[:65])
    if len(empresa_nome) > 65:
        pdf.text(52, 64, empresa_nome[65:130])

    # Termo / Objeto do Contrato
    pdf.rect(10, 68, 190, 20)
    pdf.text(11, 73, "TERMO DO CONTRATO :")
    objeto = str(dados_contrato.get('objeto', ''))
    pdf.text(53, 73, objeto[:65])
    pdf.text(53, 78, objeto[65:130])
    pdf.text(53, 83, objeto[130:195])

    # Unidade / Datas / Valores
    pdf.rect(10, 90, 190, 8)
    pdf.text(11, 95, "UNIDADE DETENTORA DO CONTRATO:")
    
    pdf.rect(10, 98, 190, 20)
    pdf.text(11, 104, f"DATA DO INÍCIO : {dados_contrato.get('data_inicio_str', '')}")
    pdf.text(11, 109, f"DATA DA CONCLUSÃO : {dados_contrato.get('data_fim_str', '')}")
    pdf.text(11, 114, f"PRAZO DO CONTRATO : {dados_contrato.get('prazo', '')} dias")

    pdf.text(121, 104, f"VALOR DO CONTRATO : {dados_contrato.get('valor', '')}")
    pdf.text(121, 109, f"LICITAÇÃO : {dados_contrato.get('licitacao', '')}")
    pdf.text(121, 114, f"RECURSO : {dados_contrato.get('recurso', '')}")

    # Campos de Texto (Ocorrências, Diligências, Avaliação, Obs)
    secoes = [
        ("Ocorrências", ocorrencias, 120),
        ("Diligências,\ndemandas e\nprovidências", diligencia, 150),
        ("Avaliação dos\nserviços e\ndocumentos", avaliacao, 180),
        ("Observações /\nSugestões /\nReclamações", obs, 210),
    ]

    for label, texto, y_pos in secoes:
        # Caixas laterais
        pdf.rect(10, y_pos, 30, 30)
        pdf.rect(40, y_pos, 160, 30)

        # Rótulo (suporta quebras manuais)
        lbl_y = y_pos + 5
        for line in label.split('\n'):
            pdf.text(11, lbl_y, line)
            lbl_y += 4.5

        # Conteúdo do texto
        texto_str = str(texto or '')
        pdf.text(42, y_pos + 6, texto_str[:80])
        if len(texto_str) > 80:
            pdf.text(42, y_pos + 12, texto_str[80:160])
        if len(texto_str) > 160:
            pdf.text(42, y_pos + 18, texto_str[160:240])

    # Rodapé / Assinatura
    pdf.rect(10, 255, 100, 8)
    pdf.text(11, 260, f"FISCAL DE CONTRATO : {dados_contrato.get('fiscal_nome', '')}")

    pdf.rect(10, 263, 100, 8)
    pdf.text(11, 268, f"PORTARIA Nº {dados_contrato.get('portaria_nro', '')}, DATA: {dados_contrato.get('portaria_data_str', '')}")

    pdf.rect(10, 271, 100, 8)
    pdf.text(11, 276, f"RELATÓRIO REFERENTE A : {data_relatorio_str}")

    pdf.rect(110, 255, 90, 8)
    pdf.text(130, 260, 'ASSINATURA')
    pdf.rect(110, 263, 90, 16)

    # Retorna o buffer de memória em bytes
    return pdf.output(dest='S').encode('latin1', errors='replace')


# ------------------------------------------------------------------------------
# 4. Interface do Usuário no Streamlit
# ------------------------------------------------------------------------------
st.title("📄 Relatório Mensal de Acompanhamento de Contratos")

if df_contratos.empty:
    st.warning("Nenhum dado de contrato carregado. Verifique as fontes de dados ou a configuração do Google Sheets.")
    st.stop()

# Sidebar para Seleção de Contrato
df_nro_contrato = df_contratos['contrato'].dropna().unique().tolist()
nro_selecionado = st.sidebar.selectbox("Selecione o Contrato", df_nro_contrato)

# Extração de Dados do Contrato Selecionado
resultado = df_contratos.loc[df_contratos['contrato'] == nro_selecionado]

if not resultado.empty:
    row = resultado.iloc[0]
    
    # Tratamento de datas seguras
    def formatar_data(val):
        if pd.isna(val): return ""
        if isinstance(val, datetime): return val.strftime("%d/%m/%Y")
        try: return pd.to_datetime(val).strftime("%d/%m/%Y")
        except: return str(val)

    dados_contrato = {
        'contrato': nro_selecionado,
        'empresa': row.get('empresa', ''),
        'objeto': row.get('objeto', ''),
        'data_inicio_str': formatar_data(row.get('data_inicio', '')),
        'data_fim_str': formatar_data(row.get('data_fim', '')),
        'prazo': row.get('prazo', ''),
        'valor': row.get('valor', ''),
        'licitacao': row.get('licitacao', ''),
        'recurso': row.get('recurso', ''),
        'fiscal_nome': row.get('fiscal_nome', ''),
        'portaria_nro': row.get('portaria_nro', ''),
        'portaria_data_str': formatar_data(row.get('portaria_data', ''))
    }

    st.sidebar.markdown("---")
    st.sidebar.subheader("Informações do Contrato")
    st.sidebar.write(f"**Empresa:** {dados_contrato['empresa']}")
    st.sidebar.write(f"**Fiscal:** {dados_contrato['fiscal_nome']}")

    # Histórico do Relatório
    if not df_relatorio.empty and 'CONTRATO' in df_relatorio.columns:
        historico = df_relatorio.loc[df_relatorio['CONTRATO'] == nro_selecionado]
        st.sidebar.markdown("---")
        st.sidebar.subheader("Histórico de Lançamentos")
        st.sidebar.dataframe(historico, height=180)
        
        # Pega a última entrada registrada para preenchimento padrão
        if not historico.empty:
            ultimo_reg = historico.tail(1).iloc[0]
            val_ocorrencias = ultimo_reg.get('ocorrencias', '')
            val_diligencias = ultimo_reg.get('diligencias', '')
            val_avaliacao = ultimo_reg.get('avaliacao', '')
            val_obs = ultimo_reg.get('observacoes', '')
        else:
            val_ocorrencias, val_diligencias, val_avaliacao, val_obs = "", "", "", ""
    else:
        val_ocorrencias, val_diligencias, val_avaliacao, val_obs = "", "", "", ""

    # Formulário e Aba de Pré-Visualização
    tab_form, tab_preview = st.tabs(["📝 Preenchimento do Relatório", "👁️ Pré-visualização do PDF"])

    with tab_form:
        col1, col2 = st.columns(2)
        with col1:
            ocorrencias = st.text_area("Ocorrências", value=val_ocorrencias, height=120)
            diligencia = st.text_area("Diligências / Providências", value=val_diligencias, height=120)
        with col2:
            avaliacao = st.text_area("Avaliação dos Serviços", value=val_avaliacao, height=120)
            obs = st.text_area("Observações / Sugestões", value=val_obs, height=120)
        
        data_relatorio = st.date_input("Data do Relatório", datetime.now())
        data_relatorio_str = data_relatorio.strftime("%d/%m/%Y")

    # Gerar PDF em memória para preview
    pdf_bytes = gerar_pdf_bytes(
        dados_contrato,
        ocorrencias,
        diligencia,
        avaliacao,
        obs,
        data_relatorio_str
    )

    with tab_preview:
        st.subheader("Pré-visualização do Relatório")
        
        # Exibe PDF inline usando base64/iframe
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
        
        st.markdown("---")
        # Botão de Download
        nome_arquivo_pdf = f"CTR_{str(nro_selecionado).replace('/', '-')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        st.download_button(
            label="📥 Baixar PDF Gerado",
            data=pdf_bytes,
            file_name=nome_arquivo_pdf,
            mime="application/pdf"
        )
