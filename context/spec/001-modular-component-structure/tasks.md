# Task List: Modular Component Structure

## Overview
This task list breaks down the Modular Component Structure feature into **vertical slices**. Each slice is independently runnable and leaves the project in a working state with incrementally improved structure.

---

## Slice 1: Foundation - Python Package Structure + Root Documentation

**Goal:** Establish the basic Python package structure and enhance root documentation so subagents understand cross-cutting standards.

- [ ] **Add Python package structure for Airflow imports**
  - [ ] Create `data_quality/__init__.py` with docstring
  - [ ] Verify `dlt_pipeline/__init__.py` exists
  - [ ] Test imports in Python REPL to ensure no ImportError

- [ ] **Enhance root CLAUDE.md with cross-cutting standards**
  - [ ] Use Context7 MCP to research Python logging best practices for data pipelines
  - [ ] Use Context7 MCP to research error handling patterns for ETL workflows
  - [ ] Add "Cross-Cutting Standards" section with logging format, error handling, code style
  - [ ] Add "Module Execution Order" section with dependency chain diagram
  - [ ] Add "Module Communication Pattern" section with DuckDB file paths table
  - [ ] Add "DuckDB Locking Constraints" section
  - [ ] Add placeholder "Module-Specific CLAUDE.md Files" section (will be populated in later slices)

- [ ] **Validation**
  - [ ] Verify existing pipeline still works (run `uv run python dlt_pipeline/bike.py`)
  - [ ] Run `uv run ruff check .` to ensure no new linting errors

---

## Slice 2: Data Ingestion Module (dlt_pipeline) - Documentation + Tooling

**Goal:** Make dlt_pipeline independently discoverable and runnable with documented patterns.

- [ ] **Create `dlt_pipeline/CLAUDE.md`**
  - [ ] Use Context7 MCP to research dlt (Data Load Tool) best practices and patterns
  - [ ] Use Context7 MCP to research Polars DataFrame best practices for CSV processing
  - [ ] Add "Module Purpose" section (data ingestion from APIs/files to DuckDB)
  - [ ] Add "Prerequisites/Dependencies" section (none - entry point)
  - [ ] Add "Common Commands" section (reference Makefile targets)
  - [ ] Add "Coding Patterns" section (dlt decorators, merge strategy, Polars, caching, error handling)
  - [ ] Add "Examples/Reference Implementations" section (bike.py, weather.py)

- [ ] **Create `dlt_pipeline/Makefile`**
  - [ ] Add `help` target
  - [ ] Add `lint` target (run ruff on dlt_pipeline/)
  - [ ] Add `format` target (format with ruff)
  - [ ] Add `test` target (run pytest tests/test_*_pipeline.py)
  - [ ] Add `build` target (run bike.py && weather.py)
  - [ ] Add `clean` target (remove __pycache__)

- [ ] **Validation**
  - [ ] Run `cd dlt_pipeline && make help` - verify all targets display
  - [ ] Run `cd dlt_pipeline && make lint` - verify passes
  - [ ] Run `cd dlt_pipeline && make test` - verify tests pass
  - [ ] Run `cd dlt_pipeline && make build` - verify ingestion works
  - [ ] Update root CLAUDE.md "Module-Specific CLAUDE.md Files" section to link to `dlt_pipeline/CLAUDE.md`

---

## Slice 3: Transformation Module (dbt) - Documentation + Tooling

**Goal:** Make dbt independently discoverable and runnable with documented SQL patterns.

- [ ] **Create `dbt/CLAUDE.md`**
  - [ ] Use Context7 MCP to research dbt best practices and style guides
  - [ ] Use Context7 MCP to research DuckDB-specific optimization patterns
  - [ ] Add "Module Purpose" section (SQL-based transformation and analytics)
  - [ ] Add "Prerequisites/Dependencies" section (bike_ingestion.duckdb, weather_ingestion.duckdb)
  - [ ] Add "Common Commands" section (reference Makefile targets)
  - [ ] Add "Coding Patterns" section (3-layer structure, naming conventions, materializations, sources, tests)
  - [ ] Add "Examples/Reference Implementations" section (stg_bike_trips.sql, mart_weather_effect.sql)

- [ ] **Create `dbt/Makefile`**
  - [ ] Add `help` target
  - [ ] Add `deps` target (dbt deps)
  - [ ] Add `build` target (dbt build)
  - [ ] Add `run` target (dbt run)
  - [ ] Add `test` target (dbt test)
  - [ ] Add `docs` target (dbt docs generate && serve)
  - [ ] Add `clean` target (remove target/, logs/)

- [ ] **Validation**
  - [ ] Run `cd dbt && make help` - verify all targets display
  - [ ] Run `cd dbt && make deps` - verify packages install
  - [ ] Run `cd dbt && make build` - verify models and tests run
  - [ ] Update root CLAUDE.md "Module-Specific CLAUDE.md Files" section to link to `dbt/CLAUDE.md`

