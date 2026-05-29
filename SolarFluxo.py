import streamlit as st
import numpy as np
import numpy_financial as npf
import pandas as pd
import plotly.graph_objects as go
import io

st.set_page_config(page_title="Viabilidade Solar Avançada", layout="wide")
st.title("☀️ Simulador Financeiro Fotovoltaico Avançado")

# --- ABAS DE ENTRADA DE DADOS ---
col1, col2 = st.columns(2)

with col1:
    st.header("🏗️ Dados Técnicos e Investimento")
    potencia_kwp = st.number_input("Potência do Sistema (kWp)", value=70.0)
    custo_kit = st.number_input("Custo do Kit (R$)", value=109395.17)
    custo_instalacao_total = st.number_input("Custo Total Instalado (Capex) (R$)", value=174395.17)
    geracao_anual_inicial = st.number_input("Geração Anual Inicial (kWh)", value=106800.0)
    degradacao_painel = st.number_input("Degradação Anual dos Painéis (%)", value=0.5) / 100

with col2:
    st.header("📉 Premissas Financeiras e OPEX")
    tarifa_inicial = st.number_input("Tarifa Média Atual (R$/kWh)", value=0.77)
    reajuste_tarifa = st.number_input("Reajuste Anual da Tarifa (%)", value=4.5) / 100
    opex_anual_perc = st.number_input("OPEX Anual (% do Capex)", value=1.5) / 100
    tma = st.number_input("Taxa Mínima de Atratividade (TMA) (%)", value=14.5) / 100
    tempo_analise = st.slider("Horizonte de Análise (Anos)", 10, 25, 25)

st.markdown("---")
col3, col4 = st.columns(2)

with col3:
    st.header("🏦 Estrutura de Financiamento")
    usa_financiamento = st.checkbox("Simular Financiamento?")
    if usa_financiamento:
        perc_financiado = st.slider("% Financiado", 10, 100, 80)
        prazo_meses = st.number_input("Prazo do Financiamento (Meses)", value=60)
        taxa_juros_ano = st.number_input("Taxa de Juros Anual (%)", value=12.0) / 100
        carência = st.number_input("Carência (Meses)", value=3)
    else:
        perc_financiado = 0
        prazo_meses = 0
        taxa_juros_ano = 0.0
        carência = 0

with col4:
    st.header("⚖️ Regime Tributário e Depreciação")
    regime = st.selectbox("Regime Tributário", ["Pessoa Física / Associação", "Simples Nacional", "Lucro Presumido", "Lucro Real"])
    
    if regime == "Pessoa Física / Associação":
        aliquota_imposto = 0.0
    elif regime == "Simples Nacional":
        aliquota_imposto = 0.06
    elif regime == "Lucro Presumido":
        aliquota_imposto = 0.1133
    else: 
        aliquota_imposto = 0.34
        
    depreciacao_anos = st.number_input("Prazo de Depreciação do Bem (Anos)", value=10)

# --- CÁLCULOS DO FLUXO DE CAIXA ---
capex = custo_instalacao_total
valor_financiado = capex * (perc_financiado / 100)
aporte_proprio = capex - valor_financiado

parcela_anual_financ = 0
if usa_financiamento:
    taxa_mensal = (1 + taxa_juros_ano)**(1/12) - 1
    parcela_mensal = npf.pmt(taxa_mensal, prazo_meses, -valor_financiado)
    parcela_anual_financ = parcela_mensal * 12

fluxos = []
fluxos.append(-aporte_proprio)

