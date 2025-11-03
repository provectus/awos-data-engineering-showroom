# Product Definition: AI-Native Data Platform

- **Version:** 1.0
- **Status:** Proposed

---

## 1. The Big Picture (The "Why")

### 1.1. Project Vision & Purpose

To create an AI-native data engineering environment where specialized subagents autonomously extend and enhance data pipelines using well-defined standards, patterns, and practices. This platform demonstrates how proper structure, module-specific documentation, and specialized subagents enable the complete data lifecycle—from ingestion to visualization—with minimal human intervention.

### 1.2. Target Audience

Data engineers who want to automate their work by leveraging AI coding assistants and specialized subagents to rapidly build, extend, and maintain data pipelines without writing everything from scratch.

### 1.3. User Personas

- **Persona 1: "Alex the Automation Engineer"**
  - **Role:** Data Engineer at a mid-sized company managing multiple data sources and dashboards.
  - **Goal:** Wants to delegate data engineering tasks to specialized subagents that understand module-specific patterns and can autonomously implement features from ingestion to visualization.
  - **Frustration:** Most data projects lack clear patterns, comprehensive documentation, and specialized tooling, making it impossible for AI tools to understand module-specific conventions (dlt patterns vs dbt patterns vs Streamlit patterns). Generic AI-generated code doesn't follow the project's established practices for each component.

### 1.4. Success Metrics

**The platform succeeds when specialized subagents can autonomously handle the complete end-to-end data engineering workflow:**

- **New Data Source Integration:** The **dlt-ingestion subagent** can add new data sources (from API specification to DuckDB tables) following established dlt patterns with minimal human guidance.
- **Exploratory Data Analysis:** The **data-analysis subagent** can generate meaningful EDA notebooks that follow project conventions and integrate with existing analysis workflows.
- **Data Modeling:** The **dbt-modeling subagent** can create dbt models (staging, core, marts) that align with the existing schema structure, naming conventions, and materialization strategies.
- **Quality Validation:** The **data-quality subagent** can implement Great Expectations suites for new data sources that match the rigor and patterns of existing validations.
- **Data Serving:** The **streamlit-viz subagent** can build or extend Streamlit dashboards and visualizations that integrate seamlessly with the existing UI/UX patterns.
- **Workflow Orchestration:** The **airflow-orchestration subagent** can update DAGs to include new tasks with correct dependencies and error handling.
- **Code Quality:** All subagent-generated code consistently passes linting, formatting, and testing standards without requiring manual fixes.
- **Documentation Maintenance:** Subagents can update relevant module-specific CLAUDE.md files when making changes to their respective components.

---

## 2. The Product Experience (The "What")

### 2.1. Core Features

- **Standardized Project Architecture:** Clear separation of concerns with modular components (dlt_pipeline, dbt, data_quality, streamlit_app, airflow) that follow consistent patterns within each module.

- **Comprehensive Module-Specific Documentation:**
  - Root CLAUDE.md with overall architecture and cross-cutting concerns
  - Component-specific CLAUDE.md files (dlt_pipeline/CLAUDE.md, dbt/CLAUDE.md, data_quality/CLAUDE.md, streamlit_app/CLAUDE.md, airflow/CLAUDE.md, notebooks/CLAUDE.md) containing module-specific coding practices, patterns, and conventions

- **Specialized Subagent System:**
  - Subagents defined in `.awos/subagents/` directory, each specialized for specific modules/tasks
  - **dlt-ingestion subagent:** Expert in dlt patterns, API extraction, data loading, and DuckDB integration
  - **dbt-modeling subagent:** Expert in dbt patterns, SQL transformations, testing, and documentation
  - **data-quality subagent:** Expert in Great Expectations patterns, validation suites, and data profiling
  - **streamlit-viz subagent:** Expert in Streamlit patterns, Plotly visualizations, and dashboard design
  - **airflow-orchestration subagent:** Expert in Airflow patterns, DAG design, and task dependencies
  - **data-analysis subagent:** Expert in Jupyter notebooks, Polars/Pandas analysis, and statistical methods

