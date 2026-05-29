import streamlit as st
import numpy as np
import numpy_financial as npf
import pandas as pd
import plotly.graph_objects as go
import io
from openpyxl.styles import Font, PatternFill, Alignment

st.set_page_config(page_title="Viabilidade Solar Avançada", layout="wide")

# URL Direta da imagem da EMPROTEC hospedada
URL_LOGO_EMPROTEC = "https://githubusercontent.com"

# --- CONTROLADOR DE MARCA/IMAGEM NA BARRA LATERAL ---
st.sidebar.header("🎨 Personalização do Aplicativo")

# Opção de posicionamento da marca da EMPROTEC
posicao_marca = st.sidebar.radio(
    "Posição da Logomarca EMPROTEC", 
    ["Superior", "Inferior", "Ambas", "Nenhuma"], 
    index=1  # Define 'Inferior' como padrão, conforme sua preferência atual
)

# Entrada do Nome da Empresa/Consultor
nome_consultor = st.sidebar.text_input("Nome da Empresa / Consultor para o Excel", value="EMPROTEC")

# Exibição da Imagem no Topo da Barra Lateral se selecionado
if posicao_marca in ["Superior", "Ambas"]:
    try:
        st.sidebar.image(URL_LOGO_EMPROTEC, use_container_width=True)
        st.sidebar.markdown("---")
    except:
        st.sidebar.warning("Carregando imagem padrão...")

# Título do App na área principal
st.title("☀️ Simulador Financeiro Fotovoltaico Comercial Avançado")

# --- ABAS DE ENTRADA DE DADOS ---
col1, col2 = st.columns(2)

with col1:
    st.header("🏗️ Dados Técnicos e Investimento")
    potencia_kwp = st.number_input("Potência do Sistema (kWp)", value=70.0)
    
    custo_kit = st.number_input("Custo do KIT Fotovoltaico (R\$)", value=109395.17, step=1000.0)
    custo_instalacao_mao_obra = st.number_input("Custo da Instalação / Engenharia (R\$)", value=65000.0, step=1000.0)
    
    soma_padrao_capex = custo_kit + custo_instalacao_mao_obra
    custo_instalacao_total = st.number_input("Custo Total Instalado (Capex) (R\$)", value=soma_padrao_capex, step=1000.0)

with col2:
    st.header("📉 Tarifas e Premissas de Mercado")
    tarifa_inicial = st.number_input("Tarifa Média Atual da Concessionária (R\$/kWh)", value=0.77)
    reajuste_tarifa = st.number_input("Reajuste Anual da Tarifa (%)", value=4.5) / 100
    tma = st.number_input("Taxa Mínima de Atratividade (TMA) (%)", value=14.5) / 100
    tempo_analise = st.slider("Horizonte de Análise (Anos)", 10, 25, 25)

st.markdown("---")
col3, col4 = st.columns(2)

with col3:
    st.header("🌱 Custos Operacionais Adicionais (OPEX)")
    opex_anual_perc = st.number_input("Manutenção/Limpeza Geral Anual (% do Capex)", value=1.5) / 100
    seguro_anual = st.number_input("Seguro Anual do Sistema (R\$)", value=1500.0)
    locacao_terreno_mensal = st.number_input("Locação Mensal do Terreno (R\$)", value=500.0)
    locacao_terreno_anual = locacao_terreno_mensal * 12

with col4:
    st.header("🤝 Modelo de Negócio: Aluguel / Assinatura")
    modelo_comercial = st.selectbox("Forma de Exploração Comercial", ["Uso Próprio / Unificação Familiar", "Aluguel da Central para Terceiros"])
    
    percentual_cobranca_contratante = 100.0
    if modelo_comercial == "Aluguel da Central para Terceiros":
        percentual_cobranca_contratante = st.slider("Percentual cobrado do Contratante sobre a tarifa (%)", 50, 95, 80) / 100

st.markdown("---")
col5, col6 = st.columns(2)

