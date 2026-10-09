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

# Estilo visual limpo
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #00d26a;
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
    df = df.sort_values('Close Date DT').reset_index(drop=True)
    
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

# 7. Gráfico da Curva de Patrimônio & Drawdown (Plotly)
st.subheader("📈 Curva de Patrimônio e High Water Mark")

fig = go.Figure()

# Linha do PnL Acumulado
fig.add_trace(go.Scatter(
    x=df['Close Date DT'], 
    y=df['Acumulado'], 
    mode='lines', 
    name='PnL Acumulado ($)',
    line=dict(color='#00d26a', width=2)
))

# Linha do Topo Histórico (High Water Mark)
fig.add_trace(go.Scatter(
    x=df['Close Date DT'], 
    y=df['Max_Historico'], 
    mode='lines', 
    name='Topo Histórico ($)',
    line=dict(color='#ffaa00', width=1.5, dash='dash')
))

fig.update_layout(
    template="plotly_dark",
    height=400,
    margin=dict(l=20, r=20, t=30, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# 8. Tabela de Operações Recentes
st.subheader("📋 Últimas Operações Registradas")
st.dataframe(
    df[['Close Date DT', 'Symbol', 'Side', 'Volume', 'Open Price', 'Close Price', 'Net Realized Profit', 'Acumulado', 'Drawdown']].tail(10),
    use_container_width=True
)