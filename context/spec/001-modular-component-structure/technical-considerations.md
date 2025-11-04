# Technical Specification: Modular Component Structure

- **Functional Specification:** [functional-spec.md](./functional-spec.md)
- **Status:** Draft
- **Author(s):** AI-Native Data Platform Team

---

## 1. High-Level Technical Approach

This implementation establishes the foundational modular architecture for the AI-Native Data Platform by creating clear module boundaries through documentation and tooling. The approach is **purely additive** - we're adding structure without modifying existing pipeline code.

**Strategy:**
1. Create module-specific CLAUDE.md files in each of the six modules (dlt_pipeline, dbt, data_quality, streamlit_app, airflow, notebooks)
2. Create standardized Makefiles for Python-based and SQL-based modules
3. Enhance root CLAUDE.md with cross-cutting standards
4. Document module communication patterns explicitly via DuckDB file paths
5. Add `__init__.py` files only to modules imported by Airflow

**Key Systems Affected:**
- Documentation structure (new CLAUDE.md files per module)
- Build tooling (new Makefiles per module)
- Python package structure (selective `__init__.py` additions)
- Root-level documentation (enhanced CLAUDE.md)

**Non-Goals:**
- No changes to existing pipeline code (bike.py, weather.py, DAG, etc.)
- No changes to existing configuration files (profiles.yml, dbt_project.yml, etc.)
- No automated validation tooling (deferred to future phases)

---

## 2. Proposed Solution & Implementation Plan (The "How")

### 2.1 Python Package Structure

**Modules requiring `__init__.py` (imported by Airflow):**

1. **`data_quality/__init__.py`** (NEW)
   - Currently missing, needed because Airflow DAG will import validation functions
   - Content: Empty file with docstring
   ```python
   """Data quality validation module using Great Expectations."""
   ```

2. **`dlt_pipeline/__init__.py`** (EXISTS)
   - Already present
   - Currently imported by Airflow DAG (`from dlt_pipeline.bike import run_bike_pipeline`)

**Modules NOT requiring `__init__.py`:**
- `streamlit_app/` - Executed as script, not imported
- `airflow/` - Container for DAGs, not imported
- `notebooks/` - Executed interactively, not imported
- `dbt/` - SQL-based, not a Python package

### 2.2 Module Documentation Structure (CLAUDE.md Files)

Each module will receive a CLAUDE.md file with mandatory sections:

#### **Template Structure:**
```markdown
# [Module Name] Module

## Module Purpose
[Brief description of what this module does and why it exists]

## Prerequisites/Dependencies
This module requires:
- [Specific file path or module output]
- [Configuration file locations]

## Common Commands
[Makefile targets with descriptions and examples]

## Coding Patterns
[Module-specific conventions, naming, structure, error handling]

## Examples/Reference Implementations
[Links to working code demonstrating all patterns]
```

#### **Module-Specific Documentation:**

**1. `dlt_pipeline/CLAUDE.md`**
- **Purpose:** Data ingestion from APIs and files to DuckDB
- **Dependencies:** None (entry point)
- **Outputs:** `duckdb/bike_ingestion.duckdb`, `duckdb/weather_ingestion.duckdb`
- **Patterns:**
  - dlt resource decorator usage
  - `write_disposition="merge"` with primary keys
  - Polars for CSV parsing
  - Local file caching in `.cache/`
  - Error handling (continue on individual month failures)
- **Examples:** `bike.py`, `weather.py`

**2. `dbt/CLAUDE.md`**
- **Purpose:** SQL-based transformation and analytics modeling
- **Dependencies:**
  - `duckdb/bike_ingestion.duckdb` (from dlt_pipeline)
  - `duckdb/weather_ingestion.duckdb` (from dlt_pipeline)
- **Outputs:** `duckdb/warehouse.duckdb`
- **Patterns:**
  - Three-layer structure: staging → core → marts
  - Model naming: `stg_*`, `dim_*`, `fact_*`, `mart_*`
  - Materialization strategies (views for staging, tables for core/marts)
  - Source definitions in `staging/sources.yml`
  - Schema tests in `schema.yml` files
  - Attached database references (e.g., `{{ source('bike', 'bike_trips') }}`)
