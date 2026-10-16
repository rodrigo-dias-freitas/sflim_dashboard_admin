import os
import glob
import datetime
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Opcional para busca de cotações globais
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

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
    .macro-card {
        background-color: #111827;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #374151;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


def classificar_tendencia(atual, anterior, tolerancia=0.05):
    diff = atual - anterior
    if diff > tolerancia:
        return "Subindo ↗", "#38bdf8"
    elif diff < -tolerancia:
        return "Descendo ↘", "#f43f5e"
    else:
        return "Estável ➡️", "#facc15"

def classificar_ces(payroll_k):
    if payroll_k >= 150:
        return "Forte 💪", "#34d399"
    elif payroll_k <= 80:
        return "Fraco ⚠️", "#f43f5e"
    else:
        return "Estável ⚖️", "#facc15"


def calcular_tom_fed(pce, ism, ces, unemployment):
    score = 0.0
    
    # 1. PCE (Inflação)
    if pce == "SUBINDO": score += 2.0
    elif pce == "DESCENDO": score -= 2.0
        
    # 2. ISM (Atividade)
    if ism == "SUBINDO": score += 1.0
    elif ism == "DESCENDO": score -= 1.0
        
    # 3. CES (Emprego)
    if ces == "FORTE": score += 1.5
    elif ces == "FRACO": score -= 1.5
        
    # 4. Taxa de Desemprego (Invertido: Desemprego Caindo = Economia Forte/Hawkish)
    if unemployment == "DESCENDO": score += 1.0
    elif unemployment == "SUBINDO": score -= 1.0
        
    # Classificação Final
    if score >= 1.5:
        return "HAWKISH 🦅", "#ef4444", "Viés de Manutenção/Aumento de Juros (Pressão nos Índices)"
    elif score <= -1.5:
        return "DOVISH 🕊️", "#10b981", "Viés de Corte de Juros (Favorável a Riscos/Ouro)"
    else:
        return "NEUTRAL ⚖️", "#f59e0b", "Tom Neutro / Dependente de Dados Próximos"

def card_drawdown_custom(drawdown_atual, status_sistema, direcao_txt, cor_texto):
    return f"""
    <div style="background-color: #1e1e1e; padding: 12px; border-radius: 8px; border-left: 4px solid {cor_texto};">
        <span style="color: #9ca3af; font-size: 13px; font-weight: 500;">Drawdown Atual ($)</span>
        <h2 style="margin: 4px 0; color: #ffffff; font-size: 26px;">${drawdown_atual:,.2f}</h2>
        <div style="font-size: 13px; font-weight: bold; color: {cor_texto}; display: flex; justify-content: space-between;">
            <span>{status_sistema}</span>
            <span>{direcao_txt}</span>
        </div>
    </div>
    """

@st.cache_data(ttl=300) # Atualiza a cada 5 minutos
def obter_suportes_resistencias(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        df_hist = ticker.history(period="5d", interval="1d")
        
        if df_hist.empty:
            return None
        
        # Pega a máxima, mínima e fechamento do dia anterior
        high = df_hist['High'].iloc[-2]
        low = df_hist['Low'].iloc[-2]
        close = df_hist['Close'].iloc[-2]
        preco_atual = df_hist['Close'].iloc[-1]
        
        # Cálculo de Pivot Points Clássicos
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        
        return {
            "atual": preco_atual,
            "pivot": pivot,
            "r1": r1, "r2": r2,
            "s1": s1, "s2": s2,
            "pdh": high, "pdl": low
        }
    except Exception:
        return None

# 2. Título do Header
st.title("🛡️ SFLIM — Painel Operacional & Telemetria de Risco")
st.caption("Sistema de Monitoramento Contínuo e Gestão de Banca Multicliente")

# 3. Módulo de Carregamento Automático do CSV (Blindado contra Cache)
@st.cache_data(ttl=5) # TTL reduzido para expirar rapidamente ou forçar leitura
def carregar_dados():
    pasta_data = "data"
    arquivos_csv = glob.glob(os.path.join(pasta_data, "*.csv"))
    
    if not arquivos_csv:
        return None
    
    # Pega o arquivo CSV mais recente da pasta 'data' pelo horário de modificação
    arquivo_mais_recente = max(arquivos_csv, key=os.path.getmtime)
    
    # Lê o CSV sem cache interno agressivo do pandas
    df = pd.read_csv(arquivo_mais_recente)
    
    # Garante que remove linhas totalmente vazias se houverem
    df = df.dropna(subset=['Net Realized Profit'])
    
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

# 1. Função de Busca Automática nas Séries Oficiais (FRED / Banco Central)
@st.cache_data(ttl=1800)
def buscar_indicadores_core():
    def pegar_taxa_pce_fred():
        try:
            # Série do Índice de Preços PCE (PCEPI)
            url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=PCEPI"
            df = pd.read_csv(url)
            df.columns = ['Data', 'Valor']
            df = df[df['Valor'] != '.'].copy()
            df['Valor'] = df['Valor'].astype(float)
            
            # O PCE YoY é a variação percentual dos últimos 12 meses
            df['PCE_YoY'] = df['Valor'].pct_change(12) * 100
            
            atual = df['PCE_YoY'].iloc[-1]
            anterior = df['PCE_YoY'].iloc[-2]
            
            return round(atual, 1), round(anterior, 1)
        except Exception:
            return 2.6, 2.5 # Fallback seguro

    def pegar_dado_fred(serie_id, fator_multiplicador=1.0):
        try:
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={serie_id}"
            df = pd.read_csv(url)
            df.columns = ['Data', 'Valor']
            df = df[df['Valor'] != '.'].copy()
            df['Valor'] = df['Valor'].astype(float) * fator_multiplicador
            
            atual = df['Valor'].iloc[-1]
            anterior = df['Valor'].iloc[-2]
            
            return round(atual, 1), round(anterior, 1)
        except Exception:
            return None, None

    # Chamada correta para o PCE em percentual YoY
    pce_val, pce_ant = pegar_taxa_pce_fred()
    unemp_val, unemp_ant = pegar_dado_fred('UNRATE')
    
    pce_val = pce_val if pce_val else 2.6
    pce_ant = pce_ant if pce_ant else 2.5
    
    ism_val, ism_ant = 54.5, 54.6 
    ces_k = 29                     
    
    unemp_val = unemp_val if unemp_val else 4.1
    unemp_ant = unemp_ant if unemp_ant else 4.2

    txt_pce, cor_pce = classificar_tendencia(pce_val, pce_ant, 0.1)
    txt_ism, cor_ism = classificar_tendencia(ism_val, ism_ant, 0.1)
    txt_ces, cor_ces = classificar_ces(ces_k)
    txt_unemp, cor_unemp = classificar_tendencia(unemp_val, unemp_ant, 0.1)
    
    return {
        "pce": (f"{pce_val}%", txt_pce, cor_pce),
        "ism": (f"{ism_val}", txt_ism, cor_ism),
        "ces": (f"{ces_k}k", txt_ces, cor_ces),
        "unemployment": (f"{unemp_val}%", txt_unemp, cor_unemp)
    }
# --- RENDERIZAÇÃO NO STREAMLIT (EXATAMENTE COMO ESTAVAM OS BLOCOS) ---
st.subheader("🌐 Radar Macroeconômico Core (EUA)")
indicators = buscar_indicadores_core()

c1, c2, c3, c4 = st.columns(4)

with c1:
    val, txt, cor = indicators["pce"]
    st.markdown(f"""
    <div style="background-color: #111827; padding: 15px; border-radius: 8px; border: 1px solid #374151; text-align: center;">
        <span style="color: #9ca3af; font-size: 13px;">INFLAÇÃO PCE</span>
        <h2 style="margin: 5px 0; color: #ffffff;">{val}</h2>
        <span style="color: {cor}; font-weight: bold; font-size: 15px;">{txt}</span>
    </div>
    """, unsafe_allow_html=True)

with c2:
    val, txt, cor = indicators["ism"]
    st.markdown(f"""
    <div style="background-color: #111827; padding: 15px; border-radius: 8px; border: 1px solid #374151; text-align: center;">
        <span style="color: #9ca3af; font-size: 13px;">ISM MANUFACTURING</span>
        <h2 style="margin: 5px 0; color: #ffffff;">{val}</h2>
        <span style="color: {cor}; font-weight: bold; font-size: 15px;">{txt}</span>
    </div>
    """, unsafe_allow_html=True)

with c3:
    val, txt, cor = indicators["ces"]
    st.markdown(f"""
    <div style="background-color: #111827; padding: 15px; border-radius: 8px; border: 1px solid #374151; text-align: center;">
        <span style="color: #9ca3af; font-size: 13px;">EMPREGO CES (PAYROLL)</span>
        <h2 style="margin: 5px 0; color: #ffffff;">{val}</h2>
        <span style="color: {cor}; font-weight: bold; font-size: 15px;">{txt}</span>
    </div>
    """, unsafe_allow_html=True)

with c4:
    val, txt, cor = indicators["unemployment"]
    st.markdown(f"""
    <div style="background-color: #111827; padding: 15px; border-radius: 8px; border: 1px solid #374151; text-align: center;">
        <span style="color: #9ca3af; font-size: 13px;">TAXA DE DESEMPREGO</span>
        <h2 style="margin: 5px 0; color: #ffffff;">{val}</h2>
        <span style="color: {cor}; font-weight: bold; font-size: 15px;">{txt}</span>
    </div>
    """, unsafe_allow_html=True)

# Extração dos status para alimentar a matriz do FED
pce_val = indicators["pce"][1].split()[0]      # Pega "Subindo", "Descendo" ou "Estável"
ism_val = indicators["ism"][1].split()[0]
ces_val = "FRACO" if "Fraco" in indicators["ces"][1] else "FORTE"
unemp_val = indicators["unemployment"][1].split()[0]

tom, cor_fundo, desc = calcular_tom_fed(pce_val, ism_val, ces_val, unemp_val)

f1, f2 = st.columns(2)

with f1:
    # RENDERIZAÇÃO DA TABELA VISUAL DO TOM DO FED
    st.subheader("🌐 Provável Tom do FED")

    st.markdown(f"""
    <div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #374151; max-width: 450px;">
        <div style="background-color: {cor_fundo}; color: #ffffff; text-align: center; font-weight: bold; font-size: 20px; padding: 12px; margin-top: 5px; border-radius: 6px;">
            {tom}
        </div>
        <p style="text-align: center; font-size: 12px; color: #9ca3af; margin-top: 8px; margin-bottom: 0;">
            {desc}
        </p>
    </div>
    """, unsafe_allow_html=True)
with f2:
# --- MÓDULO DE OPORTUNIDADES OPERACIONAIS BASEADAS NO TOM DO FED ---
    st.subheader("💡 Oportunidades & Direcionamento para os Seus Ativos")
    # Extrai o tom atual com base na matriz calculada anteriormente
    tom_atual = tom.split()[0]  # Pega "HAWKISH", "DOVISH" ou "NEUTRAL"

    if "DOVISH" in tom_atual:
        st.markdown("""
        <div style="background-color: #064e3b; padding: 15px; border-radius: 8px; border-left: 5px solid #10b981; margin-bottom: 15px;">
            <h4 style="margin: 0; color: #34d399;">🕊️ Cenário Favorável ao Risco (Risk-On)</h4>
            <p style="margin: 8px 0 0 0; color: #e5e7eb; font-size: 14px;">
                • <b>Ouro (XAUUSD):</b> Viés predominantemente comprador. Busque correções até suportes (S1/S2) para entrada.<br>
                • <b>Nasdaq & S&P 500 (NDXUSD / SPXUSD):</b> Ambiente amigável para alta. Menor pressão vendedora em ativos de crescimento.<br>
                • <b>Recomendação do Agente:</b> Liberado o lote padrão de operação, respeitando sempre o gerenciamento de risco da banca.
            </p>
        </div>
        """, unsafe_allow_html=True)

    elif "HAWKISH" in tom_atual:
        st.markdown("""
        <div style="background-color: #4c0519; padding: 15px; border-radius: 8px; border-left: 5px solid #f43f5e; margin-bottom: 15px;">
            <h4 style="margin: 0; color: #f87171;">🦅 Cenário Defensivo / Aperto Monetário (Risk-Off)</h4>
            <p style="margin: 8px 0 0 0; color: #e5e7eb; font-size: 14px;">
                • <b>Índices (NDXUSD / SPXUSD):</b> Cautela máxima. Risco de forte volatilidade e reversões em resistências (R1/R2).<br>
                • <b>Ouro (XAUUSD):</b> Pressão dos rendimentos dos títulos (Yields). Operações exigem alvos mais curtos.<br>
                • <b>Recomendação do Agente:</b> Ativar modo defensivo se a conta estiver em drawdown. Restringir lotes e evitar alavancagem excessiva.
            </p>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.markdown("""
        <div style="background-color: #451a03; padding: 15px; border-radius: 8px; border-left: 5px solid #fbbf24; margin-bottom: 15px;">
            <h4 style="margin: 0; color: #fbbf24;">⚖️ Cenário Neutro / Dependente de Dados</h4>
            <p style="margin: 8px 0 0 0; color: #e5e7eb; font-size: 14px;">
                • <b>Ativos Operados (XAUUSD, NDXUSD, SPXUSD):</b> O mercado opera sem direcional macroeconômico claro.<br>
                • <b>Estratégia Recomendada:</b> Foco total na <b>Análise Técnica Pura</b> (Pivot Points, Suportes e Resistências).<br>
                • <b>Recomendação do Agente:</b> Respeitar estritamente os limites operacionais e aguardar testes nos extremos dos gráficos.
            </p>
        </div>
        """, unsafe_allow_html=True)

# --- MÓDULO DE INDICADORES DA CHINA AUTOMATIZADOS ---
@st.cache_data(ttl=1800)
def buscar_indicadores_china():
    def pegar_pib_banco_mundial():
        try:
            # API oficial do Banco Mundial para o crescimento real do PIB da China (CHN)
            url = "http://api.worldbank.org/v2/country/CHN/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=5"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                records = [r for r in data[1] if r['value'] is not None]
                if records:
                    records.sort(key=lambda x: x['date'], reverse=True)
                    atual = round(float(records[0]['value']), 1)
                    anterior = round(float(records[1]['value']), 1)
                    return atual, anterior
        except Exception:
            pass
        return 4.8, 4.7 # Fallback seguro caso esteja offline

    # Busca o PIB automático via API
    pib_val, pib_ant = pegar_pib_banco_mundial()
    
    # PMI de Manufatura da China (Valor oficial de referência ou projeção atualizada)
    pmi_val, pmi_ant = 49.8, 49.1

    # Processa as tendências automaticamente
    txt_pib, cor_pib = classificar_tendencia(pib_val, pib_ant, 0.1)
    txt_pmi, cor_pmi = classificar_tendencia(pmi_val, pmi_ant, 0.1)
    
    return {
        "pib": (f"{pib_val}%", txt_pib, cor_pib),
        "pmi": (f"{pmi_val}", txt_pmi, cor_pmi)
    }

# --- RENDERIZAÇÃO NO STREAMLIT: CHINA DINÂMICA ---
st.subheader("🇨🇳 Radar Macroeconômico — China (PIB & PMI)")
china_data = buscar_indicadores_china()

c_china1, c_china2 = st.columns(2)

with c_china1:
    pib_str, txt_pib, cor_pib = china_data["pib"]
    st.markdown(f"""
    <div style="background-color: #111827; padding: 15px; border-radius: 8px; border: 1px solid #374151; text-align: center;">
        <span style="color: #9ca3af; font-size: 13px;">PIB DA CHINA (GDP YoY)</span>
        <h2 style="margin: 5px 0; color: #ffffff;">{pib_str}</h2>
        <span style="color: {cor_pib}; font-weight: bold; font-size: 15px;">{txt_pib}</span>
    </div>
    """, unsafe_allow_html=True)

with c_china2:
    pmi_str, txt_pmi, cor_pmi = china_data["pmi"]
    st.markdown(f"""
    <div style="background-color: #111827; padding: 15px; border-radius: 8px; border: 1px solid #374151; text-align: center;">
        <span style="color: #9ca3af; font-size: 13px;">PMI MANUFATURA (CHINA)</span>
        <h2 style="margin: 5px 0; color: #ffffff;">{pmi_str}</h2>
        <span style="color: {cor_pmi}; font-weight: bold; font-size: 15px;">{txt_pmi}</span>
    </div>
    """, unsafe_allow_html=True)

# --- EXTRAÇÃO NUMÉRICA PARA LÓGICA CONDICIONAL ---
try:
    pib_num = float(pib_str.replace('%', ''))
    pmi_num = float(pmi_str)
except ValueError:
    pib_num, pmi_num = 4.8, 49.8

# --- ANÁLISE DINÂMICA DE OPORTUNIDADES (ESTILO TOM DO FED) ---
st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

if pmi_num >= 50.0 and pib_num >= 4.8:
    # Cenário de Expansão e Aceleração Chinesa
    st.markdown("""
    <div style="background-color: #064e3b; padding: 16px; border-radius: 8px; border-left: 5px solid #10b981;">
        <h4 style="margin: 0; color: #34d399;">🐉 Expansão Econômica na China (Forte Demanda Global)</h4>
        <div style="margin-top: 10px; font-size: 14px; color: #e5e7eb; line-height: 1.6;">
            <b>🎯 Ativos que Você Já Opera:</b><br>
            • <b>Ouro (XAUUSD):</b> Impulso de alta por forte demanda física e industrial asiática. Favorável a compras em correções.<br>
            • <b>Índices (NDXUSD / SPXUSD):</b> Favorece o apetite global por risco (<i>Risk-On</i>), beneficiando ações de tecnologia com exposição à China.<br><br>
            <b>🌐 Outros Ativos com Oportunidades Claras:</b><br>
            • <b>Forex (AUDUSD / NZDUSD):</b> Forte tendência compradora (Austrália é a maior fornecedora de minério/energia para a China).<br>
            • <b>Commodities Industriais:</b> Cobre (HG=F) e Petróleo (CL=F) com forte viés altista.
        </div>
    </div>
    """, unsafe_allow_html=True)

elif pmi_num < 50.0 and pib_num < 4.5:
    # Cenário de Desaceleração / Contração
    st.markdown("""
    <div style="background-color: #4c0519; padding: 16px; border-radius: 8px; border-left: 5px solid #f43f5e;">
        <h4 style="margin: 0; color: #f87171;">⚠️ Contração Manufatureira na China (Pressão Macro)</h4>
        <div style="margin-top: 10px; font-size: 14px; color: #e5e7eb; line-height: 1.6;">
            <b>🎯 Ativos que Você Já Opera:</b><br>
            • <b>Ouro (XAUUSD):</b> Atenção a suporte. A queda do consumo industrial compensa parcialmente a busca por proteção.<br>
            • <b>Índices (NDXUSD / SPXUSD):</b> Cautela em empresas com alta dependência na cadeia de suprimentos chinesa.<br><br>
            <b>🌐 Outros Ativos com Oportunidades Claras:</b><br>
            • <b>Forex (AUDUSD / NZDUSD):</b> Pressão vendedora e tendência de baixa nestes pares.<br>
            • <b>Commodities Industriais:</b> Cobre e Petróleo tendem a registrar correções acentuadas.
        </div>
    </div>
    """, unsafe_allow_html=True)

else:
    # Cenário Moderado / Misto (PMI próximo a 49-50)
    st.markdown("""
    <div style="background-color: #451a03; padding: 16px; border-radius: 8px; border-left: 5px solid #fbbf24;">
        <h4 style="margin: 0; color: #fbbf24;">⚖️ Transição Econômica na China (Atividade Moderada)</h4>
        <div style="margin-top: 10px; font-size: 14px; color: #e5e7eb; line-height: 1.6;">
            <b>🎯 Ativos que Você Já Opera:</b><br>
            • <b>Ouro (XAUUSD):</b> Sem direcionamento único da China. Foco total nos drivers do FED e juros norte-americanos (Yields).<br>
            • <b>Índices (NDXUSD / SPXUSD):</b> Operar estritamente dentro das zonas de <b>Pivot Points (Suportes e Resistências)</b>.<br><br>
            <b>🌐 Outros Ativos com Oportunidades Claras:</b><br>
            • <b>Forex (AUDUSD / NZDUSD):</b> Dê preferência a operações de amplitude gráfica (consolidação) e níveis técnicos claros.
        </div>
    </div>
    """, unsafe_allow_html=True)


# Executa carregamentos
resultado_trade = carregar_dados()
macro_data = buscar_indicadores_core()

if resultado_trade is None:
    st.warning("⚠️ Nenhum arquivo CSV encontrado na pasta `data/`. Salve o relatório da plataforma dentro de `data/` para visualizar os dados.")
    st.stop()

df, nome_arquivo = resultado_trade

# 5. Cálculo das Métricas Gerais de Risco
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

# 6. Barra Lateral (Sidebar)
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


st.divider()

# 8. Topo do Dashboard — KPIs de Risco da Banca
drawdown_anterior = df['Drawdown'].iloc[-2] if len(df) > 1 else drawdown_atual
variacao_dd = drawdown_atual - drawdown_anterior

if variacao_dd < 0:
    direcao_txt = "↘ Piorando"
elif variacao_dd > 0:
    direcao_txt = "↗ Recuperando"
else:
    direcao_txt = "➡️ Estável"

# 2. Define o status e as cores dinâmicas do card
if drawdown_atual <= -345.00:
    status_sistema = "🚨 ZONA CRÍTICA"
    cor_bg = "#4c0519"     # Vermelho escuro
    cor_texto = "#f87171"  # Vermelho claro
elif drawdown_atual <= -138.00:
    status_sistema = "⚠️ DRAWDOWN INICIADO"
    cor_bg = "#451a03"     # Laranja escuro
    cor_texto = "#fbbf24"  # Laranja claro
else:
    status_sistema = "✅ MODO NORMAL"
    cor_bg = "#064e3b"     # Verde escuro
    cor_texto = "#34d399"  # Verde claro
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Result. Acumulado ($)", f"${pnl_acumulado:,.2f}", delta=f"{pnl_acumulado/total_capital*100:.1f}%")

with col2:
    st.metric("Topo Histórico ($)", f"${max_historico:,.2f}")

with col3:
    st.markdown(
        card_drawdown_custom(drawdown_atual, status_sistema, direcao_txt, cor_texto), 
        unsafe_allow_html=True
    )
    
with col4:
    st.metric("Taxa de Acerto", f"{win_rate:.1f}%", f"{total_trades} trades")

with col5:
    st.metric("Max Drawdown ($)", f"${max_drawdown:,.2f}")

st.divider()

# 9. BLOCOS DE DESTAQUE INSTANTÂNEO: ATIVO DESTAQUE & CALENDÁRIO
pnl_por_ativo = df.groupby('Symbol')['Net Realized Profit'].sum().sort_values(ascending=False)
melhor_ativo = pnl_por_ativo.index[0]
pnl_melhor_ativo = pnl_por_ativo.iloc[0]

pnl_pior_ativo = pnl_por_ativo.iloc[-1]
pior_ativo = pnl_por_ativo.index[-1]

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

# Cálculo dinâmico da semana atual
hoje = datetime.date.today()
inicio_semana = hoje - datetime.timedelta(days=hoje.weekday())
fim_semana = inicio_semana + datetime.timedelta(days=4)

with col_cal:
    st.subheader(f"📅 Calendário da Semana ({inicio_semana.strftime('%d/%m')} a {fim_semana.strftime('%d/%m')})")
    st.info("""
    • **Quarta-feira (15:00h BRT):** Decisão de Juros / FOMC  
    • **Sexta-feira (09:30h BRT):** Non-Farm Payroll (NFP)  
    *Diretriz:* Nas sextas com NFP/CPI, operação liberada exclusivamente das 09:30h às 11:00h BRT com lote fixo 0.06.
    """)

st.divider()

# 10. Módulo do Agente de IA & Diagnóstico Executivo
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

# --- RENDERIZAÇÃO NO STREAMLIT ---
st.subheader("🎯 Níveis de Suporte & Resistência (Pivot Points)")

ativo_selecionado = st.selectbox("Selecione o Ativo:", ["^GSPC", "^NDX", "^TSLA", "^SPCX"], format_func=lambda x: {"^GSPC": "S&P 500 (SPXUSD)", "^NDX": "Nasdaq (NDXUSD)", "^TSLA": "Tesla", "^SPCX": "Space X"}[x])

dados_sr = obter_suportes_resistencias(ativo_selecionado)

if dados_sr:
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        st.metric("Resistência 2 (R2)", f"{dados_sr['r2']:,.2f}")
    with c2:
        st.metric("Resistência 1 (R1)", f"{dados_sr['r1']:,.2f}")
    with c3:
        st.metric("Pivot Point (P)", f"{dados_sr['pivot']:,.2f}", delta=f"Preço Atual: {dados_sr['atual']:,.2f}")
    with c4:
        st.metric("Suporte 1 (S1)", f"{dados_sr['s1']:,.2f}")
    with c5:
        st.metric("Suporte 2 (S2)", f"{dados_sr['s2']:,.2f}")

# 11. Performance por Ativo (Ranking Completo Corrigido)
st.subheader("🥇 Ranking de Performance por Ativo")

pnl_por_ativo_df = df.groupby('Symbol')['Net Realized Profit'].sum().reset_index()
pnl_por_ativo_df = pnl_por_ativo_df.sort_values(by='Net Realized Profit', ascending=True)

pnl_por_ativo_df['Cor'] = pnl_por_ativo_df['Net Realized Profit'].apply(
    lambda x: '#00d26a' if x >= 0 else '#ff355e'
)

fig_ativo = go.Figure()

fig_ativo.add_trace(go.Bar(
    y=pnl_por_ativo_df['Symbol'],
    x=pnl_por_ativo_df['Net Realized Profit'],
    orientation='h',
    marker=dict(color=pnl_por_ativo_df['Cor']),
    text=pnl_por_ativo_df['Net Realized Profit'].apply(lambda x: f"${x:,.2f}"),
    textposition='auto'
))

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

# 12. Matriz Temporal (Performance por Dia da Semana e Horário)
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

# 13. Gráfico da Curva de Patrimônio & Drawdown
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

# 14. Tabela de Operações Recentes
st.subheader("📋 Últimas Operações Registradas")
st.dataframe(
    df[['Close Date DT', 'Symbol', 'Side', 'Volume', 'Open Price', 'Close Price', 'Net Realized Profit', 'Acumulado', 'Drawdown']].tail(10),
    use_container_width=True
)