- **AWOS Workflow System:** Slash commands (/awos:product, /awos:spec, /awos:roadmap, /awos:tasks, /awos:implement) that guide the orchestrator agent through structured product development workflows, delegating implementation to specialized subagents.

- **Reference Implementation Patterns:** Complete examples of data ingestion (bike, weather), validation, transformation, and visualization that serve as templates for subagents to follow.

- **Modular, Extensible Pipeline Components:** dlt resources, dbt models, Great Expectations suites, and Streamlit pages designed to be easily extended or replicated by specialized subagents.

- **Quality Gates at Every Layer:** Automated validation (Great Expectations), transformation testing (dbt tests), code quality checks (ruff), and unit tests (pytest) that subagents can replicate.

- **End-to-End Orchestration:** Airflow DAGs demonstrating how all components integrate, providing subagents with a blueprint for adding new workflows.

### 2.2. User Journey

**Typical Workflow: Adding a New Data Source with Specialized Subagents**

1. **Initialization:** Alex opens the project in Claude Code and requests: "Add traffic congestion data from NYC DOT API to analyze its correlation with bike demand."

2. **Planning Phase:** The orchestrator agent reads the root CLAUDE.md, uses `/awos:spec` to create a functional specification for the new feature, then `/awos:tasks` to break it into module-specific implementation steps.

3. **Data Ingestion:** The orchestrator delegates to the **dlt-ingestion subagent**, which:
   - Reads `dlt_pipeline/CLAUDE.md` for module-specific patterns
   - Examines bike.py and weather.py reference implementations
   - Creates `dlt_pipeline/traffic.py` following dlt conventions (resource decorators, merge strategy, error handling, Polars parsing, DuckDB destinations)

4. **Data Quality Validation:** The orchestrator delegates to the **data-quality subagent**, which:
   - Reads `data_quality/CLAUDE.md` for validation patterns
   - Reviews existing expectation suites (bike_trips_suite, weather_suite)
   - Creates `validate_traffic_data.py` with appropriate Great Expectations checks following the established structure

5. **Data Modeling:** The orchestrator delegates to the **dbt-modeling subagent**, which:
   - Reads `dbt/CLAUDE.md` for dbt-specific conventions
   - Examines the three-layer structure (staging/core/marts)
   - Creates `models/staging/stg_traffic.sql` to clean raw data
   - Updates core models to join traffic with trips
   - Creates `models/marts/mart_traffic_impact.sql` for analytics
   - Adds appropriate schema.yml tests following dbt patterns

6. **Exploratory Analysis:** The orchestrator delegates to the **data-analysis subagent**, which:
   - Reads `notebooks/CLAUDE.md` for analysis patterns
   - Reviews existing EDA notebooks (polars_eda.ipynb)
   - Creates `traffic_analysis.ipynb` with visualizations and statistical tests following notebook conventions

7. **Visualization:** The orchestrator delegates to the **streamlit-viz subagent**, which:
   - Reads `streamlit_app/CLAUDE.md` for UI/UX patterns
   - Examines existing pages (Home.py, Weather.py)
   - Creates `pages/Traffic_Impact.py` with interactive visualizations following the established dashboard structure and styling

8. **Orchestration Update:** The orchestrator delegates to the **airflow-orchestration subagent**, which:
   - Reads `airflow/CLAUDE.md` for DAG patterns
   - Reviews `bike_weather_dag.py` structure
   - Adds traffic ingestion and validation tasks with correct dependencies and error handling

9. **Testing & Documentation:** Each subagent:
   - Generates module-specific unit tests following patterns in `tests/`
   - Runs quality checks appropriate to their module
   - Updates their respective CLAUDE.md files with new patterns or learnings

10. **Review & Deploy:** Alex reviews the subagent-generated code across all modules, makes minor adjustments if needed, and runs the complete pipeline end-to-end.

