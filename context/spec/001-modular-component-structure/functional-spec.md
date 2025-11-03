# Functional Specification: Modular Component Structure

- **Roadmap Item:** Establish clear separation between dlt_pipeline, dbt, data_quality, streamlit_app, airflow, and notebooks modules with consistent patterns within each.
- **Status:** Draft
- **Author:** AI-Native Data Platform Team

---

## 1. Overview and Rationale (The "Why")

This is a foundational feature in Phase 1 that establishes the core architectural structure of the AI-Native Data Platform. The goal is to create clear module boundaries so that specialized subagents can understand and work within their specific domains without confusion.

**User Problem:** "Alex the Automation Engineer" needs to delegate data engineering tasks to specialized subagents, but without clear module boundaries, subagents struggle to understand their scope of work and could introduce cross-module inconsistencies. Generic AI-generated code doesn't follow module-specific practices.

**Desired Outcome:** Each module (dlt_pipeline, dbt, data_quality, streamlit_app, airflow, notebooks) has clear boundaries, consistent internal patterns, and well-defined interfaces with other modules. This enables specialized subagents to work confidently within their designated areas.

**Success Metrics:**
- Each module can be run independently via Makefile targets
- Subagents can identify which module they should work in based on the task
- Module interfaces are explicit and documented
- Cross-cutting concerns (logging, error handling, code style) are consistent across all modules

---

## 2. Functional Requirements (The "What")

### 2.1 Module Directory Structure

Each module must have a standardized internal structure:

- **Acceptance Criteria:**
  - [ ] Each Python module contains an `__init__.py` file
  - [ ] Each module has a `CLAUDE.md` file documenting module-specific patterns and practices
  - [ ] Each module has a `tests/` subdirectory for module-specific tests
  - [ ] Each module has a `Makefile` with standardized targets (where applicable)
  - [ ] Module names use lowercase with underscores (e.g., `dlt_pipeline/`, `data_quality/`)
  - [ ] Python files within modules use snake_case naming (e.g., `bike_pipeline.py`)
  - [ ] SQL files use snake_case with prefixes (e.g., `stg_bike_trips.sql`, `mart_demand_daily.sql`)
  - [ ] Test files follow the pattern `test_<module_name>.py`

### 2.2 Module Communication & Data Flow

Modules must communicate through explicit, documented interfaces:

- **Acceptance Criteria:**
  - [ ] Each module that produces data specifies its output location in its native configuration file (e.g., dlt uses `.dlt/config.toml`, dbt uses `profiles.yml`)
  - [ ] Downstream modules reference upstream output paths explicitly in their configuration
  - [ ] Each module's `CLAUDE.md` documents its dependencies with a "Prerequisites/Dependencies" section stating: "This module requires: [X module's output at Y path]"
  - [ ] Data flow uses DuckDB file paths as the primary mechanism (e.g., dbt attaches to `bike_ingestion.duckdb` and `weather_ingestion.duckdb`)
  - [ ] Dependencies are visible and traceable by reading configuration files

### 2.3 Module Independence

Each module must be runnable standalone for testing and development:

- **Acceptance Criteria:**
  - [ ] Each module can be executed independently via its Makefile targets (e.g., `cd dbt && make build` runs dbt without Airflow)
  - [ ] Module execution does not require the full Airflow orchestration to function
  - [ ] Developers and subagents can test individual modules in isolation
  - [ ] Module failures are isolated and don't crash other modules

### 2.4 Cross-Cutting Standards (Root-Level)

Common patterns must be documented at the root level and applied consistently:

- **Acceptance Criteria:**
  - [ ] Root `CLAUDE.md` documents cross-cutting patterns including:
    - Python coding style (ruff configuration)
    - Logging format (consistent `logging.basicConfig()` format string across all modules)
    - Error handling approaches
    - Git workflow conventions
  - [ ] All Python modules use the same logger format as specified in root `CLAUDE.md`
  - [ ] All Python modules follow the ruff linting configuration defined at project root
  - [ ] Module-specific exceptions are acceptable, but naming conventions are documented in each module's `CLAUDE.md`

### 2.5 Module Configuration Management

Each module uses its technology's native configuration format:

