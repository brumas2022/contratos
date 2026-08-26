import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import os

# -----------------------------------------------------------------------------
# Configuração da Página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Contratos - Fiscal Marcos Brumatti",
    page_icon="📋",
    layout="wide"
)

# -----------------------------------------------------------------------------
# Funções Auxiliares de Formatação e Tratamento de Datas
# -----------------------------------------------------------------------------
def formatar_moeda_br(valor):
    """Converte valores numéricos para o padrão de moeda brasileiro (ex: 1.234.567,89)"""
    try:
        if isinstance(valor, str):
            valor = valor.replace("R$", "").replace(".", "").replace(",", ".").strip()
        val_float = float(valor)
        return f"{val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(valor)

def formatar_inteiro(valor):
    """Garante que o valor seja exibido como número inteiro, sem casas decimais"""
    try:
        if isinstance(valor, str):
            valor = valor.replace(",", ".").strip()
        val_float = float(valor)
        return str(int(val_float))
    except (ValueError, TypeError):
        return str(valor)

def converter_para_data(valor):
    """Converte dinamicamente diferentes formatos de entrada para objeto date"""
    if pd.isna(valor) or valor is None:
        return None
    if isinstance(valor, (datetime, pd.Timestamp)):
        return valor.date()
    str_data = str(valor).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(str_data, fmt).date()
        except ValueError:
            pass
    return None

def obter_contratos_a_vencer(df_p1, df_p5, dias=60):
    """
    Verifica prazos na Planilha1 (coluna 'fim') e na Planilha5 (colunas de vigência/execução)
    para o limite de 60 dias a partir de hoje.
    """
    hoje = datetime.now().date()
    limite = hoje + timedelta(days=dias)
    
    contratos_vencendo = []
    
    # 1. Checagem na Planilha1
    for idx, row in df_p1.iterrows():
        nro_contrato = row.get('contrato')
        data_fim = converter_para_data(row.get('fim'))
        
        if data_fim and hoje <= data_fim <= limite:
            contratos_vencendo.append({
                "Contrato": nro_contrato,
                "Empresa": row.get('empresa', '-'),
                "Tipo de Prazo": "Fim do Contrato (Planilha1)",
                "Vencimento": data_fim.strftime("%d/%m/%Y"),
                "Dias Restantes": (data_fim - hoje).days
            })

    # 2. Checagem na Planilha5 (Buscando por Execução ou Vigência)
    if df_p5 is not None and not df_p5.empty:
        # Padroniza os nomes das colunas para busca
        colunas_p5 = [str(c).lower().strip() for c in df_p5.columns]
        df_p5_temp = df_p5.copy()
        df_p5_temp.columns = colunas_p5

        # Identifica colunas alvo na Planilha5
        col_contrato = next((c for c in colunas_p5 if 'contrato' in c), None)
        cols_prazos = [c for c in colunas_p5 if any(p in c for p in ['execucao', 'execução', 'vigencia', 'vigência', 'fim'])]

        if col_contrato and cols_prazos:
            for idx, row in df_p5_temp.iterrows():
                nro_ctr = row.get(col_contrato)
                if pd.isna(nro_ctr):
                    continue
                
                # Busca o nome da empresa correspondente na Planilha1
                empresa_nome = "-"
                match_p1 = df_p1[df_p1['contrato'] == nro_ctr]
                if not match_p1.empty:
                    empresa_nome = match_p1.iloc[0].get('empresa', '-')

                for col_p in cols_prazos:
                    dt_prazo = converter_para_data(row.get(col_p))
                    if dt_prazo and hoje <= dt_prazo <= limite:
                        label_tipo = f"{col_p.replace('_', ' ').title()} (Planilha5)"
                        
                        # Evita duplicidade exata de contrato + mesmo tipo
                        if not any(c['Contrato'] == nro_ctr and c['Tipo de Prazo'] == label_tipo for c in contratos_vencendo):
                            contratos_vencendo.append({
                                "Contrato": nro_ctr,
                                "Empresa": empresa_nome,
                                "Tipo de Prazo": label_tipo,
                                "Vencimento": dt_prazo.strftime("%d/%m/%Y"),
                                "Dias Restantes": (dt_prazo - hoje).days
                            })
            
    df_resultado = pd.DataFrame(contratos_vencendo)
    if not df_resultado.empty:
        # Remove duplicatas gerais se existirem registros idênticos
        df_resultado = df_resultado.drop_duplicates(subset=["Contrato", "Tipo de Prazo", "Vencimento"])
    
    return df_resultado

