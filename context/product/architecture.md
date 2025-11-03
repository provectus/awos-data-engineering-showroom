# System Architecture Overview: AI-Native Data Platform

---

## 1. Data Pipeline & Processing Stack

- **Data Ingestion Framework:** dlt (Data Load Tool) - for idempotent, incremental loading from APIs and files to DuckDB with merge strategies and primary key deduplication
- **Data Transformation Framework:** dbt (Data Build Tool) - for SQL-based transformations with testing, documentation, and lineage tracking
- **Data Quality Framework:** Great Expectations - for validation suites, data profiling, and statistical checks
- **Data Analysis Library:** Polars - for fast DataFrame operations in notebooks with lazy evaluation and expression API

---

## 2. Data Storage & Persistence

- **Analytics Data Warehouse:** DuckDB - embedded analytical database with vectorized execution, ACID transactions, and SQL analytics
- **Multi-Database Pattern:** Attached DuckDB Files - separate databases for raw ingestion (`bike_ingestion.duckdb`, `weather_ingestion.duckdb`) managed by dlt, and transformed data (`warehouse.duckdb`) managed by dbt
- **File-Based Caching:** Local filesystem (`.cache/`) - for downloaded data files before ingestion, supporting idempotent re-runs

---

## 3. Orchestration & Workflow Management

- **Workflow Orchestrator:** Apache Airflow - for scheduling and managing DAG-based workflows with task dependencies, retry logic, and monitoring
- **Task Execution Pattern:** Python TaskFlow API (`@task` decorators) combined with BashOperator for dbt commands - hybrid approach for flexibility
- **Execution Environment:** uv-managed virtual environment - for fast, reliable dependency management during task execution
- **Executor:** SequentialExecutor - for local development and demonstration (single-threaded execution)

---

## 4. Visualization & User Interface

- **Dashboard Framework:** Streamlit - for rapid development of interactive data applications with Python, supporting multi-page apps
- **Visualization Library:** Plotly - for interactive charts and graphs (line charts, pie charts, bar charts) with hover details and zooming
- **Analysis Interface:** Jupyter Notebooks (JupyterLab) - for exploratory data analysis, statistical testing, and documentation with rich output support
- **Data Connection:** DuckDB Python client - for direct SQL queries from Streamlit and notebooks with read-only access to warehouse

---

## 5. AI Agent & Subagent System

- **Orchestrator Agent:** Claude Code (Sonnet 4.5) - main agent that reads product definitions, delegates to subagents, and coordinates overall workflow
- **Subagent Architecture:** Markdown-based subagent definitions (`.awos/subagents/`) - version-controlled files defining role, expertise, and patterns for specialized subagents:
  - `dlt-ingestion.md` - data extraction and loading specialist
  - `dbt-modeling.md` - SQL transformation specialist
  - `data-quality.md` - validation and quality checks specialist
  - `streamlit-viz.md` - dashboard development specialist
  - `airflow-orchestration.md` - workflow orchestration specialist
  - `data-analysis.md` - exploratory analysis specialist
- **Context System:** Module-specific CLAUDE.md files - documentation at root and component levels (dlt_pipeline/, dbt/, data_quality/, streamlit_app/, airflow/, notebooks/) containing coding practices, patterns, and conventions
- **Workflow Commands:** AWOS slash commands - structured commands for development lifecycle:
  - `/awos:product` - product definition
  - `/awos:spec` - functional specifications
  - `/awos:roadmap` - feature prioritization
  - `/awos:architecture` - system design
  - `/awos:tasks` - task breakdown
  - `/awos:implement` - automated implementation with subagent delegation

---

## 6. Development Tools & Code Quality

- **Package Manager:** uv - for fast Python dependency management (10-100x faster than pip), virtual environment handling, and lockfile generation
- **Code Linting & Formatting:** Ruff - for fast Python linting and formatting (replaces flake8, black, isort) configured for line length 100, Python 3.11+ target
- **Testing Framework:** pytest - for unit and integration testing with mocking capabilities (pytest-mock) and coverage reporting
- **Task Automation:** Make (Makefile) - standardized commands for each module (e.g., `make test`, `make lint`, `make build`) that subagents can easily discover and execute
- **Type Checking:** Optional mypy integration - for static type analysis (currently minimal, can be enhanced for production-quality code)
- **Version Control:** Git - with conventional commit messages and clear workflow patterns documented for subagents

---

## 7. External Data Sources & APIs

- **Bike Trip Data Source:** NYC Citi Bike Open Data (Amazon S3) - monthly CSV files (gzipped) accessed via HTTPS, demonstrating file-based batch ingestion patterns
- **Weather Data Source:** Open-Meteo Historical Weather API - JSON REST API for historical weather data with query parameters, demonstrating API-based ingestion patterns
- **HTTP Client Library:** requests - for API calls and file downloads with timeout configuration and streaming support for large files
- **Data Format Handling:**
  - CSV parsing via Polars (fast, memory-efficient)
  - JSON parsing via Python standard library
  - ZIP archive extraction via Python zipfile module

---

## Architecture Principles

1. **Local-First Development:** All components run locally without requiring cloud infrastructure, making it easy to set up and demonstrate
2. **Embedded Analytics:** DuckDB provides powerful analytics capabilities without external database servers
3. **Separation of Concerns:** Clear boundaries between ingestion (dlt), validation (Great Expectations), transformation (dbt), and serving (Streamlit)
4. **Idempotent Operations:** All pipeline components support re-running without duplicating data or breaking existing results
5. **Version-Controlled Configuration:** All configuration, patterns, and subagent definitions stored as code in Git
6. **Module-Specific Documentation:** Each component has its own CLAUDE.md with relevant patterns, enabling focused subagent specialization
7. **AI-Native Design:** Architecture optimized for subagent comprehension and extension, not just human developers
