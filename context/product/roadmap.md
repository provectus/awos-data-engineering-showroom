# Product Roadmap: AI-Native Data Platform

_This roadmap outlines our strategic direction based on the goal of creating an AI-native data engineering environment where specialized subagents can autonomously extend pipelines. It focuses on the "what" and "why," not the technical "how."_

---

### Phase 1: Foundation - Core Infrastructure & Reference Implementation

_The highest priority features that establish the foundational platform structure and patterns for subagents to learn from._

- [ ] **Standardized Project Architecture**
  - [ ] **Modular Component Structure:** Establish clear separation between dlt_pipeline, dbt, data_quality, streamlit_app, airflow, and notebooks modules with consistent patterns within each.
  - [ ] **Reference Data Sources:** Implement complete bike trips and weather data pipelines as working examples demonstrating all patterns subagents need to follow.

- [ ] **Root-Level Documentation**
  - [ ] **Project-Wide CLAUDE.md:** Create comprehensive documentation covering overall architecture, data flow, cross-cutting concerns, and common commands across all modules.
  - [ ] **Development Standards:** Document linting configuration (ruff), testing practices (pytest), and Git workflow conventions.

- [ ] **Quality & Testing Infrastructure**
  - [ ] **Code Quality Tools:** Set up ruff configuration with appropriate rules for data engineering code.
  - [ ] **Unit Testing Framework:** Establish pytest patterns with example tests for pipeline components.

---

### Phase 2: Module-Specific Documentation & Patterns

_Once the foundation is complete, create detailed, module-specific documentation that enables subagents to understand each component's unique conventions._

- [ ] **Data Ingestion Documentation**
  - [ ] **dlt_pipeline/CLAUDE.md:** Document dlt patterns, resource decorators, merge strategies, error handling, Polars parsing, and DuckDB destination configuration.
  - [ ] **API Integration Patterns:** Provide clear examples for both file-based (bike trips) and API-based (weather) data sources.

- [ ] **Data Transformation Documentation**
  - [ ] **dbt/CLAUDE.md:** Document dbt three-layer structure (staging/core/marts), materialization strategies, testing conventions, and documentation practices.
  - [ ] **SQL Modeling Patterns:** Establish naming conventions, ref/source patterns, and schema design principles.

- [ ] **Data Quality Documentation**
  - [ ] **data_quality/CLAUDE.md:** Document Great Expectations patterns, suite structure, checkpoint configuration, and validation execution.
  - [ ] **Quality Check Patterns:** Provide examples of different expectation types (nullability, ranges, uniqueness, business rules).

- [ ] **Visualization & Analysis Documentation**
  - [ ] **streamlit_app/CLAUDE.md:** Document Streamlit UI/UX patterns, page structure, visualization standards, and dashboard design conventions.
  - [ ] **notebooks/CLAUDE.md:** Document exploratory analysis patterns, notebook structure, Polars usage, and visualization standards.

- [ ] **Orchestration Documentation**
  - [ ] **airflow/CLAUDE.md:** Document DAG patterns, task structure, dependency management, error handling, and retry strategies.

---

### Phase 3: Specialized Subagent System

_With complete documentation in place, define specialized subagents that can autonomously work within each module following established patterns._

- [ ] **Data Pipeline Subagents**
  - [ ] **dlt-ingestion Subagent:** Create subagent specialized in data extraction, dlt resource patterns, API integration, and DuckDB loading.
  - [ ] **dbt-modeling Subagent:** Create subagent specialized in SQL transformations, dbt model creation, testing, and documentation.
  - [ ] **data-quality Subagent:** Create subagent specialized in Great Expectations suites, validation rules, and data profiling.

- [ ] **Serving & Analysis Subagents**
  - [ ] **streamlit-viz Subagent:** Create subagent specialized in Streamlit dashboard development, Plotly visualizations, and UI/UX patterns.
  - [ ] **data-analysis Subagent:** Create subagent specialized in Jupyter notebooks, exploratory analysis, statistical methods, and Polars.

- [ ] **Infrastructure Subagent**
  - [ ] **airflow-orchestration Subagent:** Create subagent specialized in Airflow DAG updates, task dependency management, and workflow optimization.

- [ ] **Orchestration & Delegation**
  - [ ] **Subagent Instructions:** Document when and how the orchestrator should delegate to each specialized subagent.
  - [ ] **Context Passing:** Define how information flows between orchestrator and subagents (module-specific CLAUDE.md reading, reference implementation analysis).

---

### Phase 4: AWOS Workflow Integration & Automation

_Features planned to enable full end-to-end automation from product planning through implementation using the AWOS command system._

- [ ] **Product Planning Workflows**
  - [ ] **Product Definition Command:** Implement /awos:product for creating structured product definitions.
  - [ ] **Roadmap Planning Command:** Implement /awos:roadmap for feature prioritization and phasing.
  - [ ] **Architecture Definition Command:** Implement /awos:architecture for system design documentation.

- [ ] **Implementation Workflows**
  - [ ] **Functional Spec Command:** Implement /awos:spec for detailed feature specifications that guide subagents.
  - [ ] **Task Breakdown Command:** Implement /awos:tasks for converting specs into module-specific implementation tasks.
  - [ ] **Automated Implementation Command:** Implement /awos:implement for orchestrator-driven development with automatic subagent delegation.

- [ ] **Quality Assurance Integration**
  - [ ] **End-to-End Testing:** Validate that subagents can add a complete new data source (ingestion → validation → transformation → visualization → orchestration) autonomously.
  - [ ] **Code Quality Validation:** Ensure all subagent-generated code passes ruff checks and pytest without manual intervention.
  - [ ] **Documentation Updates:** Verify subagents update their respective CLAUDE.md files after making changes.

---

### Future Enhancements (Backlog)

_Features for future consideration, dependent on validation of the core platform's effectiveness._

- [ ] **Advanced Subagent Capabilities**
  - [ ] **Self-Learning Patterns:** Enable subagents to learn from successful implementations and update their own documentation.
  - [ ] **Cross-Module Optimization:** Allow subagents to suggest architectural improvements spanning multiple modules.

- [ ] **Extended Reference Implementations**
  - [ ] **Third Data Source Example:** Add another complete data source (e.g., traffic, events) to provide more pattern variety.
  - [ ] **Advanced dbt Patterns:** Demonstrate incremental models, snapshots, and macros.
  - [ ] **ML Integration Example:** Show how to integrate simple ML models into the pipeline.

- [ ] **Developer Experience**
  - [ ] **Interactive Setup Wizard:** Create guided setup process for new users.
  - [ ] **Subagent Performance Metrics:** Track how effectively subagents complete tasks (time, code quality, pattern adherence).
  - [ ] **VS Code Extensions:** Consider tooling integration for improved developer workflow.
