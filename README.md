# 🛡️ SFLIM — Dashboard Admin & Gestão de Risco Intraday

> **Sistema de Telemetria Operacional, Diagnóstico Contínuo e Gestão de Banca Multicliente**  
> Parte integrante do ecossistema **SFLIM (Sistema Freitas de Leitura Integrada de Mercado)**.

---

## 📌 Sobre o Projeto

O **SFLIM Dashboard Admin** é uma aplicação de alta performance desenvolvida em Python e Streamlit para monitoramento em tempo real, telemetria de performance e gestão estrita de risco para contas de trading multicliente.

A plataforma automatiza a leitura dos relatórios operacionais (`.csv`), consolida métricas patrimoniais, calcula o estado de rebaixamento (*Drawdown* / *High Water Mark*) e fornece diretrizes automatizadas de risco para garantir a preservação do capital e o alinhamento proporcional entre os aportes dos clientes.

---

## 🎯 Funcionalidades Principais

- 📊 **Monitoramento Patrimonial & High Water Mark:** Acompanhamento da curva de patrimônio acumulado e topo histórico.
- 🛡️ **Matriz Dinâmica de Gestão de Risco:**
  - Status em tempo real (`MODO NORMAL`, `DRAWDOWN INICIADO` e `ZONA CRÍTICA`).
  - Trava automática de segurança e limites de stop diário.
- 🥇 **Ranking de Performance por Ativo:** Diagnóstico instantâneo dos ativos mais lucrativos e pontos de vazamento de capital.
- 📊 **Matriz Temporal de Eficiência:** Análise detalhada por dia da semana e faixa horária de abertura das posições.
- 🤖 **Agente SFLIM de Insights:** Relatório com diretrizes operacionais e alertas de calendário econômico de alto impacto.
- 👥 **Gestão Multicliente Proporcional:** Algoritmo ajustado para alocação de lotes respeitando as cotas de participação da banca.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.10+
- **Interface & Dashboard:** Streamlit
- **Processamento de Dados:** Pandas / NumPy
- **Visualização Gráfica:** Plotly Express / Plotly Graph Objects
- **Controle de Versão:** Git & GitHub

---

## ⚙️ Estrutura da Banca & Parâmetros de Risco

### 💰 Alocação de Capital 
- **Lote Mínimo Base:** `0.06` *(Garante a participação mínima do Cliente 3)*

### 🛡️ Limites de Risco
| Parâmetro | Valor ($ / %) | Ação Automática |
| :--- | :---: | :--- |
| **Risco por Trade** | $36,00 (~0,8%) | Stop Loss recomendado por operação |
| **Limite Diário** | $92,00 (~2,0%) | Trava de no máximo 2 a 3 stops no dia |
| **Drawdown Iniciado** | -$138,00 (-3,0%) | Bloqueio de aumento de lote (Mantém 0.06) |
| **Zona Crítica** | -$345,00 (-7,5%) | Ativação do modo defensivo / Pausa técnica |

---

## 🚀 Como Executar o Projeto Localmente

### 1. Clonar o repositório
```bash
git clone [https://github.com/rodrigo-dias-freitas/sflim_dashboard_admin.git](https://github.com/rodrigo-dias-freitas/sflim_dashboard_admin.git)
cd sflim_dashboard_admin
```

### 2. Criar e ativar o ambiente virtual
```bash
python -m venv .venv

# No Windows (PowerShell):
.venv\Scripts\Activate.ps1

# No Linux/Mac:
source .venv/bin/activate
```

### 3. Instalar as dependências
```bash
pip install -r requirements.txt
```

### 4. Adicionar os dados operacionais
Crie uma pasta chamada data/ na raiz do projeto e insira o seu arquivo .csv baixado da plataforma de trading:
```bash
mkdir data
```

### 5. Executar a aplicação
```bash
python -m streamlit run app.py
```

    O dashboard será aberto automaticamente no seu navegador em http://localhost:8501.

## 📁 Estrutura do Repositório

sflim_dashboard_admin/
├── .venv/               # Ambiente virtual Python (ignorado pelo Git)
├── data/                # Pasta de armazenamento dos relatórios CSV (ignorado pelo Git)
├── app.py               # Código-fonte principal do Dashboard Streamlit
├── requirements.txt     # Lista de dependências do projeto
├── .gitignore           # Regras de exclusão de arquivos sensíveis
└── README.md            # Documentação técnica do projeto

## 🔒 Segurança e Privacidade

Este repositório foi estruturado seguindo os melhores padrões de privacidade:

Arquivos .csv com históricos de operações e dados financeiros dos clientes são ignorados pelo Git e permanecem estritamente locais.

Suporte nativo para variáveis de ambiente e autenticação de acesso restrito.

## 📄 License

MIT License

---

## 👨‍💻 Author

Rodrigo Freitas  
Excent partner trader | Financial Planner | Frontend Developer

---