with col5:
    st.header("🏦 Financiamento (Recursos Próprios se desmarcado)")
    usa_financiamento = st.checkbox("Simular Financiamento?")
    if usa_financiamento:
        perc_financiado = st.slider("% Financiado", 10, 100, 80)
        prazo_meses = st.number_input("Prazo do Financiamento (Meses)", value=60)
        taxa_juros_ano = st.number_input("Taxa de Juros Anual (%)", value=12.0) / 100
        valor_financiado = custo_instalacao_total * (perc_financiado / 100)
    else:
        perc_financiado = 0
        prazo_meses = 0
        taxa_juros_ano = 0.0
        valor_financiado = 0

with col6:
    st.header("⚖️ Regime Tributário")
    regime = st.selectbox("Regime Tributário do Dono da Usina", ["Pessoa Física / Associação", "Simples Nacional", "Lucro Presumido", "Lucro Real"])
    aliquota_imposto = 0.0 if regime == "Pessoa Física / Associação" else (0.06 if regime == "Simples Nacional" else (0.1133 if regime == "Lucro Presumido" else 0.34))
    depreciacao_anos = 10

# --- PROCESSAMENTO DO FLUXO DE CAIXA ---
capex = custo_instalacao_total
aporte_proprio = capex - valor_financiado

geracao_anual_inicial = potencia_kwp * 1525  
degradacao_painel = 0.005 

parcela_anual_financ = 0
if usa_financiamento:
    taxa_mensal = (1 + taxa_juros_ano)**(1/12) - 1
    parcela_mensal = npf.pmt(taxa_mensal, prazo_meses, -valor_financiado)
    parcela_anual_financ = parcela_mensal * 12

fluxos_dono = [-aporte_proprio]
ganho_contratante_lista = [0.0]

for ano in range(1, tempo_analise + 1):
    tarifa_ano = tarifa_inicial * ((1 + reajuste_tarifa) ** (ano - 1))
    geracao_ano = geracao_anual_inicial * ((1 - degradacao_painel) ** (ano - 1))
    
    valor_energia_concessionaria = geracao_ano * tarifa_ano
    
    if modelo_comercial == "Aluguel da Central para Terceiros":
        receita_bruta_dono = valor_energia_concessionaria * percentual_cobranca_contratante
        economia_liquida_contratante = valor_energia_concessionaria - receita_bruta_dono
    else:
        receita_bruta_dono = valor_energia_concessionaria
        economia_liquida_contratante = 0.0
        
    ganho_contratante_lista.append(economia_liquida_contratante)
    
    opex_manutencao = capex * opex_anual_perc * ((1 + reajuste_tarifa) ** (ano - 1))
    seguro_ano = seguro_anual * ((1 + reajuste_tarifa) ** (ano - 1))
    terreno_ano = locacao_terreno_anual * ((1 + reajuste_tarifa) ** (ano - 1))
    opex_total_ano = opex_manutencao + seguro_ano + terreno_ano
    
    depreciacao_ano = (capex / depreciacao_anos) if (ano <= depreciacao_anos and regime == "Lucro Real") else 0
    if regime == "Lucro Real":
        base_calculo = max(0, receita_bruta_dono - opex_total_ano - depreciacao_ano)
        imposto_ano = base_calculo * aliquota_imposto
    else:
        imposto_ano = receita_bruta_dono * aliquota_imposto
        
    custo_financiamento_ano = parcela_anual_financ if (ano <= np.ceil(prazo_meses/12)) else 0
    
    fluxo_liquido_dono = receita_bruta_dono - opex_total_ano - imposto_ano - custo_financiamento_ano
    fluxos_dono.append(fluxo_liquido_dono)

fluxos_dono = np.array(fluxos_dono)
ganho_contratante_lista = np.array(ganho_contratante_lista)

# --- CÁLCULO DE INDICADORES ---
try: tir_dono = npf.irr(fluxos_dono) * 100
except: tir_dono = 0
vpl_dono = npf.npv(tma, fluxos_dono)