- **Examples:** `models/staging/stg_bike_trips.sql`, `models/marts/mart_weather_effect.sql`

**3. `data_quality/CLAUDE.md`**
- **Purpose:** Data validation using Great Expectations
- **Dependencies:**
  - `duckdb/warehouse.duckdb` (from dbt)
  - `duckdb/bike_ingestion.duckdb` (for raw data validation)
  - `duckdb/weather_ingestion.duckdb` (for raw data validation)
- **Outputs:** Validation reports in `gx/uncommitted/data_docs/`
- **Patterns:**
  - Expectation suites in `gx/expectations/`
  - Checkpoint execution
  - Statistical validation (value ranges, null checks, distribution checks)
- **Examples:** `validate_bike_data.py`, `validate_weather_data.py`, `validate_all.py`

**4. `streamlit_app/CLAUDE.md`**
- **Purpose:** Interactive dashboards and visualization
- **Dependencies:** `duckdb/warehouse.duckdb` (from dbt)
- **Outputs:** Web UI on http://localhost:8501
- **Patterns:**
  - Multi-page app structure (`pages/` directory)
  - Read-only DuckDB connections
  - Plotly for interactive charts
  - Streamlit caching decorators
- **Examples:** `Home.py`, `pages/*.py`

**5. `airflow/CLAUDE.md`**
- **Purpose:** Workflow orchestration and scheduling
- **Dependencies:** All other modules
- **Outputs:** Orchestrated pipeline execution
- **Patterns:**
  - TaskFlow API with `@task` decorators
  - BashOperator for dbt commands
  - Task dependencies (>>)
  - DAG structure with default_args
  - sys.path modification for imports (with E402 ignore)
- **Examples:** `dags/bike_weather_dag.py`

**6. `notebooks/CLAUDE.md`**
- **Purpose:** Exploratory data analysis and statistical testing
- **Dependencies:** Any DuckDB file (flexible)
- **Outputs:** Analysis reports, visualizations
- **Patterns:**
  - Polars for DataFrame operations
  - Statistical tests (scipy, statsmodels)
  - Markdown documentation in cells
  - Plot inline with matplotlib/seaborn
- **Examples:** `marts_eda.ipynb`

### 2.3 Standardized Makefile Implementation

#### **Python Modules Makefile Template** (dlt_pipeline, data_quality, streamlit_app, airflow, notebooks)

```makefile
.PHONY: help test lint format build clean

help:  ## Show available targets with descriptions
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

test:  ## Run module-specific tests
	uv run pytest tests/[module-specific-pattern] -v

lint:  ## Run ruff checks
	uv run ruff check .

format:  ## Format code with ruff
	uv run ruff format .

clean:  ## Cleanup generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:  ## Execute module's main function
	[module-specific command]
```

**Module-Specific Build Commands:**

| Module | `make build` Command |
|--------|---------------------|
| `dlt_pipeline/` | `uv run python bike.py && uv run python weather.py` |
| `data_quality/` | `uv run python validate_all.py` |
| `streamlit_app/` | `uv run streamlit run Home.py` |
| `airflow/` | `uv run airflow dags trigger bike_weather_pipeline` |
| `notebooks/` | `uv run jupyter lab` |

#### **dbt Module Makefile**

```makefile
.PHONY: help deps build run test docs clean

help:  ## Show available targets with descriptions
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

deps:  ## Install dbt packages
	uv run dbt deps

build:  ## Run dbt build (models + tests)
	uv run dbt build

run:  ## Run dbt models only
	uv run dbt run

test:  ## Run dbt tests only
	uv run dbt test

docs:  ## Generate and serve dbt docs
	uv run dbt docs generate
	uv run dbt docs serve

clean:  ## Remove target/ and logs/
	rm -rf target/ logs/
```

#### **Root-Level Master Makefile**