---

## Slice 4: Data Quality Module (data_quality) - Documentation + Tooling

**Goal:** Make data_quality independently discoverable and runnable with validation patterns.

- [ ] **Create `data_quality/CLAUDE.md`**
  - [ ] Use Context7 MCP to research Great Expectations best practices
  - [ ] Use Context7 MCP to research data quality validation patterns for data pipelines
  - [ ] Add "Module Purpose" section (data validation using Great Expectations)
  - [ ] Add "Prerequisites/Dependencies" section (warehouse.duckdb, raw DuckDB files)
  - [ ] Add "Common Commands" section (reference Makefile targets)
  - [ ] Add "Coding Patterns" section (expectation suites, checkpoints, statistical validation)
  - [ ] Add "Examples/Reference Implementations" section (validate_*.py files)

- [ ] **Create `data_quality/Makefile`**
  - [ ] Add `help` target
  - [ ] Add `lint` target (run ruff on data_quality/)
  - [ ] Add `format` target (format with ruff)
  - [ ] Add `build` target (run validate_all.py)
  - [ ] Add `clean` target (remove __pycache__)

- [ ] **Validation**
  - [ ] Run `cd data_quality && make help` - verify all targets display
  - [ ] Run `cd data_quality && make lint` - verify passes
  - [ ] Run `cd data_quality && make build` - verify validation runs
  - [ ] Update root CLAUDE.md "Module-Specific CLAUDE.md Files" section to link to `data_quality/CLAUDE.md`

---

## Slice 5: Visualization Module (streamlit_app) - Documentation + Tooling

**Goal:** Make streamlit_app independently discoverable and runnable with dashboard patterns.