acumulado_dono = np.cumsum(fluxos_dono)
payback_dono = "Superior ao horizonte"
for idx in range(1, len(acumulado_dono)):
    if acumulado_dono[idx] >= 0:
        fracao = abs(acumulado_dono[idx - 1]) / fluxos_dono[idx]
        anos = idx - 1 + fracao
        ai = int(anos)
        mr = round((anos - ai) * 12)
        payback_dono = f"{mr} meses" if ai == 0 else f"{ai} ano(s) e {mr} mês(es)"
        break

# --- EXIBIÇÃO DE RESULTADOS NA TELA ---
st.markdown("---")
st.header("📈 Indicadores Financeiros da Usina")

if modelo_comercial == "Aluguel da Central para Terceiros":
    c_dono, c_clie = st.columns(2)
    with c_dono:
        st.subheader("💼 Para o Investidor (Dono/Locador)")
        st.metric("TIR do Investidor", f"{tir_dono:.2f} %")
        st.metric("VPL do Investidor", f"R\$ {vpl_dono:,.2f}")
        st.metric("Payback do Investidor", payback_dono)
    with c_clie:
        st.subheader("👤 Para o Contratante (Cliente/Assinante)")
        st.metric("Economia Líquida no Ano 1", f"R\$ {ganho_contratante_lista:,.2f}")
        st.metric("Economia Acumulada Total", f"R\$ {np.sum(ganho_contratante_lista):,.2f}")
else:
    m1, m2, m3 = st.columns(3)
    m1.metric("Taxa Interna de Retorno (TIR)", f"{tir_dono:.2f} %")
    m2.metric("Valor Presente Líquido (VPL)", f"R\$ {vpl_dono:,.2f}")
    m3.metric("Tempo de Retorno (Payback)", payback_dono)

# --- GRÁFICO ---
st.subheader("📊 Balanço Acumulado do Investidor (Ano a Ano)")
anos_grafico = list(range(0, tempo_analise + 1))
cores = ['#EF553B' if v < 0 else '#00CC96' for v in acumulado_dono]
fig = go.Figure(data=[go.Bar(x=anos_grafico, y=acumulado_dono, marker_color=cores, hovertemplate="Ano %{x}<br>Saldo: R\$ %{y:,.2f}<extra></extra>")])
fig.update_layout(xaxis_title="Anos", yaxis_title="Saldo Acumulado (R\$)", template="plotly_white", height=350)
st.plotly_chart(fig, use_container_width=True)

# --- TABELA E EXPORTAÇÃO EXCEL ---
st.subheader("📋 Detalhamento do Fluxo de Caixa")
df_fluxo = pd.DataFrame({
    "Ano": anos_grafico,
    "Fluxo Liquido Investidor (R\$)": fluxos_dono,
    "Saldo Acumulado Investidor (R\$)": acumulado_dono,
    "Economia Liquida Contratante (R\$)": ganho_contratante_lista
})
st.dataframe(df_fluxo.style.format({"Fluxo Liquido Investidor (R\$)": "R\$ {:,.2f}", "Saldo Acumulado Investidor (R\$)": "R\$ {:,.2f}", "Economia Liquida Contratante (R\$)": "R\$ {:,.2f}"}), use_container_width=True)

buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df_fluxo.to_excel(writer, index=False, sheet_name='Simulação Solar', startrow=4)
    workbook = writer.book
    worksheet = writer.sheets['Simulação Solar']
    
    worksheet['A1'] = "RELATÓRIO DE VIABILIDADE FINANCEIRA - EMPROTEC SOLAR"
    worksheet['A1'].font = Font(name='Arial', size=14, bold=True, color='FFFFFF')
    worksheet['A1'].fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
    worksheet.merge_cells('A1:D1')
    
    worksheet['A2'] = f"Consultoria: {nome_consultor}"
    worksheet['A2'].font = Font(name='Arial', size=11, italic=True)
    worksheet.merge_cells('A2:D2')
    
    worksheet['A3'] = f"Potência Analisada: {potencia_kwp} kWp | Investimento Estimado: R\$ {capex:,.2f}"
    worksheet['A3'].font = Font(name='Arial', size=10)
    worksheet.merge_cells('A3:D3')
    