```makefile
.PHONY: help lint format lint-sql test-all

help:  ## Show available targets
	@echo "Master Makefile - Project-wide operations"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

lint:  ## Run ruff checks across all Python modules
	uv run ruff check .

format:  ## Format all Python code with ruff
	uv run ruff format .

lint-sql:  ## Run SQLFluff on dbt models (if configured)
	cd dbt && uv run dbt compile

test-all:  ## Run all tests
	uv run pytest tests/ -v
```

### 2.4 Root CLAUDE.md Enhancements

Add a new section to the existing root `CLAUDE.md`:

```markdown
## Cross-Cutting Standards

### Logging Format

All Python modules MUST use this logging configuration:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
```

### Error Handling Principles

- **Use specific exceptions:** Prefer specific exception types over generic `Exception`
- **Log before raising:** Always log error context before raising exceptions
- **Graceful degradation:** For batch operations (e.g., processing multiple months), continue processing remaining items if one fails
- **Timeout configuration:** Set reasonable timeouts for HTTP requests (default: 300s)

Example pattern from `dlt_pipeline/bike.py`:
```python
for month_str in months_to_load:
    try:
        # Process month
        logger.info("Processing %s", month_str)
        # ... processing logic ...
    except requests.exceptions.RequestException as e:
        logger.error("Failed to process %s: %s", month_str, e)
        continue  # Continue with next month
```

### Code Style (Ruff Configuration)

Project uses Ruff for linting and formatting with the following configuration:

- **Line length:** 100 characters
- **Target Python version:** 3.11+
- **String quotes:** Double quotes
- **Import sorting:** Enabled (isort)
- **Per-file ignores:**
  - `airflow/dags/*.py`: E402, I001 (imports after sys.path modifications)
  - `notebooks/*.ipynb`: T201, I001 (print statements and unsorted imports allowed)

Run checks:
```bash
uv run ruff check .
uv run ruff format .
```

### Module Execution Order

**Sequential dependency chain:**
1. **dlt_pipeline** → Ingest raw data to DuckDB
2. **dbt** → Transform raw data in warehouse
3. **data_quality** → Validate transformed data
4. **streamlit_app / notebooks** → Visualize and analyze (can run in parallel)

**Airflow orchestration order:**
```
ingest_bike_data ─┐
                  ├─→ validate_bike_data ─┐
ingest_weather_data ┘                     ├─→ dbt_transform → dbt_test
                                          │
                   validate_weather_data ─┘
```

### Module Communication Pattern

Modules communicate via **DuckDB file paths**:

| Producer Module | Output File | Consumer Module(s) |
|----------------|-------------|-------------------|
| dlt_pipeline | `duckdb/bike_ingestion.duckdb` | dbt, data_quality |
| dlt_pipeline | `duckdb/weather_ingestion.duckdb` | dbt, data_quality |
| dbt | `duckdb/warehouse.duckdb` | data_quality, streamlit_app, notebooks |

Configuration files specify these paths:
- **dlt:** Uses pipeline name to auto-create `duckdb/{pipeline_name}.duckdb`
- **dbt:** Uses `profiles.yml` to attach external databases and write to warehouse
- **Consumers:** Read-only connections to warehouse

### DuckDB Locking Constraints

**CRITICAL:** Only one process can write to a DuckDB file at a time.

- **Development:** Run modules sequentially (use Makefile targets)
- **Production:** Airflow DAG enforces task dependencies
- **Symptom of violation:** "database is locked" error
- **Resolution:** Ensure previous task completes before starting next

### Module-Specific CLAUDE.md Files

Each module has its own CLAUDE.md with detailed patterns:

- `dlt_pipeline/CLAUDE.md` - Data ingestion patterns
- `dbt/CLAUDE.md` - SQL transformation patterns
- `data_quality/CLAUDE.md` - Validation patterns
- `streamlit_app/CLAUDE.md` - Dashboard patterns
- `airflow/CLAUDE.md` - Orchestration patterns
- `notebooks/CLAUDE.md` - Analysis patterns