- [ ] **Create `streamlit_app/CLAUDE.md`**
  - [ ] Use Context7 MCP to research Streamlit best practices and performance optimization
  - [ ] Use Context7 MCP to research Plotly best practices for interactive dashboards
  - [ ] Add "Module Purpose" section (interactive dashboards and visualization)
  - [ ] Add "Prerequisites/Dependencies" section (warehouse.duckdb from dbt)
  - [ ] Add "Common Commands" section (reference Makefile targets)
  - [ ] Add "Coding Patterns" section (multi-page structure, read-only connections, Plotly, caching)
  - [ ] Add "Examples/Reference Implementations" section (Home.py, pages/*.py)

- [ ] **Create `streamlit_app/Makefile`**
  - [ ] Add `help` target
  - [ ] Add `lint` target (run ruff on streamlit_app/)
  - [ ] Add `format` target (format with ruff)
  - [ ] Add `build` target (streamlit run Home.py)
  - [ ] Add `clean` target (remove __pycache__)

- [ ] **Validation**
  - [ ] Run `cd streamlit_app && make help` - verify all targets display
  - [ ] Run `cd streamlit_app && make lint` - verify passes
  - [ ] Run `cd streamlit_app && make build` - verify dashboard launches (can Ctrl+C to stop)
  - [ ] Update root CLAUDE.md "Module-Specific CLAUDE.md Files" section to link to `streamlit_app/CLAUDE.md`

---

## Slice 6: Orchestration Module (airflow) - Documentation + Tooling

**Goal:** Make airflow independently discoverable with orchestration patterns.

- [ ] **Create `airflow/CLAUDE.md`**
  - [ ] Use Context7 MCP to research Apache Airflow best practices and TaskFlow API patterns
  - [ ] Use Context7 MCP to research DAG design patterns for data pipelines
  - [ ] Add "Module Purpose" section (workflow orchestration and scheduling)
  - [ ] Add "Prerequisites/Dependencies" section (all other modules)
  - [ ] Add "Common Commands" section (reference Makefile targets)
  - [ ] Add "Coding Patterns" section (TaskFlow API, BashOperator, dependencies, sys.path modification)
  - [ ] Add "Examples/Reference Implementations" section (bike_weather_dag.py)

- [ ] **Create `airflow/Makefile`**
  - [ ] Add `help` target
  - [ ] Add `lint` target (run ruff on airflow/)
  - [ ] Add `format` target (format with ruff)
  - [ ] Add `build` target (airflow dags trigger bike_weather_pipeline - requires Airflow running)
  - [ ] Add `clean` target (remove __pycache__)

- [ ] **Validation**
  - [ ] Run `cd airflow && make help` - verify all targets display
  - [ ] Run `cd airflow && make lint` - verify passes
  - [ ] Update root CLAUDE.md "Module-Specific CLAUDE.md Files" section to link to `airflow/CLAUDE.md`

---

## Slice 7: Analysis Module (notebooks) - Documentation + Tooling

**Goal:** Make notebooks independently discoverable with exploratory analysis patterns.

- [ ] **Create `notebooks/CLAUDE.md`**
  - [ ] Use Context7 MCP to research Jupyter notebook best practices and documentation standards
  - [ ] Use Context7 MCP to research Polars best practices for data analysis workflows
  - [ ] Add "Module Purpose" section (exploratory data analysis and statistical testing)
  - [ ] Add "Prerequisites/Dependencies" section (any DuckDB file - flexible)
  - [ ] Add "Common Commands" section (reference Makefile targets)
  - [ ] Add "Coding Patterns" section (Polars, statistical tests, markdown, inline plots)
  - [ ] Add "Examples/Reference Implementations" section (marts_eda.ipynb)

- [ ] **Create `notebooks/Makefile`**
  - [ ] Add `help` target
  - [ ] Add `lint` target (run ruff on notebooks/ - may have limited value)
  - [ ] Add `format` target (format with ruff)
  - [ ] Add `build` target (jupyter lab)
  - [ ] Add `clean` target (remove .ipynb_checkpoints)

- [ ] **Validation**
  - [ ] Run `cd notebooks && make help` - verify all targets display
  - [ ] Run `cd notebooks && make build` - verify Jupyter launches (can Ctrl+C to stop)
  - [ ] Update root CLAUDE.md "Module-Specific CLAUDE.md Files" section to link to `notebooks/CLAUDE.md`

---

## Slice 8: Root-Level Tooling - Master Makefile

**Goal:** Provide project-wide tooling for cross-module operations.

- [ ] **Create root-level `Makefile`**
  - [ ] Add `help` target
  - [ ] Add `lint` target (run ruff check . on entire project)
  - [ ] Add `format` target (run ruff format . on entire project)
  - [ ] Add `lint-sql` target (cd dbt && dbt compile for SQL validation)
  - [ ] Add `test-all` target (pytest tests/ -v)

- [ ] **Validation**
  - [ ] Run `make help` from project root - verify all targets display
  - [ ] Run `make lint` - verify passes with no new errors
  - [ ] Run `make format` - verify formats code
  - [ ] Run `make test-all` - verify all tests pass

---

## Slice 9: End-to-End Validation

**Goal:** Verify the complete modular structure works end-to-end without breaking existing functionality.

- [ ] **Run full pipeline using Makefile targets**
  - [ ] Run `cd dlt_pipeline && make build && cd ..` - verify ingestion works
  - [ ] Run `cd dbt && make build && cd ..` - verify transformation works
  - [ ] Run `cd data_quality && make build && cd ..` - verify validation works
  - [ ] Verify DuckDB files exist with data (bike_ingestion.duckdb, weather_ingestion.duckdb, warehouse.duckdb)

- [ ] **Verify Airflow DAG still works**
  - [ ] Start Airflow standalone (`uv run airflow standalone`)
  - [ ] Trigger DAG manually or verify it runs on schedule
  - [ ] Confirm all tasks complete successfully

- [ ] **Documentation completeness check**
  - [ ] Verify all 6 module CLAUDE.md files have all mandatory sections
  - [ ] Verify root CLAUDE.md links to all module CLAUDE.md files
  - [ ] Verify all Makefile targets documented match actual Makefile content

- [ ] **Code style validation**
  - [ ] Run `make lint` from root - no new errors
  - [ ] Run `make format --check` from root - all files formatted correctly

- [ ] **Python import verification**
  - [ ] Test `from dlt_pipeline.bike import run_bike_pipeline` works
  - [ ] Test `from dlt_pipeline.weather import run_weather_pipeline` works
  - [ ] Test `from data_quality.validate_all import ...` works (if applicable)

---

## Success Criteria

Implementation is complete when:

- ✅ All six modules have CLAUDE.md files with mandatory sections
- ✅ All applicable modules have Makefiles with standardized targets
- ✅ Root CLAUDE.md includes cross-cutting standards and module registry
- ✅ Python package structure supports Airflow imports
- ✅ End-to-end pipeline executes successfully
- ✅ All Makefile targets work as documented
- ✅ No existing functionality is broken
- ✅ Module dependencies are explicit and traceable
- ✅ Code passes ruff linting and formatting checks
- ✅ Context7 MCP research integrated into coding patterns documentation

---

## Notes on Context7 MCP Usage

**When to use Context7 MCP:**
- When documenting coding patterns and best practices for each module
- To research technology-specific conventions (dlt, dbt, Great Expectations, Streamlit, Airflow, Polars)
- To find authoritative style guides and community standards
- To verify our patterns align with current best practices

**What to research:**
- Official documentation and style guides
- Performance optimization patterns
- Common pitfalls and anti-patterns
- Testing strategies
- Error handling conventions

**How to integrate findings:**
- Extract key patterns and add to "Coding Patterns" sections in module CLAUDE.md files
- Include code examples from authoritative sources
- Reference specific documentation URLs in comments
- Validate our existing code follows discovered best practices
