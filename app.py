import os
import glob
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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
    .agent-box {
        background-color: #111827;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #374151;
        margin-bottom: 25px;
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
    
    # Pega o arquivo CSV mais recente da pasta 'data'
    arquivo_mais_recente = max(arquivos_csv, key=os.path.getmtime)
    df = pd.read_csv(arquivo_mais_recente)
    
    # Tratamento básico de colunas e datas
    df['Close Date DT'] = pd.to_datetime(df['Close Date'])
    df['Open Date DT'] = pd.to_datetime(df['Open Date'])
    df = df.sort_values('Close Date DT').reset_index(drop=True)
    
    # Extração de Dia da Semana e Hora de Abertura
    dias_map = {
        'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
        'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }
    df['Dia_Semana'] = df['Open Date DT'].dt.day_name().map(dias_map)
    df['Hora_Abertura'] = df['Open Date DT'].dt.hour
    
    # Cálculos das métricas acumuladas
    df['Acumulado'] = df['Net Realized Profit'].cumsum()
    df['Max_Historico'] = df['Acumulado'].cummax()
    df['Drawdown'] = df['Acumulado'] - df['Max_Historico']
    
    return df, os.path.basename(arquivo_mais_recente)

# Executa carregamento
resultado = carregar_dados()

if resultado is None:
    st.warning("⚠️ Nenhum arquivo CSV encontrado na pasta `data/`. Salve o relatório da plataforma dentro de `data/` para visualizar os dados.")
    st.stop()

df, nome_arquivo = resultado

# 4. Cálculo das Métricas de Risco do Sistema
total_capital = 4610.40
pnl_acumulado = df['Acumulado'].iloc[-1]
max_historico = df['Max_Historico'].max()
drawdown_atual = df['Drawdown'].iloc[-1]
max_drawdown = df['Drawdown'].min()

win_rate = (df['Net Realized Profit'] > 0).mean() * 100
total_trades = len(df)

# Definição do Status do Sistema com base nas regras
if drawdown_atual <= -345.00:
    status_sistema = "🚨 ZONA CRÍTICA"
    cor_status = "red"
elif drawdown_atual <= -138.00:
    status_sistema = "⚠️ DRAWDOWN INICIADO"
    cor_status = "orange"
else:
    status_sistema = "✅ MODO NORMAL (ZONA SEGURA)"
    cor_status = "green"

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

# 6. Topo do Dashboard — KPIs em Destaque (Cards)
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

# 7. Módulo do Agente de IA & Diagnóstico Executivo
with st.expander("🤖 **Relatório e Insights do Agente SFLIM**", expanded=True):
    st.subheader("📋 Diagnóstico do Co-Piloto de Risco")
    
    col_ag1, col_ag2 = st.columns(2)
    
    with col_ag1:
        st.markdown("#### 🚨 Diretrizes Operacionais")
        if status_sistema == "🚨 ZONA CRÍTICA":
            st.error("""
            **SISTEMA EM ZONA CRÍTICA (-$345.00 ou superior)**
            - **Ação:** Modo defensivo ativado. Reduzir o lote base para o mínimo absoluto (0.06).
            - **Restrição:** Proibido abrir novas operações em ativos de alta volatilidade (NDXUSD / XAUUSD) sem confirmação dupla.
            - **Pausa:** Considerar pausa de 24h a 48h para reavaliação de estratégia.
            """)
        elif status_sistema == "⚠️ DRAWDOWN INICIADO":
            st.warning("""
            **DRAWDOWN INICIADO (-$138.00 ou superior)**
            - **Ação:** Rebaixamento em relação ao topo histórico ativado.
            - **Restrição:** Mantido o lote base obrigatoriamente em **0.06** (sem aumentos para 0.08).
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
        st.markdown("#### 📅 Alerta de Calendário & Filtro Temporal")
        
        # Filtro de Sexta-feira
        pnl_sextas = df[df['Dia_Semana'] == 'Sexta']['Net Realized Profit'].sum()
        
        st.info(f"""
        **Regra de Sexta-feira:**
        - **Resultado Histórico nas Sextas:** `${pnl_sextas:,.2f}`
        - **Diretriz Padrão:** **NÃO OPERAR** nas sextas-feiras comuns.
        - **Exceção Exclusiva:** Liberado apenas em sextas com divulgação do **Payroll (NFP)** ou **CPI**, na janela das 09:30h às 11:00h BRT, com lote fixo em **0.06**.
        - **Horários Proibidos:** Madrugada (22:00h às 04:59h BRT) bloqueada permanentemente.
        """)

st.divider()

# 8. Gráfico da Curva de Patrimônio & Drawdown
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
    height=380,
    margin=dict(l=20, r=20, t=30, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

# 9. Matriz Temporal (Performance por Dia da Semana e Horário)
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
    fig_dia.update_layout(template="plotly_dark", showlegend=False, height=320)
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
    fig_hora.update_layout(template="plotly_dark", showlegend=False, height=320)
    st.plotly_chart(fig_hora, use_container_width=True)

st.divider()

# 10. Tabela de Operações Recentes
st.subheader("📋 Últimas Operações Registradas")
st.dataframe(
    df[['Close Date DT', 'Symbol', 'Side', 'Volume', 'Open Price', 'Close Price', 'Net Realized Profit', 'Acumulado', 'Drawdown']].tail(10),
    use_container_width=True
)