**Subagent workflow:** Always check for module-level CLAUDE.md before starting work in that module.
```

---

## 3. Impact and Risk Analysis

### System Dependencies

**Module Interdependency Graph:**
```
dlt_pipeline (entry point)
    ├─→ bike_ingestion.duckdb
    │   ├─→ dbt (reads via attach)
    │   └─→ data_quality (raw validation)
    │
    └─→ weather_ingestion.duckdb
        ├─→ dbt (reads via attach)
        └─→ data_quality (raw validation)

dbt
    └─→ warehouse.duckdb
        ├─→ data_quality (transformed validation)
        ├─→ streamlit_app (visualization)
        └─→ notebooks (analysis)

airflow (orchestrates all modules)
```

**Critical Path:** dlt_pipeline → dbt → {data_quality, streamlit_app, notebooks}

### Potential Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| **Module execution order confusion** | High - Pipeline failures | Medium | Root CLAUDE.md explicitly documents dependency graph. Each module's CLAUDE.md lists prerequisites with specific paths. |
| **Inconsistent Makefile implementations** | Medium - User confusion | Medium | Use template-based approach. Document deviations in module CLAUDE.md. |
| **Breaking existing workflows** | High - Development disruption | Low | Implementation is purely additive (no code changes). Validate existing commands still work. |
| **DuckDB file locking conflicts** | High - Pipeline failures | Low | Document locking constraints in root CLAUDE.md. Airflow DAG already enforces sequential execution. |
| **Subagents not finding CLAUDE.md files** | High - Defeats purpose | Medium | Root CLAUDE.md lists all module CLAUDE.md locations. Establish convention in subagent definitions. |
| **Documentation drift over time** | Medium - Outdated guidance | High | Include CLAUDE.md updates in PR review checklist (deferred to Development Standards feature). |
| **Module patterns not discoverable** | Medium - Inconsistent code | Medium | Each CLAUDE.md includes "Examples/Reference Implementations" section pointing to working code. |

---

## 4. Testing Strategy

### 4.1 Manual Verification Tests (Per-Module)

**For each module with a Makefile:**
- [ ] `make help` displays all targets with descriptions
- [ ] `make lint` runs successfully
- [ ] `make format` runs without errors
- [ ] `make build` executes the module's primary function
- [ ] `make clean` removes generated artifacts
- [ ] `make test` runs module-specific tests (where applicable)

**For dbt module specifically:**
- [ ] `make deps` installs dbt packages
- [ ] `make run` executes models
- [ ] `make test` runs schema tests
- [ ] `make docs` generates and serves documentation

### 4.2 End-to-End Pipeline Validation

Execute the complete pipeline to ensure no functionality is broken:

```bash
# 1. Ingestion
cd dlt_pipeline && make build && cd ..

# 2. Transformation
cd dbt && make build && cd ..

# 3. Validation
cd data_quality && make build && cd ..

# 4. Visualization
cd streamlit_app && make build && cd ..
```

**Success criteria:**
- [ ] All steps complete without errors
- [ ] DuckDB files are created/updated with expected data
- [ ] Airflow DAG `bike_weather_pipeline` runs successfully
- [ ] Streamlit dashboard displays correctly

### 4.3 Documentation Completeness Check

**For each module's CLAUDE.md:**
- [ ] All mandatory sections present:
  - Module Purpose
  - Prerequisites/Dependencies
  - Common Commands
  - Coding Patterns
  - Examples/Reference Implementations
- [ ] Prerequisites list specific file paths (not generic descriptions)
- [ ] Examples reference actual files in the module
- [ ] Cross-references to other modules are accurate (file paths exist)
- [ ] Commands in "Common Commands" section match Makefile targets

**For root CLAUDE.md enhancements:**
- [ ] Cross-cutting standards section added
- [ ] Logging format documented with code example
- [ ] Error handling principles documented
- [ ] Module execution order diagram present
- [ ] Module communication table accurate
- [ ] Links to all module CLAUDE.md files included

### 4.4 Code Style Validation

Run linting at project root to ensure no new issues:

```bash
uv run ruff check .
uv run ruff format . --check
```

**Success criteria:**
- [ ] No new linting errors introduced
- [ ] All Python files pass formatting checks
- [ ] Per-file ignores are working correctly (airflow DAGs, notebooks)

### 4.5 Python Package Import Verification

Verify that modules with `__init__.py` can be imported by Airflow:

```python
# Test in Python REPL or script
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Should work (has __init__.py)
from dlt_pipeline.bike import run_bike_pipeline
from dlt_pipeline.weather import run_weather_pipeline
from data_quality.validate_all import main  # Assuming this exists