# -----------------------------------------------------------------------------
# Classe PDF com Layout Modernizado, Profissional e Suporte a Logotipo
# -----------------------------------------------------------------------------
class RelatorioPDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_margins(12, 12, 12)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        logo_path = "Logosanear1.jpg"
        if os.path.exists(logo_path):
            self.image(logo_path, x=75, y=10, w=60)
            self.ln(22)
        else:
            self.ln(8)

        self.set_fill_color(24, 43, 73)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 11)
        self.cell(0, 8, "RELATÓRIO MENSAL DE ACOMPANHAMENTO DE CONTRATO", border=0, ln=True, align="C", fill=True)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

    def secao_titulo(self, titulo):
        self.set_font("Arial", "B", 9)
        self.set_fill_color(230, 238, 248)
        self.set_text_color(24, 43, 73)
        self.cell(0, 6, f"  {titulo}", border=1, ln=True, fill=True)
        self.set_text_color(0, 0, 0)

    def campo_texto(self, titulo, conteudo, altura=20):
        self.secao_titulo(titulo)
        self.set_font("Arial", "", 8.5)
        texto = conteudo.strip() if conteudo and conteudo.strip() else "Nenhuma ocorrência ou observação registrada."
        self.multi_cell(0, 5, f" {texto}", border="LRB", align="L")
        self.ln(2.5)

def gerar_pdf_bytes(dados):
    pdf = RelatorioPDF("P", "mm", "A4")
    pdf.add_page()
    
    # 1. Informações Básicas
    pdf.secao_titulo("1. IDENTIFICAÇÃO DO CONTRATO E CONTRATADA")
    pdf.set_font("Arial", "", 8.5)
    pdf.cell(93, 6, f" Contrato Nº: {dados['contrato']}", border="L")
    pdf.cell(93, 6, f" Data de Início: {dados['data_inicio']}", border="R", ln=True)
    pdf.cell(186, 6, f" Contratado(a): {dados['empresa']}", border="LR", ln=True)
    
    pdf.set_font("Arial", "B", 8.5)
    pdf.cell(186, 5, " Objeto:", border="LR", ln=True)
    pdf.set_font("Arial", "", 8.5)
    pdf.multi_cell(186, 5, f" {dados['objeto']}", border="LRB")
    pdf.ln(2.5)

    # 2. Prazos e Valores
    pdf.secao_titulo("2. DETALHES FINANCEIROS E LEGAIS")
    pdf.set_font("Arial", "", 8.5)
    
    valor_formatado = formatar_moeda_br(dados['valor'])
    prazo_formatado = formatar_inteiro(dados['prazo'])
    
    pdf.cell(93, 6, f" Data Conclusão: {dados['data_fim']}", border="L")
    pdf.cell(93, 6, f" Valor do Contrato: R$ {valor_formatado}", border="R", ln=True)
    pdf.cell(93, 6, f" Prazo: {prazo_formatado} dias", border="L")
    pdf.cell(93, 6, f" Licitação: {dados['licitacao']}", border="R", ln=True)
    pdf.cell(186, 6, f" Recurso: {dados['recurso']}", border="LRB", ln=True)
    pdf.ln(2.5)

    # 3. Textos do Relatório
    pdf.campo_texto("3. OCORRÊNCIAS", dados['ocorrencias'])
    pdf.campo_texto("4. DILIGÊNCIAS, DEMANDAS E PROVIDÊNCIAS ADOTADAS", dados['diligencias'])
    pdf.campo_texto("5. AVALIAÇÃO DOS SERVIÇOS E DOCUMENTOS", dados['avaliacao'])
    pdf.campo_texto("6. OBSERVAÇÕES / SUGESTÕES / RECLAMAÇÕES", dados['obs'])

    # 4. Assinatura e Dados do Fiscal
    pdf.ln(2)
    pdf.secao_titulo("7. IDENTIFICAÇÃO DO FISCAL E ASSINATURA")
    pdf.set_font("Arial", "", 8.5)
    
    portaria_formatada = formatar_inteiro(dados['portaria_nro'])
    
    pdf.cell(106, 6, f" Fiscal de Contrato: {dados['fiscal_nome']}", border="L")
    pdf.cell(80, 6, " ASSINATURA", border="R", ln=True, align="C")
    pdf.cell(106, 12, f" Portaria Nº: {portaria_formatada} | Data: {dados['portaria_data']}", border="LB")
    pdf.cell(80, 12, "", border="RB", ln=True)
    
    pdf.set_font("Arial", "I", 8)
    pdf.cell(186, 6, f" Relatório Referente a: {dados['data_relatorio']}", border="LRB", ln=True, align="R")

    return pdf.output(dest="S")

