import os
import glob
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import datetime

# 1. Configuração do Layout do Streamlit
st.set_page_config(
    page_title="SFLIM - Dashboard Admin & Gestão de Risco",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo visual
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #00d26a;
    }
    .best-asset {
        background-color: #064e3b;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #10b981;
    }
    .worst-asset {
        background-color: #4c0519;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #f43f5e;
    }
</style>
""", unsafe_allow_html=True)

# 2. Título do Header
st.title("🛡️ SFLIM — Painel Operacional & Telemetria de Risco")
st.caption("Sistema de Monitoramento Contínuo e Gestão de Banca Multicliente")

# 3. Módulo de Carregamento Automático do CSV
@st.cache_data(ttl=60)
def carregar_dados():
    pasta_data = "data"
    arquivos_csv = glob.glob(os.path.join(pasta_data, "*.csv"))
    
    if not arquivos_csv:
        return None
    
    arquivo_mais_recente = max(arquivos_csv, key=os.path.getmtime)
    df = pd.read_csv(arquivo_mais_recente)
    
    df['Close Date DT'] = pd.to_datetime(df['Close Date'])
    df['Open Date DT'] = pd.to_datetime(df['Open Date'])
    df = df.sort_values('Close Date DT').reset_index(drop=True)
    
    dias_map = {
        'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
        'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }
    df['Dia_Semana'] = df['Open Date DT'].dt.day_name().map(dias_map)
    df['Hora_Abertura'] = df['Open Date DT'].dt.hour
    
    df['Acumulado'] = df['Net Realized Profit'].cumsum()
    df['Max_Historico'] = df['Acumulado'].cummax()
    df['Drawdown'] = df['Acumulado'] - df['Max_Historico']
    
    return df, os.path.basename(arquivo_mais_recente)

resultado = carregar_dados()

if resultado is None:
    st.warning("⚠️ Nenhum arquivo CSV encontrado na pasta `data/`. Salve o relatório da plataforma dentro de `data/` para visualizar os dados.")
    st.stop()

df, nome_arquivo = resultado

# 4. Cálculo das Métricas Gerais
total_capital = 4610.40
pnl_acumulado = df['Acumulado'].iloc[-1]
max_historico = df['Max_Historico'].max()
drawdown_atual = df['Drawdown'].iloc[-1]
max_drawdown = df['Drawdown'].min()

win_rate = (df['Net Realized Profit'] > 0).mean() * 100
total_trades = len(df)

if drawdown_atual <= -345.00:
    status_sistema = "🚨 ZONA CRÍTICA"
elif drawdown_atual <= -138.00:
    status_sistema = "⚠️ DRAWDOWN INICIADO"
else:
    status_sistema = "✅ MODO NORMAL (ZONA SEGURA)"

# 5. Barra Lateral (Sidebar)
with st.sidebar:
    st.header("⚙️ Painel de Controle")
    st.info(f"📂 **Arquivo Ativo:**\n`{nome_arquivo}`")
    st.metric("Status Operacional", status_sistema)
    
    st.divider()
    st.subheader("📊 Distribuição de Banca")
    st.text(f"Capital Total: ${total_capital:,.2f}")
    st.caption("• Cliente 1 (59,55%): ~$2.745,49")
    st.caption("• Cliente 2 (21,94%): ~$1.011,52")
    st.caption("• Cliente 3 (18,51%): ~$853,39")
    
    st.divider()
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

# 6. Topo do Dashboard — KPIs em Destaque
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Result. Acumulado ($)", f"${pnl_acumulado:,.2f}", delta=f"{pnl_acumulado/total_capital*100:.1f}%")

with col2:
    st.metric("Topo Histórico ($)", f"${max_historico:,.2f}")

with col3:
    st.metric("Drawdown Atual ($)", f"${drawdown_atual:,.2f}", delta_color="inverse")

with col4:
    st.metric("Taxa de Acerto", f"{win_rate:.1f}%", f"{total_trades} trades")

with col5:
    st.metric("Max Drawdown ($)", f"${max_drawdown:,.2f}")

st.divider()

# 7. BLOCOS DE DESTAQUE INSTANTÂNEO: ATIVO DESTAQUE & CALENDÁRIO
pnl_por_ativo = df.groupby('Symbol')['Net Realized Profit'].sum().sort_values(ascending=False)
melhor_ativo = pnl_por_ativo.index[0]
pnl_melhor_ativo = pnl_por_ativo.iloc[0]

pnl_pior_ativo = pnl_por_ativo.iloc[-1]
pior_ativo = pnl_por_ativo.index[-1]

hoje = datetime.date.today()
inicio_semana = hoje - datetime.timedelta(days=hoje.weekday())
fim_semana = inicio_semana + datetime.timedelta(days=4)

eventos_chave_outubro = [
    {"data": datetime.date(2026, 10, 2), "evento": "US Non-Farm Payroll (NFP)", "horario": "09:30 BRT", "impacto": "🔴 Alto"},
    {"data": datetime.date(2026, 10, 7), "evento": "Ata da Reunião do FOMC (FOMC Minutes)", "horario": "15:00 BRT", "impacto": "🟡 Médio/Alto"},
    {"data": datetime.date(2026, 10, 14), "evento": "US CPI (Inflação ao Consumidor)", "horario": "09:30 BRT", "impacto": "🔴 Alto"},
    {"data": datetime.date(2026, 10, 28), "evento": "Decisão de Juros do Fed (FOMC)", "horario": "15:00 BRT", "impacto": "🔴 Crítico"},
]

# Filtrar eventos que caem na semana atual
eventos_da_semana = [e for e in eventos_chave_outubro if inicio_semana <= e['data'] <= fim_semana]

col_a1, col_a2, col_cal = st.columns([1, 1, 2])

with col_a1:
    st.markdown(f"""
    <div class="best-asset">
        <span style="font-size: 14px; color: #a7f3d0;">🏆 MELHOR ATIVO</span>
        <h2 style="margin: 0; color: #ffffff;">{melhor_ativo}</h2>
        <h3 style="margin: 0; color: #34d399;">+${pnl_melhor_ativo:,.2f} USD</h3>
    </div>
    """, unsafe_allow_html=True)

with col_a2:
    st.markdown(f"""
    <div class="worst-asset">
        <span style="font-size: 14px; color: #fecdd3;">⚠️ PIOR ATIVO (MAIOR DRENO)</span>
        <h2 style="margin: 0; color: #ffffff;">{pior_ativo}</h2>
        <h3 style="margin: 0; color: #fb7185;">${pnl_pior_ativo:,.2f} USD</h3>
    </div>
    """, unsafe_allow_html=True)

with col_cal:
    st.subheader(f"📅 Calendário Econômico — Semana ({inicio_semana.strftime('%d/%m')} a {fim_semana.strftime('%d/%m')})")
    
    if eventos_da_semana:
        for ev in eventos_da_semana:
            st.markdown(f"• **{ev['data'].strftime('%d/%m (%a)')} - {ev['horario']}:** **{ev['evento']}** [{ev['impacto']}]")
    else:
        st.success("✅ **Semana sem divulgação de NFP/CPI de alto impacto direto.** Operação padrão em vigor.")
    
    st.caption("💡 *O sistema calcula automaticamente a janela de segunda a sexta da data atual do seu computador.*")

st.divider()

# 8. Módulo do Agente de IA & Diagnóstico Executivo
with st.expander("🤖 **Relatório e Insights do Agente SFLIM**", expanded=True):
    col_ag1, col_ag2 = st.columns(2)
    
    with col_ag1:
        st.markdown("#### 🚨 Diretrizes Operacionais")
        if status_sistema == "🚨 ZONA CRÍTICA":
            st.error("""
            **SISTEMA EM ZONA CRÍTICA (-$345.00 ou superior)**
            - **Ação:** Modo defensivo ativado. Reduzir o lote base para o mínimo absoluto (0.06).
            - **Restrição:** Proibido abrir novas operações em ativos de alta volatilidade sem confirmação.
            """)
        elif status_sistema == "⚠️ DRAWDOWN INICIADO":
            st.warning("""
            **DRAWDOWN INICIADO (-$138.00 ou superior)**
            - **Ação:** Mantido o lote base obrigatoriamente em **0.06** (sem aumentos para 0.08).
            - **Limite Diário:** Aplicar trava estrita de máximo 2 stops no mesmo dia (-$72.00).
            """)
        else:
            st.success("""
            **MODO NORMAL / ZONA SEGURA**
            - **Ação:** Operação dentro dos parâmetros padrão.
            - **Lote Permitido:** Lote base em 0.06; liberado até 0.08 em ativos menos voláteis (SPXUSD).
            - **Risco Máximo por Trade:** $36.00 por operação (~0,8% da banca).
            """)

    with col_ag2:
        st.markdown("#### 📊 Análise por Ativo")
        st.markdown(f"- **Ativo de Maior Consistência:** `{melhor_ativo}` (Total: **+${pnl_melhor_ativo:,.2f}**)")
        st.markdown(f"- **Ponto de Atenção/Vazamento:** `{pior_ativo}` (Total: **${pnl_pior_ativo:,.2f}**)")
        st.caption("Recomendação: Se o drawdown aproximar-se de $138, suspenda novas entradas no ativo de pior performance.")

st.divider()

# 9. Performance por Ativo (Ranking Completo)
st.subheader("🥇 Ranking de Performance por Ativo")

pnl_por_ativo_df = df.groupby('Symbol')['Net Realized Profit'].sum().reset_index()
pnl_por_ativo_df = pnl_por_ativo_df.sort_values(by='Net Realized Profit', ascending=True)

pnl_por_ativo_df['Cor'] = pnl_por_ativo_df['Net Realized Profit'].apply(lambda x: '#00d26a' if x >= 0 else '#ff355e')

fig_ativo = go.Figure()

fig_ativo.add_trace(go.Bar(
    y=pnl_por_ativo_df['Symbol'],
    x=pnl_por_ativo_df['Net Realized Profit'],
    orientation='h',
    marker=dict(color=pnl_por_ativo_df['Cor']),
    text=pnl_por_ativo_df['Net Realized Profit'].apply(lambda x: f"${x:,.2f}"),
    textposition='auto'
))

# Linha de referência no ZERO
fig_ativo.add_vline(x=0, line_width=1.5, line_color="#ffffff", line_dash="dash")

fig_ativo.update_layout(
    template="plotly_dark",
    height=400,
    xaxis_title="Resultado Acumulado ($)",
    yaxis_title="Ativo / Símbolo",
    margin=dict(l=20, r=20, t=30, b=20),
    showlegend=False
)

st.plotly_chart(fig_ativo, use_container_width=True)

st.divider()

# 10. Matriz Temporal (Performance por Dia da Semana e Horário)
st.subheader("📊 Matriz Temporal de Eficiência")

col_dia, col_hora = st.columns(2)

ordem_dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
pnl_por_dia = df.groupby('Dia_Semana')['Net Realized Profit'].sum().reindex(ordem_dias).dropna()

with col_dia:
    fig_dia = px.bar(
        x=pnl_por_dia.index,
        y=pnl_por_dia.values,
        labels={'x': 'Dia da Semana', 'y': 'Resultado ($)'},
        title="Resultado Acumulado por Dia da Semana",
        color=pnl_por_dia.values,
        color_continuous_scale=['#ff355e', '#00d26a']
    )
    fig_dia.update_layout(template="plotly_dark", showlegend=False, height=300)
    st.plotly_chart(fig_dia, use_container_width=True)

pnl_por_hora = df.groupby('Hora_Abertura')['Net Realized Profit'].sum().reset_index()

with col_hora:
    fig_hora = px.bar(
        pnl_por_hora,
        x='Hora_Abertura',
        y='Net Realized Profit',
        labels={'Hora_Abertura': 'Hora do Dia (BRT)', 'Net Realized Profit': 'Resultado ($)'},
        title="Resultado Acumulado por Faixa Horária",
        color='Net Realized Profit',
        color_continuous_scale=['#ff355e', '#00d26a']
    )
    fig_hora.update_layout(template="plotly_dark", showlegend=False, height=300)
    st.plotly_chart(fig_hora, use_container_width=True)

st.divider()

# 11. Gráfico da Curva de Patrimônio & Drawdown
st.subheader("📈 Curva de Patrimônio e High Water Mark")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df['Close Date DT'], 
    y=df['Acumulado'], 
    mode='lines', 
    name='PnL Acumulado ($)',
    line=dict(color='#00d26a', width=2)
))

fig.add_trace(go.Scatter(
    x=df['Close Date DT'], 
    y=df['Max_Historico'], 
    mode='lines', 
    name='Topo Histórico ($)',
    line=dict(color='#ffaa00', width=1.5, dash='dash')
))

fig.update_layout(
    template="plotly_dark",
    height=350,
    margin=dict(l=20, r=20, t=30, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

# 12. Tabela de Operações Recentes
st.subheader("📋 Últimas Operações Registradas")
st.dataframe(
    df[['Close Date DT', 'Symbol', 'Side', 'Volume', 'Open Price', 'Close Price', 'Net Realized Profit', 'Acumulado', 'Drawdown']].tail(10),
    use_container_width=True
)