import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# -----------------------------------------------------------------------------
# Configuração da Página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Contratos - Fiscal Marcos Brumatti",
    page_icon="📋",
    layout="wide"
)

# -----------------------------------------------------------------------------
# Classe PDF com Layout Modernizado e Limpo
# -----------------------------------------------------------------------------
class RelatorioPDF(FPDF):
    def header(self):
        # Título / Cabeçalho
        self.set_font("Arial", "B", 12)
        self.set_text_color(33, 37, 41)
        self.cell(0, 8, "RELATÓRIO MENSAL DE ACOMPANHAMENTO DE CONTRATO", border=0, ln=True, align="C")
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

    def secao_titulo(self, titulo):
        """Cria um cabeçalho de seção estilizado"""
        self.set_font("Arial", "B", 10)
        self.set_fill_color(230, 235, 245)
        self.set_text_color(24, 43, 73)
        self.cell(0, 6, f"  {titulo}", border=1, ln=True, fill=True)
        self.set_text_color(0, 0, 0)

    def campo_texto(self, titulo, conteudo, altura=20):
        """Cria blocos de texto dinâmicos com auto-quebra de linha"""
        self.secao_titulo(titulo)
        self.set_font("Arial", "", 9)
        # Usamos multi_cell para evitar que textos longos sejam cortados
        self.multi_cell(0, 5, conteudo, border="LRB", align="L")
        self.ln(2)