print("All imports successful!")
```

**Success criteria:**
- [ ] dlt_pipeline imports work
- [ ] data_quality imports work (after `__init__.py` added)
- [ ] No ImportError exceptions

### 4.6 Subagent Comprehension Test (Post-Implementation)

Simulate subagent behavior by asking task-based questions:

**Test scenarios:**
1. "I need to add a new weather API. Which module should I work in?"
   - Expected: Subagent identifies `dlt_pipeline/` by reading module CLAUDE.md files
2. "What's the correct logging format for this project?"
   - Expected: Subagent references root CLAUDE.md cross-cutting standards
3. "How do I run just the bike data pipeline?"
   - Expected: Subagent finds `dlt_pipeline/CLAUDE.md` and uses `make build` or references `bike.py`
4. "What does dbt depend on?"
   - Expected: Subagent reads `dbt/CLAUDE.md` prerequisites section and identifies attached DuckDB files

**Success criteria:**
- [ ] Subagent can locate relevant module documentation
- [ ] Subagent can identify module dependencies
- [ ] Subagent can find example implementations
- [ ] Subagent follows documented patterns

---

## 5. Implementation Checklist

### Phase 1: Python Package Structure
- [ ] Add `data_quality/__init__.py`
- [ ] Verify `dlt_pipeline/__init__.py` exists (should already be present)

### Phase 2: Module CLAUDE.md Files
- [ ] Create `dlt_pipeline/CLAUDE.md`
- [ ] Create `dbt/CLAUDE.md`
- [ ] Create `data_quality/CLAUDE.md`
- [ ] Create `streamlit_app/CLAUDE.md`
- [ ] Create `airflow/CLAUDE.md`
- [ ] Create `notebooks/CLAUDE.md`

### Phase 3: Makefile Creation
- [ ] Create `dlt_pipeline/Makefile`
- [ ] Create `dbt/Makefile`
- [ ] Create `data_quality/Makefile`
- [ ] Create `streamlit_app/Makefile`
- [ ] Create `airflow/Makefile`
- [ ] Create `notebooks/Makefile`
- [ ] Create root-level master `Makefile`

### Phase 4: Root Documentation Enhancement
- [ ] Add "Cross-Cutting Standards" section to root `CLAUDE.md`
- [ ] Add "Module Execution Order" section to root `CLAUDE.md`
- [ ] Add "Module Communication Pattern" section to root `CLAUDE.md`
- [ ] Add "Module-Specific CLAUDE.md Files" section to root `CLAUDE.md`

### Phase 5: Validation
- [ ] Run all Makefile targets (per module)
- [ ] Execute end-to-end pipeline
- [ ] Verify documentation completeness
- [ ] Run code style validation
- [ ] Test Python package imports
- [ ] Perform subagent comprehension tests

---

## 6. Success Criteria

Implementation is complete when:

1. ✅ All six modules have CLAUDE.md files with mandatory sections
2. ✅ All applicable modules have Makefiles with standardized targets
3. ✅ Root CLAUDE.md includes cross-cutting standards and module registry
4. ✅ Python package structure supports Airflow imports
5. ✅ End-to-end pipeline executes successfully
6. ✅ All Makefile targets work as documented
7. ✅ No existing functionality is broken
8. ✅ Subagents can identify correct module for given tasks
9. ✅ Module dependencies are explicit and traceable
10. ✅ Code passes ruff linting and formatting checks
