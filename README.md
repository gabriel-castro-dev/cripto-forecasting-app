# Explorador de Mercado Binance - EDA

Sistema de Análise Exploratória de Dados (EDA) do mercado de criptomoedas com arquitetura em camadas, extraindo informações da API Binance, transformando e estruturando dados em DataFrames para análise detalhada.

**Projeto desenvolvido para demonstrar:** Manipulação avançada de dados, arquitetura em camadas, integração com APIs REST e boas práticas em Python.

## Status

-  **Implementado**: Serviços, Controllers e lógica de requisições
-  **Em Desenvolvimento**: Exportação para XLSX e análise de dados com BI

---

##  Arquitetura

Projeto estruturado em **3 camadas** seguindo o padrão de separação de responsabilidades:

```
┌─────────────────────────────────────┐
│       main.py (Execução)            │
└────────────────┬────────────────────┘
                 │
┌────────────────▼─────────────────────────────────┐
│  Controllers (Orquestracao)                      │
│  • market_data_controller.py                     │
│  • account_history_controller.py                 │
│  • controllers_manager.py                        │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────┐
│  Services (Logica de Negocio)                   │
│  • binance_market_data_service.py               │
│  • binance_account_history_service.py           │
│  • services_manager.py                          │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  Environment & Configuracao                     │
│  • env/keys.py (Credenciais & API Keys)         │
└─────────────────────────────────────────────────┘
```

### Responsabilidades por Camada

| Camada | Responsabilidade | Arquivos |
|--------|-----------------|----------|
| **Services** | Requisicoes a API Binance, transformacao em DataFrames, tratamento de erros, retry logic, validacao de dados | `binance_*_service.py` |
| **Controllers** | Orquestracao de chamadas aos services, delegacao de responsabilidades | `*_controller.py` |
| **Managers** | Factory Pattern - Centraliza instanciacao de dependencias com injecao de dependencias | `*_manager.py` |
| **Environment** | Isolamento de credenciais e configuracoes sensiveis | `env/keys.py` |

---

##  Funcionalidades Implementadas

### Dados de Mercado (`MarketDataController`)
-  Ticker 24h de pares de criptomoedas
-  Volume de ordem (order book)
-  K-lines (velas) - Tempo real e histórico
-  Preço médio
-  Trades recentes e históricos
-  Agregação de trades
-  Profundidade de mercado (depth)

### Dados de Conta (`AccountHistoryController`)
-  Informações de saldo da conta
-  Status da conta
-  Status de trading da API
-  Histórico de trades executados
-  Histórico de dividendos
-  Ordens (todas, em aberto, etc)
-  Saldo de ativos específicos

---

## Instalação & Configuração

### Pré-requisitos
- Python 3.8+
- pip

### 1. Clonar o repositório
```bash
git clone https://github.com/gabriel-castro-dev/Explorador-de-Mercado-Binance-EDA
cd Explorador-de-Mercado-Binance-EDA
```

### 2. Criar ambiente virtual
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar credenciais
Copie o arquivo exemplo e adicione suas chaves:
```bash
cp env/examplekeys.py env/keys.py
```

Edite `env/keys.py`:
```python
BINANCE_API_KEY = "sua_chave_de_api_aqui"
BINANCE_API_SECRET = "seu_secret_aqui"
```

### 5. Executar
```bash
python main.py
```

---

## Exemplo de Uso

```python
from controllers.controllers_manager import ControllersManager
import pandas as pd

# Instanciar managers
controllers_manager = ControllersManager()
market_data, account_history = controllers_manager.export_controllers()

# Obter dados de mercado
symbol = 'BTCUSDT'
ticker_data = market_data.get_ticker_24hr(symbol)
print(ticker_data)

# Obter histórico da conta
account_balances = account_history.account_info()
print(account_balances)

# Obter K-lines histórico
klines = market_data.get_historical_klines(
    symbol='ETUSDT',
    interval='1h',
    start_str='30 days ago UTC'
)
print(klines)
```

---

## Estrutura de Arquivos

```
crypto-data/
├── main.py                               # Ponto de entrada
├── README.md                             # Este arquivo
├── requirements.txt                      # Dependências Python
│
├── services/                             # Camada de Serviços
│   ├── binance_market_data_service.py   # Requisições de dados de mercado
│   ├── binance_account_history_service.py # Requisições de conta
│   └── services_manager.py               # Factory de serviços
│
├── controllers/                          # Camada de Controladores
│   ├── market_data_controller.py        # Transformação de dados de mercado
│   ├── account_history_controller.py    # Transformação de dados de conta
│   └── controllers_manager.py            # Factory de controladores
│
└── env/                                  # Configuração
    ├── keys.py                           # Chaves 
    └── __init__.py
```

---

## Tecnologias & Dependências

| Tecnologia | Versão | Uso |
|------------|--------|-----|
| **Python** | 3.8+ | Linguagem base |
| **python-binance** | Latest | SDK oficial Binance |
| **pandas** | Latest | Estruturação e transformação de dados |

---

## Padrões de Design Utilizados

- **Factory Pattern**: `ServicesManager`, `ControllersManager`
- **Separation of Concerns**: Camadas bem definidas
- **Retry Pattern**: Resiliência com tentativas
- **Error Handling**: Tratamento específico de exceções

---

## Licença

Este projeto foi desenvolvido como portfólio pessoal para demonstrar habilidades em Python, arquitetura de software e manipulação de dados.

---