def gerar_pdf_bytes(dados):
    """Gera o arquivo PDF em memória (retorna bytes)"""
    pdf = RelatorioPDF("P", "mm", "A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # 1. Informações Básicas
    pdf.secao_titulo("1. IDENTIFICAÇÃO DO CONTRATO E CONTRATADA")
    pdf.set_font("Arial", "", 9)
    
    # Linha 1: Contrato e Abertura
    pdf.cell(95, 6, f" Contrato Nº: {dados['contrato']}", border="L")
    pdf.cell(95, 6, f" Data de Início: {dados['data_inicio']}", border="R", ln=True)
    
    # Linha 2: Contratada
    pdf.cell(190, 6, f" Contratado(a): {dados['empresa']}", border="LR", ln=True)
    
    # Linha 3: Objeto
    pdf.set_font("Arial", "B", 9)
    pdf.cell(190, 5, " Objeto:", border="LR", ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.multi_cell(190, 5, f" {dados['objeto']}", border="LRB")
    pdf.ln(2)

    # 2. Prazos e Valores
    pdf.secao_titulo("2. DETALHES FINANCEIROS E LEGAIS")
    pdf.set_font("Arial", "", 9)
    pdf.cell(95, 6, f" Data Conclusão: {dados['data_fim']}", border="L")
    pdf.cell(95, 6, f" Valor do Contrato: R$ {dados['valor']}", border="R", ln=True)
    
    pdf.cell(95, 6, f" Prazo: {dados['prazo']} dias", border="L")
    pdf.cell(95, 6, f" Licitação: {dados['licitacao']}", border="R", ln=True)
    
    pdf.cell(190, 6, f" Recurso: {dados['recurso']}", border="LRB", ln=True)
    pdf.ln(2)

    # 3. Textos do Relatório (Desejável que fluam e não cortem)
    pdf.campo_texto("3. OCORRÊNCIAS", dados['ocorrencias'])
    pdf.campo_texto("4. DILIGÊNCIAS, DEMANDAS E PROVIDÊNCIAS ADOTADAS", dados['diligencias'])
    pdf.campo_texto("5. AVALIAÇÃO DOS SERVIÇOS E DOCUMENTOS", dados['avaliacao'])
    pdf.campo_texto("6. OBSERVAÇÕES / SUGESTÕES / RECLAMAÇÕES", dados['obs'])

    # 4. Assinatura e Dados do Fiscal
    pdf.ln(3)
    pdf.secao_titulo("7. IDENTIFICAÇÃO DO FISCAL")
    pdf.set_font("Arial", "", 9)
    pdf.cell(110, 6, f" Fiscal de Contrato: {dados['fiscal_nome']}", border="L")
    pdf.cell(80, 6, " ASSINATURA", border="R", ln=True, align="C")
    
    pdf.cell(110, 6, f" Portaria Nº: {dados['portaria_nro']} | Data: {dados['portaria_data']}", border="L")
    pdf.cell(80, 12, "", border="R", ln=True) # Espaço para assinatura física/digital
    
    pdf.cell(190, 6, f" Relatório Referente a: {dados['data_relatorio']}", border="LRB", ln=True)

    return pdf.output(dest="S") ##.encode("latin-1", errors="replace")
# --------------------------------------------
# Conexão com Google Sheets via Streamlit GSheetsConnection
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

# Carrega os dados das abas (defina os nomes das planilhas/abas no argumento `worksheet`)
@st.cache_data(ttl=60)  # Recarrega a cada 60 segundos
def carregar_dados():
    df_contratos = conn.read(worksheet="Planilha1")
    df_relatorio = conn.read(worksheet="Planilha2")
    return df_contratos, df_relatorio

try:
    df_contratos, df_relatorio = carregar_dados()
except Exception as e:
    st.error(f"Erro ao conectar ao Google Sheets: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# Interface Principal do Streamlit
# -----------------------------------------------------------------------------
st.title("📋 Relatório Mensal de Acompanhamento de Contratos")

# Sidebar - Seleção
lista_contratos = df_contratos['contrato'].dropna().unique().tolist()
nro_contrato = st.sidebar.selectbox("Escolha o Contrato:", lista_contratos)

# Filtra dados do contrato selecionado
dados_ctr = df_contratos[df_contratos['contrato'] == nro_contrato].iloc[0]

st.sidebar.markdown("---")
st.sidebar.subheader("Empresa Contratada")
st.sidebar.info(dados_ctr['empresa'])

# Busca histórico do relatório mais recente para preencher os campos por padrão
historico = df_relatorio[df_relatorio['CONTRATO'] == nro_contrato]
ultimo_registro = historico.tail(1) if not historico.empty else None

# Formulário de Edição
with st.form("form_relatorio"):
    st.subheader(f"Edição do Relatório - Contrato: {nro_contrato}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Empresa:** {dados_ctr['empresa']}")
        st.write(f"**Valor:** R$ {dados_ctr['valor']}")
    with col2:
        st.write(f"**Fiscal:** {dados_ctr['fiscal']}")
        st.write(f"**Portaria:** {dados_ctr['portaria']}")

    st.markdown("---")
    
    ocorrencias_def = ultimo_registro.iloc[0]['OCORRENCIA'] if ultimo_registro is not None else ""
    diligencias_def = ultimo_registro.iloc[0]['DILIGENCIA'] if ultimo_registro is not None else ""
    avaliacao_def = ultimo_registro.iloc[0]['AVALIACAO'] if ultimo_registro is not None else ""
    obs_def = ultimo_registro.iloc[0]['OBSERVAÇÃO'] if ultimo_registro is not None else ""

    ocorrencias = st.text_area("Ocorrências", value=ocorrencias_def, height=100)
    diligencias = st.text_area("Diligências, demandas e providências adotadas", value=diligencias_def, height=100)
    avaliacao = st.text_area("Avaliação dos serviços e documentos apresentados", value=avaliacao_def, height=100)
    obs = st.text_area("Observações / Sugestões / Reclamações", value=obs_def, height=100)
    
    data_relatorio = st.date_input("Data do Relatório", value=datetime.today())
    data_relatorio_str = data_relatorio.strftime("%d/%m/%Y")

    btn_salvar = st.form_submit_button("💾 Salvar Dados e Gerar Relatório")

# -----------------------------------------------------------------------------
# Processamento e Emissão/Pré-visualização
# -----------------------------------------------------------------------------
if btn_salvar:
    # 1. Atualizar/Inserir no Google Sheets
    novo_registro = pd.DataFrame([{
        "CONTRATO": nro_contrato,
        "DATA_RELATORIO": data_relatorio_str,
        "ocorrencias": ocorrencias,
        "diligencias": diligencias,
        "avaliacao": avaliacao,
        "observacao": obs
    }])
    
    df_atualizado = pd.concat([df_relatorio, novo_registro], ignore_index=True)
    conn.update(worksheet="Planilha2", data=df_atualizado)
    st.success("✅ Dados salvos com sucesso no Google Sheets!")
    st.cache_data.clear()

    # 2. Montar Dicionário de Dados para o PDF
    dados_pdf = {
        'contrato': str(nro_contrato),
        'empresa': str(dados_ctr['empresa']),
        'objeto': str(dados_ctr['objeto']),
        'data_inicio': str(dados_ctr['inicio']),
        'data_fim': str(dados_ctr['fim']),
        'prazo': str(dados_ctr['prazo']),
        'valor': str(dados_ctr['valor']),
        'licitacao': str(dados_ctr['licitacao']),
        'recurso': str(dados_ctr['recurso']),
        'fiscal_nome': str(dados_ctr['fiscal']),
        'portaria_nro': str(dados_ctr['portaria']),
        'portaria_data': str(dados_ctr['data_portaria']),
        'ocorrencias': ocorrencias,
        'diligencias': diligencias,
        'avaliacao': avaliacao,
        'obs': obs,
        'data_relatorio': data_relatorio_str
    }

    # 3. Gerar Bytes do PDF
    pdf_bytes = gerar_pdf_bytes(dados_pdf)

    # 4. Pré-visualização e Botão de Download (Resolve o problema de salvar na pasta local)
    st.markdown("### 📄 Pré-visualização e Download do Relatório")
    
    filename_pdf = f"Relatorio_CTR_{str(nro_contrato).replace('/', '-')}.pdf"
    
    # Botão de download do PDF no navegador do usuário
    st.download_button(
        label="📥 Baixar Relatório em PDF",
        data=pdf_bytes,
        file_name=filename_pdf,
        mime="application/pdf"
    )
