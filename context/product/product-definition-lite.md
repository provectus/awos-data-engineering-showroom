# Product Definition Summary: AI-Native Data Platform

**Version:** 1.0

---

## Vision

Create an AI-native data engineering environment where specialized subagents autonomously extend and enhance data pipelines using well-defined standards, patterns, and practices. Empower subagents to handle the complete data lifecycle—from ingestion to visualization—with minimal human intervention.

---

## Target Audience

Data engineers who want to automate their work by leveraging specialized subagents to rapidly build, extend, and maintain data pipelines.

---

## Core Features

- **Standardized Project Architecture:** Modular components (dlt_pipeline, dbt, data_quality, streamlit_app, airflow) with consistent patterns within each module

- **Module-Specific Documentation:** CLAUDE.md files at project root and for each major component containing module-specific coding practices and patterns

- **Specialized Subagent System:** Domain-expert subagents defined in `.awos/subagents/`:
  - **dlt-ingestion subagent** for data extraction and loading
  - **dbt-modeling subagent** for SQL transformations
  - **data-quality subagent** for validation and quality checks
  - **streamlit-viz subagent** for dashboard development
  - **airflow-orchestration subagent** for workflow orchestration
  - **data-analysis subagent** for exploratory analysis

- **AWOS Workflow System:** Slash commands (/awos:product, /awos:spec, /awos:roadmap, /awos:tasks, /awos:implement) for structured development with subagent delegation

- **Reference Implementation Patterns:** Complete examples (bike trips, weather) serving as templates for subagents to follow

- **Modular, Extensible Components:** dlt resources, dbt models, Great Expectations suites designed for easy replication by specialized subagents

- **Quality Gates at Every Layer:** Automated validation, transformation testing, code quality checks, and unit tests

---

## Success Metric

**The platform succeeds when specialized subagents can autonomously handle the complete end-to-end workflow:** the **dlt-ingestion subagent** adds new data sources, the **data-quality subagent** implements validations, the **dbt-modeling subagent** creates transformations, the **data-analysis subagent** performs exploratory analysis, the **streamlit-viz subagent** builds visualizations, and the **airflow-orchestration subagent** updates workflows—all following module-specific patterns with minimal human guidance.