**Result:** A new data source fully integrated across all platform layers—ingestion, quality, modeling, analysis, visualization, and orchestration—with each component following its module-specific conventions and patterns, completed in a fraction of the time manual coding would require.

---

## 3. Project Boundaries

### 3.1. What's In-Scope for this Version

**Core Infrastructure:**
- Complete reference implementation with 2-3 example data sources (bike trips, weather, optionally one more)
- Root-level CLAUDE.md with overall architecture, cross-cutting concerns, and common commands
- Module-specific CLAUDE.md files for each major component:
  - `dlt_pipeline/CLAUDE.md`: dlt patterns, resource conventions, API extraction, error handling
  - `dbt/CLAUDE.md`: dbt patterns, model structure, testing conventions, documentation practices
  - `data_quality/CLAUDE.md`: Great Expectations patterns, suite structure, validation practices
  - `streamlit_app/CLAUDE.md`: Streamlit patterns, UI/UX conventions, visualization standards
  - `airflow/CLAUDE.md`: DAG patterns, task structure, dependency management, error handling
  - `notebooks/CLAUDE.md`: Analysis patterns, notebook structure, visualization standards

**Specialized Subagent System:**
- Subagent definitions in `.awos/subagents/` directory:
  - `dlt-ingestion.md`: Specialized in data extraction and loading patterns
  - `dbt-modeling.md`: Specialized in SQL transformations and dbt conventions
  - `data-quality.md`: Specialized in validation and quality checks
  - `streamlit-viz.md`: Specialized in dashboard and visualization development
  - `airflow-orchestration.md`: Specialized in workflow orchestration
  - `data-analysis.md`: Specialized in exploratory analysis and notebooks
- Clear instructions for when the orchestrator should delegate to each subagent

**AWOS Workflow Integration:**
- Full AWOS command suite (/awos:product, /awos:spec, /awos:roadmap, /awos:architecture, /awos:tasks, /awos:implement)
- Templates for product definition, functional specs, technical specs, and task lists
- Orchestrator agent that delegates implementation tasks to specialized subagents

**Quality & Standards:**
- Comprehensive linting and formatting configuration (ruff)
- Great Expectations validation framework with example suites
- dbt testing patterns (schema tests, data tests)
- pytest unit testing examples
- Git workflow and commit conventions

**Documentation:**
- README with setup instructions and demo walkthrough
- Inline code documentation and docstrings
- dbt model documentation and lineage
- Great Expectations data docs
- Subagent documentation explaining their roles and capabilities

**End-to-End Example:**
- Complete data pipeline from ingestion to visualization
- Airflow orchestration demonstrating task dependencies
- Multiple visualization pages showing different analytical approaches

### 3.2. What's Out-of-Scope (Non-Goals)

**Production Deployment:**
- Cloud infrastructure setup (AWS, GCP, Azure)
- Container orchestration (Kubernetes, ECS)
- Production-grade security and authentication
- Multi-environment configuration (dev/staging/prod)
- CI/CD pipeline automation

**Advanced Features:**
- Real-time streaming data ingestion (Kafka, Kinesis)
- Machine learning model training and deployment
- Advanced time-series forecasting
- Complex event processing
- Data lineage tracking tools (separate from dbt docs)

**Enterprise Features:**
- Multi-tenant architecture
- Role-based access control (RBAC)
- Data governance and cataloging (Collibra, Alation)
- Cost optimization and resource management
- Advanced monitoring and alerting (beyond Airflow)

**Scalability:**
- Distributed computing (Spark, Ray)
- Large-scale data processing (petabyte scale)
- High-availability configurations
- Performance optimization for production workloads

**Alternative Interfaces:**
- Mobile applications
- REST API for programmatic access
- Command-line interface tools
- Third-party integrations (Slack, email notifications)

**Note:** This is a demonstration and reference platform optimized for subagent-assisted development, not a production-ready data infrastructure. The focus is on clarity, module-specific patterns, specialized subagents, and extensibility, not on operational robustness or scale.