# -----------------------------------------------------------------------------
# Conexão com Google Sheets
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def carregar_dados():
    df_contratos = conn.read(worksheet="Planilha1")
    df_relatorio = conn.read(worksheet="Planilha2")
    
    # Carrega a Planilha5 se disponível
    try:
        df_planilha5 = conn.read(worksheet="Planilha5")
    except Exception:
        df_planilha5 = pd.DataFrame()
        
    return df_contratos, df_relatorio, df_planilha5

try:
    df_contratos, df_relatorio, df_planilha5 = carregar_dados()
except Exception as e:
    st.error(f"Erro ao conectar ao Google Sheets: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# Interface Principal e Sidebar
# -----------------------------------------------------------------------------
st.title("📋 Relatório Mensal de Acompanhamento de Contratos")

# --- ALERTA DE VENCIMENTOS COMBINADO (Planilha1 e Planilha5) NA SIDEBAR ---
df_vencendo = obter_contratos_a_vencer(df_contratos, df_planilha5, dias=60)
qtd_vencendo = len(df_vencendo)

st.sidebar.markdown("### ⚠️ Alertador de Prazos")
if qtd_vencendo > 0:
    expander_alerta = st.sidebar.expander(f"🔔 Prazos a vencer em 60 dias ({qtd_vencendo})", expanded=False)
    with expander_alerta:
        st.warning(f"Existem **{qtd_vencendo}** prazo(s) com término até 60 dias:")
        st.dataframe(
            df_vencendo.sort_values(by="Dias Restantes"),
            use_container_width=True,
            hide_index=True
        )
else:
    st.sidebar.success("✅ Nenhum prazo a vencer nos próximos 60 dias.")

st.sidebar.markdown("---")

# Seleção de Contrato
lista_contratos = df_contratos['contrato'].dropna().unique().tolist()
nro_contrato = st.sidebar.selectbox("Escolha o Contrato:", lista_contratos)

dados_ctr = df_contratos[df_contratos['contrato'] == nro_contrato].iloc[0]

st.sidebar.subheader("Empresa Contratada")
st.sidebar.info(dados_ctr['empresa'])

historico = df_relatorio[df_relatorio['CONTRATO'] == nro_contrato]
ultimo_registro = historico.tail(1) if not historico.empty else None
st.sidebar.dataframe(historico)

# Formulário de Edição
with st.form("form_relatorio"):
    st.subheader(f"Edição do Relatório - Contrato: {nro_contrato}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Empresa:** {dados_ctr['empresa']}")
        st.write(f"**Valor:** R$ {formatar_moeda_br(dados_ctr['valor'])}")
    with col2:
        st.write(f"**Fiscal:** {dados_ctr['fiscal']}")
        st.write(f"**Portaria:** {formatar_inteiro(dados_ctr['portaria'])}")

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
    novo_registro = pd.DataFrame([{
        "CONTRATO": nro_contrato,
        "MES": data_relatorio_str,
        "OCORRENCIA": ocorrencias,
        "DILIGENCIA": diligencias,
        "AVALIACAO": avaliacao,
        "OBSERVAÇÃO": obs
    }])
    
    df_atualizado = pd.concat([df_relatorio, novo_registro], ignore_index=True)
    conn.update(worksheet="Planilha2", data=df_atualizado)
    st.success("✅ Dados salvos com sucesso no Google Sheets!")
    st.cache_data.clear()

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

    pdf_bytes = bytes(gerar_pdf_bytes(dados_pdf))

    st.markdown("### 📄 Pré-visualização e Download do Relatório")
    filename_pdf = f"Relatorio_CTR_{str(nro_contrato).replace('/', '-')}.pdf"
    st.download_button(label="Baixar Relatório em PDF", data=pdf_bytes, file_name=filename_pdf, mime="application/pdf")
