# Plataforma de Engenharia de Dados, ML & Visualização - Mercado Binance

Plataforma ponta a ponta (End-to-End) para coleta automatizada, armazenamento persistente, previsão de preços com Machine Learning e exibição de indicadores do mercado de criptomoedas através de dashboards interativos.

**Evolução do Projeto:** O sistema nasceu como um pipeline local de Análise Exploratória de Dados (EDA) focado em logs de terminal e planilhas CSV. A arquitetura atual transforma esse escopo inicial em um ecossistema robusto de dados baseado em microsserviços, APIs REST e automação via CI/CD.

---

## Arquitetura do Sistema

O projeto adota o modelo de **Monorepo**, segregando responsabilidades desde a coleta diária até a entrega de valor na interface do usuário.

```
Binance API
│
▼
Pipeline de Coleta (GitHub Actions)
│
▼
Supabase (PostgreSQL)
│
├──────────────────────────────┐
▼                              ▼
FastAPI (REST API)           Machine Learning (Treinamento/Métricas)
│                              │
└──────────────┬───────────────┘
▼
React Dashboard (Vercel)
│
▼
Usuário
```

### Divisão de Responsabilidades (Monorepo)

| Componente | Tecnologia | Papel no Ecossistema | Hospedagem |
| :--- | :--- | :--- | :--- |
| **Pipeline de Coleta** | Python (`uv`) | Worker diário para ingestão, validação de candles inéditos e registro de logs. | GitHub Actions |
| **Banco de Dados** | Supabase | PostgreSQL persistente para séries históricas, indicadores, previsões e versionamento de modelos. | Supabase Cloud |
| **Back-end** | FastAPI | Disponibilização de endpoints REST, documentação Swagger, cálculo de indicadores técnicos em tempo real e entrega de previsões. | Render |
| **Machine Learning**| Scikit-Learn / Prophet | Scripts de treinamento (semanal/mensal) e geração de projeções diárias de preços. | GitHub Actions / Runner |
| **Front-end** | React | Dashboard interativo para comparação de ativos, gráficos temporais e acompanhamento de performance dos modelos. | Vercel |

---

## Tecnologias, Ferramentas & Padrões

* **Linguagem Base:** Python 3.12+
* **Gerenciador de Pacotes Python:** `uv` (Fast Python package installer & resolver)
* **Validação de Ambiente:** Pydantic Settings (Gerenciamento de tipos via `.env`)
* **Arquitetura do Código (Back-end):** Clean Architecture / 3-Tier (Split entre `Clients`, `Repositories`, `Services` e `Controllers`)
* **Design Patterns:** Retry Pattern (Resiliência de conexões com a API), e Injeção de Dependências.

---

## Funcionalidades da Plataforma

### Ingestão & Pipeline de Dados
* **Atualização Automática (Cron):** Ingestão diária via GitHub Actions capturando novos candles sem gerar duplicidade no banco.
* **Resiliência a Falhas:** Lógica avançada de *retry* com backoff exponencial contra limites de rate-limit da API da Binance.
* **Data Quality:** Validação de tipos e consistência estrutural antes da inserção no banco PostgreSQL.

### Inteligência Artificial & Computação
* **Predição de Séries Temporais:** Modelos estatísticos/ML atualizados periodicamente utilizando todo o histórico de dados limpos.
* **Versionamento:** Rastreabilidade completa de métricas de performance (MAE, RMSE) por versão de modelo gerado.

### Entrega de Dados (API Gateway)
* **Endpoints REST:** Rotas otimizadas para puxar histórico de preços, status do mercado e as previsões futuras.
* **Indicadores Técnicos:** Cálculo em tempo real de métricas como RSI (IFR), Médias Móveis (SMA/EMA) e Bandas de Bollinger.
* **Documentação Viva:** Swagger e OpenAPI gerados dinamicamente para consumo facilitado.

---

## Schema do Banco de Dados (Supabase / PostgreSQL)