for ano in range(1, tempo_analise + 1):
    tarifa_ano = tarifa_inicial * ((1 + reajuste_tarifa) ** (ano - 1))
    geracao_ano = geracao_anual_inicial * ((1 - degradacao_painel) ** (ano - 1))
    economia_bruta = geracao_ano * tarifa_ano
    
    opex_ano = capex * opex_anual_perc * ((1 + reajuste_tarifa) ** (ano - 1))
    depreciacao_ano = (capex / depreciacao_anos) if ano <= depreciacao_anos else 0
    
    if regime == "Lucro Real":
        base_calculo = max(0, economia_bruta - opex_ano - depreciacao_ano)
        imposto_ano = base_calculo * aliquota_imposto
    else:
        imposto_ano = economia_bruta * aliquota_imposto
        
    custo_financiamento_ano = parcela_anual_financ if (ano <= np.ceil(prazo_meses/12)) else 0
    
    fluxo_liquido = economia_bruta - opex_ano - imposto_ano - custo_financiamento_ano
    fluxos.append(fluxo_liquido)

fluxos = np.array(fluxos)
try:
    tir = npf.irr(fluxos) * 100
except:
    tir = 0

vpl = npf.npv(tma, fluxos)

# --- CÁLCULO DE PAYBACK PRECISO ---
acumulado = np.cumsum(fluxos)
payback = "Superior ao horizonte"

for idx in range(1, len(acumulado)):
    if acumulado[idx] >= 0:
        saldo_negativo_anterior = abs(acumulado[idx - 1])
        caixa_ano_atual = fluxos[idx]
        fracao_ano = saldo_negativo_anterior / caixa_ano_atual
        payback_anos_total = (idx - 1) + fracao_ano
        
        anos_inteiros = int(payback_anos_total)
        meses_restantes = round((payback_anos_total - anos_inteiros) * 12)
        
        if anos_inteiros == 0:
            payback = f"{meses_restantes} meses"
        else:
            payback = f"{anos_inteiros} ano(s) e {meses_restantes} mês(es)"
        break

# --- EXIBIÇÃO DO RESULTADO ---
st.markdown("---")
st.header("📈 Indicadores Prontos de Viabilidade")

m1, m2, m3 = st.columns(3)
m1.metric("Taxa Interna de Retorno (TIR)", f"{tir:.2f} %")
m2.metric("Valor Presente Líquido (VPL)", f"R$ {vpl:,.2f}")
m3.metric("Tempo de Retorno (Payback)", payback)

# --- GRÁFICO DE EVOLUÇÃO PATRIMONIAL ---
st.subheader("📊 Curva de Retorno Financeiro (Saldo Acumulado Ano a Ano)")
anos_grafico = list(range(0, tempo_analise + 1))
cores = ['#EF553B' if v < 0 else '#00CC96' for v in acumulado]

fig = go.Figure(data=[
    go.Bar(
        x=anos_grafico, 
        y=acumulado,
        marker_color=cores,
        hovertemplate="Ano %{x}<br>Saldo Acumulado: R$ %{y:,.2f}<extra></extra>"
    )
])
fig.update_layout(
    xaxis_title="Tempo de Operação (Anos)",
    yaxis_title="Saldo Acumulado do Projeto (R$)",
    template="plotly_white",
    height=400,
    margin=dict(l=20, r=20, t=20, b=20)
)
st.plotly_chart(fig, use_container_width=True)

# Tabela detalhada e Exportação
st.subheader("📋 Detalhamento do Fluxo de Caixa")
df_fluxo = pd.DataFrame({
    "Ano": anos_grafico,
    "Fluxo de Caixa Líquido (R$)": fluxos,
    "Saldo Acumulado (R$)": acumulado
})

st.dataframe(df_fluxo.style.format({
    "Fluxo de Caixa Líquido (R$)": "R$ {:,.2f}",
    "Saldo Acumulado (R$)": "R$ {:,.2f}"
}), use_container_width=True)

# Lógica para converter o dataframe para bytes Excel
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df_fluxo.to_excel(writer, index=False, sheet_name='Fluxo de Caixa')
buffer.seek(0)

st.download_button(
    label="📥 Exportar Fluxo de Caixa para Excel",
    data=buffer,
    file_name="fluxo_caixa_solar.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