- **Acceptance Criteria:**
  - [ ] No forced standardization of configuration formats across modules (dlt uses `.dlt/config.toml`, dbt uses `profiles.yml`, etc.)
  - [ ] Each module's `CLAUDE.md` documents its configuration file locations and format
  - [ ] Configuration files include comments explaining key settings for subagent comprehension

### 2.6 Standardized Makefile Targets

For Python-based modules, standardized Makefile targets enable consistent operations:

- **Acceptance Criteria:**
  - [ ] Python modules (`dlt_pipeline/`, `data_quality/`, `streamlit_app/`, `airflow/`, `notebooks/`) have a `Makefile` with standard targets:
    - `make test` - run module-specific tests
    - `make lint` - run ruff checks
    - `make format` - format code with ruff
    - `make build` - execute the module's main function
    - `make clean` - cleanup generated files
    - `make help` - show available targets and their descriptions
  - [ ] SQL-based modules (dbt) have appropriate targets for their tooling (e.g., `make build` runs `dbt build`)
  - [ ] Master Makefile at project root can run Python formatting/linting across all modules
  - [ ] Master Makefile at project root can run SQL formatting for dbt models
  - [ ] Makefile target order is documented when sequence matters

### 2.7 Module Documentation (CLAUDE.md)

Each module must have comprehensive documentation for subagent comprehension:

- **Acceptance Criteria:**
  - [ ] Every module has a `CLAUDE.md` file with the following mandatory sections:
    - **Module Purpose:** What this module does and why it exists
    - **Prerequisites/Dependencies:** What this module requires from other modules (with specific paths)
    - **Common Commands:** Makefile targets and their usage
    - **Coding Patterns:** Module-specific conventions (naming, structure, error handling)
    - **Examples/Reference Implementations:** Working code demonstrating all patterns
  - [ ] Module setup requirements are documented in the Prerequisites section (e.g., "Run `dbt deps` first", "Ensure `.dlt/config.toml` exists")
  - [ ] No separate `README.md` files are created (CLAUDE.md is sufficient for both AI and human developers)

### 2.8 Module Initialization Order

The order of module setup and execution must be clear:

- **Acceptance Criteria:**
  - [ ] Root `CLAUDE.md` documents the correct order for module initialization and execution
  - [ ] The order specifies which modules must be set up before others (e.g., dlt before dbt)
  - [ ] Subagents can determine execution order by reading the root documentation
  - [ ] Airflow DAG demonstrates the production execution order with explicit task dependencies

### 2.9 Pattern Consistency Verification

Module patterns must be verifiable through examples and documentation:

- **Acceptance Criteria:**
  - [ ] Each module contains working example files demonstrating all required patterns (e.g., `bike.py` and `weather.py` in `dlt_pipeline/`)
  - [ ] Module `CLAUDE.md` documents common patterns with code snippets
  - [ ] Subagents can learn patterns by examining reference implementations within the module
  - [ ] Pattern adherence is verified through code review (automated linting/validation deferred to future phases)

---

## 3. Scope and Boundaries

### In-Scope

- Establishing clear directory structure for all six modules: dlt_pipeline, dbt, data_quality, streamlit_app, airflow, notebooks
- Creating CLAUDE.md files for each module with mandatory sections
- Documenting cross-cutting standards in root CLAUDE.md
- Setting up Makefile targets for Python and SQL modules
- Documenting module dependencies and execution order
- Providing reference implementation examples in each module
- Defining module communication through DuckDB file paths and configuration files

### Out-of-Scope

- **Reference Data Sources** (separate roadmap item in Phase 1)
- **Root-Level Documentation** for project-wide CLAUDE.md (separate roadmap item in Phase 1)
- **Development Standards** documentation (separate roadmap item in Phase 1)
- **Code Quality Tools** setup (separate roadmap item in Phase 1)
- **Unit Testing Framework** establishment (separate roadmap item in Phase 1)
- All Phase 2 items (module-specific documentation beyond basic CLAUDE.md structure)
- All Phase 3 items (specialized subagent system)
- All Phase 4 items (AWOS workflow integration)
- Automated pattern validation tools (deferred to future enhancement)
- Master `make setup` command (not needed)
- Standardized configuration formats across different technologies
