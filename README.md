# YZTA-BOOTCAMP-26-GRUP30

# Information About Team and Product

## Team Members

| Photo | Name | Title | Socials Media |
|---|---|---|---|
|  | Elif Keskin | Scrum Master | [![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/elif-keskin-data-professional/) [![GitHub](https://img.shields.io/badge/-GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/elifkeskin) |
|  | Recep Atabey Demir | Product Owner | [![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/recep-atabey-demir/) [![GitHub](https://img.shields.io/badge/-GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/Atabeydem) |
|  | Rida Doğrul | Developer | [![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/rida-doğrul/) [![GitHub](https://img.shields.io/badge/-GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/RidaDogrul) |
|  | Nimet Asude Yalçın | Developer | [![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/nimet-asude-yalçın) [![GitHub](https://img.shields.io/badge/-GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/asudeyal) |
|  | Sevde Koç | Developer | [![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/sevde-ko%C3%A7-5b335b26b/) [![GitHub](https://img.shields.io/badge/-GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/svdsevde-cpu) |




# Autonomous Data Cleanroom and Forecasting Agent

An autonomous AI agent that connects to companies' scattered databases (SQL, NoSQL, Cloud), cleans raw data, fills in missing values, and — when the user asks a question in natural language without writing any technical code — runs machine learning models in the background to produce predictive reports and action plans.

---

## Project Structure

```
ai-data-agent/
│
├── src/
│   ├── api/                        # API Layer (FastAPI)
│   │   ├── v1/
│   │   │   ├── endpoints/          # chat, connect_db, reports routes
│   │   │   └── api.py
│   │   └── middleware/             # Security and Authentication
│   │
│   ├── connectors/                 # Database Connections
│   │   ├── postgres.py             # SQL connection and schema reading logic
│   │   ├── mysql.py
│   │   └── s3_storage.py          # File/Cloud storage connections
│   │
│   ├── security/                   # Cleanroom and Masking
│   │   └── anonymizer.py           # PII (Personal data) filtering algorithms
│   │
│   ├── agents/                     # AI Agents (CrewAI / LangChain)
│   │   ├── orchestrator.py         # The brain managing workflow between agents
│   │   ├── prompts.py              # System prompts and text-to-sql templates
│   │   └── tools/                  # Python functions usable by the agents
│   │
│   ├── ml_models/                  # Forecasting Engine (AutoML)
│   │   ├── forecaster.py           # Time series (Prophet/LightGBM) forecasting logic
│   │   └── preprocessor.py         # Missing data imputation and outlier cleaning
│   │
│   └── utils/                      # Helper Functions (Logger, Formatters)
│       ├── config.py               # Centralized .env-based settings management
│       └── logger.py               # JSON logging and request-id tracking
│
├── tests/                          # Unit and Integration Tests
├── requirements.txt                # Dependencies (fastapi, pandas, crewai, scikit-learn)
└── main.py                         # Main file that boots the application
```

---

## Data & Logic Flow

The end-to-end pipeline showing how a user's natural language question is processed in the background:

```
[USER] ──(1. Natural Language Question)──> [FRONTEND / CHAT UI]
                                                │
                                                ▼
                                    [BACKEND: API GATEWAY]
                                                │
                             (2. Schema Integration & Security Filter)
                                                │
                                                ▼
                           [AI AGENT ORCHESTRATOR] (CrewAI / LangChain)
                                                │
                  ┌─────────────────────────────┴─────────────────────────────┐
                  ▼                                                           ▼
       [AGENT 1: SQL/DATA EXECUTOR]                             [AGENT 2: DATA SCIENTIST]
        - Generates SQL based on schema                          - Cleans data with Pandas
        - Pulls raw data from the DB                              - Fills in missing values
        - Sends data to the Sandbox                               - Triggers the ML forecasting model
                  │                                                           │
                  └─────────────────────────────┬─────────────────────────────┘
                                                │
                                   (3. Cleaned & Forecasted Data)
                                                │
                                                ▼
                                    [AGENT 3: INSIGHT GENERATOR]
                                     - Structures results as JSON/Text
                                     - Prepares chart data (D3.js)
                                     - Produces an action plan
                                                │
                                                ▼
[USER] <──(4. Report, Charts & Action Plan)── [FRONTEND]
```

---

## Development Phases

### Phase 1 — Infrastructure and Data Connections

| Task | Description |
|-------|----------|
| **1.1 Data Source Connectors** | Secure connection interfaces for PostgreSQL, MySQL, MongoDB, and AWS S3/Snowflake |
| **1.2 Data Discovery & Schema Extraction** | An engine that automatically detects table schemas and converts them into an LLM-friendly JSON metadata format |
| **1.3 Data Security & Masking** | A filtering layer that anonymizes PII data (name, email, phone) under KVKK/GDPR locally before sending it to the agent |

### Phase 2 — Autonomous AI Agent Intelligence

| Task | Description |
|-------|----------|
| **2.1 Autonomous Data Cleaning** | A pipeline that fills null values via mean/median/interpolation and detects and flags outliers |
| **2.2 Text-to-SQL / Text-to-Python** | A LangChain/LlamaIndex prompt chain that converts the user's question into a correct SQL query based on the database schema |
| **2.3 AutoML Integration** | A Python module that runs time series forecasts with Prophet, ARIMA, or LightGBM and selects the most accurate model |

### Phase 3 — Reporting and Interface

| Task | Description |
|-------|----------|
| **3.1 Natural Language Reporting** | An LLM summarization layer that translates forecast results into a clear Turkish/English report, plus Chart.js/D3.js visualizations |
| **3.2 Action Plan Generator** | A reasoning step that not only identifies problems but also produces solution recommendations |
| **3.3 No-Code Dashboard** | A settings screen for connecting data sources, a chat interface for talking to the agent, and a home page listing reports |

### Phase 4 — Business Development and Market Entry

| Task | Description |
|-------|----------|
| **4.1 Closed Beta** | Anonymized real-data testing with 2-3 design partners from the e-commerce/retail sector |
| **4.2 Pricing** | A tiered SaaS model based on data size and usage hours (Freemium / Growth / Enterprise) |

---

## Sample API Output

```json
{
  "status": "success",
  "summary": "A 12% revenue loss risk has been detected in the Textile category for next month.",
  "chart_data": [
    {"date": "2026-07-01", "predicted_sales": 12000}
  ],
  "action_plan": [
    "Plan an urgent discount campaign in the Textile category.",
    "Reduce supply orders by 10%."
  ]
}
```

---

## Sprint Plan — Role and Task Distribution (6 Weeks)

| Role | Responsible Tasks | Weekly Output |
|-----|------------------------|----------------|
| **Data Engineer** | DB connectors, KVKK masking, data cleaning pipeline | Secure data connection and clean DataFrame generation |
| **AI / NLP Engineer** | Text-to-SQL, Agentic Workflow (LangChain/CrewAI), time series forecasting models | The AI brain that understands the question and produces the correct forecast in the background |
| **Full-Stack Developer** | Chat interface, chart integrations, user management panel, AWS/Cloud architecture | The web application where the user can log in and talk to the agent |

---

## Technology Stack

| Layer | Technologies |
|--------|-------------|
| **Backend** | Python, FastAPI |
| **AI Orchestration** | LangChain, CrewAI |
| **ML / Forecasting** | Prophet, ARIMA, LightGBM, scikit-learn |
| **Data Processing** | Pandas |
| **Databases** | PostgreSQL, MySQL, MongoDB |
| **Cloud / Storage** | AWS S3, Snowflake, AWS Secrets Manager |
| **Security** | Microsoft Presidio (PII masking), KVKK/GDPR compliance |
| **Frontend** | Chart.js / D3.js |
| **Testing** | Unit and integration tests |

---

## Retro & Review Meeting Summaries

Summaries of the Retrospective and Review meetings held at the end of each sprint can be found in the folder below:

📁 [`Retro & Review Toplantıları -Özet/`](./Retro%20%26%20Review%20Toplant%C4%B1lar%C4%B1%20-%C3%96zet)

| Sprint | Retro | Review |
|--------|-------|--------|
| **Sprint I** | [Retro Summary](./Retro%20%26%20Review%20Toplant%C4%B1lar%C4%B1%20-%C3%96zet/Sprint%20I/Retro%20Toplant%C4%B1s%C4%B1%20-%20%C3%96zet.md) | [Review Summary](./Retro%20%26%20Review%20Toplant%C4%B1lar%C4%B1%20-%C3%96zet/Sprint%20I/Review%20Toplant%C4%B1s%C4%B1-%C3%96zet.md) |
| **Sprint II** | *(Coming soon)* | *(Coming soon)* |
| **Sprint III** | *(Coming soon)* | *(Coming soon)* |

---

## Jira

Sprint planning and task tracking are carried out via Jira. Board screenshots and task breakdowns for each sprint can be found in the folder below:

📁 [`Jira/`](./Jira)

| Sprint | Folder | Content |
|--------|--------|--------|
| **Sprint I** | [`Jira/Sprint-I/`](./Jira/Sprint-I) | [Board Screenshot 1](./Jira/Sprint-I/Sprint%20I%20-%20Jira.png) · [Board Screenshot 2](./Jira/Sprint-I/Sprint-I-jira-2.png) · [Task List (xlsx)](./Jira/Sprint-I/jira-sprint1%20.xlsx) |
| **Sprint II** | [`Jira/Sprint-II/`](./Jira/Sprint-II) | *(Coming soon)* |
| **Sprint III** | [`Jira/Sprint-III/`](./Jira/Sprint-III) | *(Coming soon)* |

---

## Daily Scrum

Screenshots of the stand-up meetings (2-3 times a week) held throughout each sprint can be found in the folder below:

📁 [`Daily Scrum/`](./Daily%20Scrum)

| Sprint | Folder | Images |
|--------|--------|-----------|
| **Sprint I** | [`Daily Scrum/Sprint-I/`](./Daily%20Scrum/Sprint-I) | [1](./Daily%20Scrum/Sprint-I/1000022584.jpg) · [2](./Daily%20Scrum/Sprint-I/1000022585.jpg) · [3](./Daily%20Scrum/Sprint-I/1000022586.jpg) · [4](./Daily%20Scrum/Sprint-I/1000022587.jpg) · [5](./Daily%20Scrum/Sprint-I/20260705-16590.jpg) |
| **Sprint II** | [`Daily Scrum/Sprint-II/`](./Daily%20Scrum/Sprint-II) | *(Coming soon)* |
| **Sprint III** | [`Daily Scrum/Sprint-III/`](./Daily%20Scrum/Sprint-III) | *(Coming soon)* |

---

## Product Status Check Folder

In the product status check folder, you can find the current status of the product and screenshots of the tests performed throughout each sprint related to this product status:

📁 [`Ürün_Durumu_Kontrol/`](./Ürün_Durumu_Kontrol)

| Sprint | Folder | Content |
|--------|--------|--------|
| **Sprint I** | [`Ürün_Durumu_Kontrol/Sprint-I/`](./Ürün_Durumu_Kontrol/Sprint-I) | Screenshots of FastAPI setup, LangChain integration, MySQL/MongoDB/PostgreSQL connector tests, AWS S3 test, schema extractor, PII masking, logger tests, local CI checks, and config management/health check tests |
| **Sprint II** | [`Ürün_Durumu_Kontrol/Sprint-II/`](./Ürün_Durumu_Kontrol/Sprint-II) | *(Coming soon)* |
| **Sprint III** | [`Ürün_Durumu_Kontrol/Sprint-III/`](./Ürün_Durumu_Kontrol/Sprint-III) | *(Coming soon)* |


**NOTE**: Changes made will be updated at the end of each sprint.

---

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