```
┌─────────────────────────────────────────────────────────────────┐
│ symbols (tabela referencial)                                    │
│ ├─ PK symbol: text                                              │
│ └─ created_at: timestamptz                                      │
└──────┬──────────────────────────────────────────────────────────┘
       │ FK
       ├──────────────────────────────────────────────────────┐
       │                                                      │
       ▼                                                      ▼
┌─────────────────────────────────────┐    ┌──────────────────────────────────────┐
│ klines_15m / klines_1h / klines_1d  │    │ ticker_24hr_history                  │
│ (OHLCV bruto — top 20 ativos)       │    │ (24h summary — todos os ativos)      │
├─────────────────────────────────────┤    ├──────────────────────────────────────┤
│ PK id: bigint                       │    │ PK id: bigint                        │
│ symbol: text FK                     │    │ symbol: text FK                      │
│ open_time / close_time: timestamp   │    │ open_time / close_time: timestamp    │
│ open / high / low / close: numeric  │    │ price_change / price_change_percent  │
│ volume: numeric                     │    │ weighted_avg_price / prev_close_price│
│ quote_asset_volume: numeric         │    │ last_price / last_qty                │
│ number_of_trades: integer           │    │ bid_price -> ask_qty                 │
│ taker_buy_*: numeric                │    │ open_price -> low_price              │
└─────────────────────────────────────┘    │ volume / quote_volume                │
                                           │ first_id / last_id / count           │
┌─────────────────────────────────────┐    └──────────────────────────────────────┘
│ orderbook_tickers                   │    ┌─────────────────────────────────────┐
│ (bid/ask — top 20 ativos, 5min)     │    │ features_klines                     │
├─────────────────────────────────────┤    │ (indicadores calculados — top 20)   │
│ PK id: bigint                       │    ├─────────────────────────────────────┤
│ symbol: text FK                     │    │ PK (symbol, timestamp, interval)    │
│ bid_price / bid_qty: numeric        │    │ symbol: text FK                     │
│ ask_price / ask_qty: numeric        │    │ timestamp: timestamptz              │
│ fetched_at: timestamptz             │    │ interval: text (15m/1h/1d)          │
└─────────────────────────────────────┘    │ sma_20 / sma_50 / sma_200: numeric  │
                                           │ ema_12 / ema_26: numeric            │
                                           │ rsi_14: numeric                     │
                                           │ bb_upper/middle/lower: numeric      │
                                           │ atr_14: numeric                     │
                                           │ volume_sma_20: numeric              │
                                           └─────────────────────────────────────┘
```

> Coleta restrita ao **top 20 ativos por volume 24h** (exceto `ticker_24hr_history` que coleta todos para rankear). `features_klines` armazena indicadores calculados a partir dos dados brutos — é a tabela de entrada para os modelos de ML.

---

## Estrutura do Monorepo

```text
crypto-market-platform/
├── .github/
│   └── workflows/
│       └── daily_pipeline.yml       # Automação de coleta e predição diária
├── back-end/                        # API REST (FastAPI)
│   ├── app/
│   │   ├── clients/                 # Conexões externas (Binance, Supabase)
│   │   ├── controllers/             # Orquestração das rotas de entrada
│   │   ├── repositories/            # Camada de persistência/consultas SQL
│   │   ├── services/                # Regras de negócio e cálculos matemáticos
│   │   └── feature_engineering/     # Pipeline offline de features + retenção
│   │       ├── config/              # features.yaml
│   │       ├── pipelines/           # Orquestração por tabela (orderbook, klines, etc.)
│   │       ├── transforms/          # Indicadores técnicos (SMA, RSI, Bollinger, etc.)
│   │       ├── downsample/          # Resample 5min→1h, 1h→1d
│   │       └── retention/           # Limpeza programada por retenção
│   │                                # (usa repositories/ para ler/escrever)
│   ├── main.py                      # Inicialização do servidor FastAPI
│   ├── config.py                    # Classe de Settings Pydantic
│   └── pyproject.toml               # Dependências da API via 'uv'
├── front-end/                       # Dashboard Interativo (React)
├── pipeline_coleta/                 # Scripts isolados do Worker de Ingestão
└── ml_models/                       # Modelos preditivos, métricas e notebooks
```

## Instalação & Setup de Desenvolvimento
Pré-requisitos

* Python 3.12+ instalado.
* Gerenciador uv instalado (pip install uv).

## 1. Preparando o Back-end

```Bash
# Entrar na pasta do backend
cd back-end
```

* Instalar dependências e criar ambiente virtual automaticamente via uv

```Bash
uv sync
```

## 2. Variáveis de Ambiente

* Crie um arquivo .env na raiz do monorepo seguindo a estrutura abaixo:

```Bash
Snippet de código
SUPABASE_URL=[https://seu-projeto.supabase.co](https://seu-projeto.supabase.co)
SUPABASE_KEY=sua-chave-pública-supabase
BINANCE_API_KEY=sua-api-key-da-binance
BINANCE_API_SECRET=seu-secret-da-binance
USE_TESTNET=True
```

## 3. Rodando a API Localmente

```Bash
uv run uvicorn app.main:app --reload
Acesse a documentação interativa em: http://127.0.0.1:8000/docs
```

# Licença

Este projeto está sendo desenvolvido como um portfólio avançado de Engenharia e Ciência de Dados, demonstrando habilidades com automação de infraestrutura, modelagem estatística e arquitetura escalável de software.
