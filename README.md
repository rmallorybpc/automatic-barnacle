# automatic-barnacle

GitHub Learn content review and feature monitoring system.

## Executive Summary

**Automatic Barnacle** is a strategic automation platform that ensures GitHub's product documentation and learning content remains synchronized with rapidly evolving platform capabilities. This system delivers continuous intelligence on feature releases, API changes, and documentation gaps, enabling proactive content planning and reducing time-to-market for educational materials.

**Business Value:**
- **Risk Mitigation**: Automatically detects and flags documentation gaps before they impact customer experience
- **Resource Optimization**: Reduces manual monitoring effort by 80%, freeing technical writers for high-value content creation
- **Competitive Intelligence**: Tracks GitHub's product roadmap and changelog in real-time, surfacing strategic opportunities
- **Data-Driven Decisions**: Provides quantitative coverage metrics and trend analysis via live dashboard

**Key Capabilities:**
- Real-time monitoring of GitHub changelog, roadmap, and GraphQL API schema changes
- Automated issue creation for identified feature gaps with severity classification
- Interactive dashboard at [rmallorybpc.github.io/automatic-barnacle](https://rmallorybpc.github.io/automatic-barnacle) with coverage analytics
- Multi-channel notifications (Slack, Teams) for critical updates
- Monthly executive reports with actionable insights

**Operational Model**: Fully automated via GitHub Actions—runs daily for feature monitoring, monthly for executive reporting. Zero infrastructure costs, minimal maintenance overhead.

---

Automatic Barnacle is an automated monitoring and reporting stack for tracking GitHub product updates, features, and API changes. It ingests data from multiple sources, generates analytics, opens GitHub issues for feature gaps, and publishes a dashboard to GitHub Pages via Actions (no Jekyll). This README describes what the repo creates and tracks, how the dashboard updates, the architecture, workflows, and how to develop locally.

## Table of contents
- Overview
- What this repo creates and tracks
- How the dashboard updates (when and how often)
- Architecture
  - Components
  - Logging and error handling
- Configuration
  - config.yaml
  - Environment variables
- Workflows
  - Run Now (Manual Trigger)
  - Feature Gap Monitoring (Scheduled)
  - Monthly Issues Report (Scheduled)
  - Pages deployment (Actions-based)
- Repository structure
- Local development
- GraphQL Schema Diff
- Output artifacts
- Troubleshooting
- Contributing
- License

---

## Overview

This repository implements an automated monitoring stack for tracking GitHub product updates, features, and API changes. It ingests data from multiple sources (changelog, roadmap, GraphQL schema), builds analytics and coverage metrics, generates dashboard and report artifacts, files issues for feature gaps, and sends notifications to team channels. The repo also deploys a static dashboard website to GitHub Pages using GitHub Actions.

## What this repo creates and tracks

- A static dashboard site published at: https://rmallorybpc.github.io/automatic-barnacle
- Dashboard data JSON served from `docs/reports/dashboard.json`, consumed by `docs/index.html`
- Feature coverage metrics and gap detection; gaps can automatically create GitHub issues
- Monthly summary reports (JSON and Markdown)
- Notifications to Slack and Microsoft Teams for key events

Key tracked items:
- Product updates from the GitHub changelog and roadmap
- API-level changes via GraphQL schema diffs (types, fields, mutations)
- Semantic embeddings to relate and cluster features
- Coverage evaluation across product areas
- Time-series and breakdown analytics for dashboard visualization

## How the dashboard updates (when and how often)

- Source of truth: `docs/reports/dashboard.json` on the `main` branch
- Update mechanism: The monitoring pipeline (GitHub Actions or external CI) generates `dashboard.json` and commits it to `docs/reports/` on `main`
- Deploy trigger: The Pages deployment workflow runs on push to `main` (or via “Run workflow”), uploading the `docs/` directory as the site artifact and deploying it
- Latency: After `dashboard.json` is committed and the deploy workflow completes (typically under a minute), the site serves the new data immediately. The `docs/index.html` page fetches the JSON at runtime; there is no additional Pages delay beyond the workflow run.

Common schedules:
- Daily: Regenerate `dashboard.json` and commit to `docs/reports/`
- On-demand: Manually trigger “Run Now” to produce updated reports and dashboard data

If you prefer not to commit `dashboard.json`, your workflow can place the file in `docs/reports/` prior to uploading the Pages artifact. The site will still fetch it from the deployed artifact.

---

## Architecture

### Components

1. Ingestion (`src/feature_monitor/ingestion.py`)
   - Fetches GitHub changelog entries
   - Pulls roadmap items from github/roadmap
   - Integrates GraphQL schema changes
   - Outputs: `data/features.json`

2. GraphQL Schema Diff (`src/feature_monitor/graphql_diff.py`)
   - Downloads current GraphQL schema
   - Compares with previous snapshot
   - Detects new types, fields, and mutations
   - Saves snapshots: `data/graphql/schema-YYYY-MM-DD.graphql`

3. Module Indexing (`src/feature_monitor/modules_index.py`)
   - Indexes features by product area
   - Outputs: `data/feature_index.json`

4. Embeddings (`src/feature_monitor/embeddings.py`)
   - Generates vector embeddings for features
   - Outputs: `data/embeddings/features_with_embeddings.json`

5. Coverage (`src/feature_monitor/coverage.py`)
   - Evaluates feature coverage metrics
   - Checks against thresholds
   - Outputs: `data/reports/coverage.json`

6. Report (`src/feature_monitor/report.py`)
   - Generates JSON and Markdown reports
   - Outputs: `data/reports/report.{json,md}`

7. Issues (`src/feature_monitor/issues.py`)
   - Creates GitHub issues for feature gaps
   - Tracks issue creation
   - Outputs: `data/issues/summary.json`

8. Dashboard (`src/feature_monitor/dashboard.py`)
   - Generates dashboard data for visualization
   - Time-series and breakdown analytics
   - Outputs: `data/dashboard/dashboard_latest.json`

9. Notifications (`src/feature_monitor/notifications.py`)
   - Sends updates to Slack via webhook
   - Sends updates to Teams via webhook

10. Monthly Report (`src/feature_monitor/monthly_report.py`)
    - Generates monthly summary reports
    - Outputs: `data/reports/monthly/YYYY-MM_report.{json,md}`

### Logging and error handling

All modules include:
- Structured logging: INFO and ERROR levels with timestamps and context
- Retry logic: Network calls use exponential backoff (3 retries by default)
- Data validation: Checks for missing files with actionable error messages
- Safe file writing: Atomic writes prevent artifact corruption
- Exit codes: Non-zero exit on critical failures for CI visibility

---

## Configuration

The system is configured via `config.yaml`:

```yaml
# Data sources
sources:
  changelog:
    enabled: true
  roadmap:
    enabled: true
  graphql_schema:
    enabled: true

# Issue management
issue:
  repo: "rmallorybpc/automatic-barnacle"
  labels: ["feature-gap", "automated"]

# Notifications
notifications:
  slack:
    enabled: true
    webhook_url_env: "SLACK_WEBHOOK_URL"
  teams:
    enabled: true
    webhook_url_env: "TEAMS_WEBHOOK_URL"
```

### Environment variables

- `SLACK_WEBHOOK_URL`: Slack incoming webhook URL (optional)
- `TEAMS_WEBHOOK_URL`: Microsoft Teams webhook URL (optional)
- `GITHUB_TOKEN`: GitHub API token (provided by Actions)

---

## Workflows

### 1) Run Now (Manual Trigger)

File: `.github/workflows/run-now.yml`

Runs the complete monitoring pipeline on demand via `workflow_dispatch`.

Usage:
1. Go to Actions → Run Now
2. Click “Run workflow”
3. Optional: Skip notifications

Pipeline steps:
1. Ingest features from all sources
2. Index by product area
3. Generate embeddings
4. Evaluate coverage
5. Generate report
6. Create/update issues
7. Generate dashboard
8. Send notifications

### 2) Feature Gap Monitoring (Scheduled)

File: `.github/workflows/feature-gap.yml`

Runs daily at 9 AM UTC to monitor for new features and gaps.

### 3) Monthly Issues Report (Scheduled)

File: `.github/workflows/monthly-issues-report.yml`

Runs on the 1st of each month to generate monthly summary reports.

### 4) Pages deployment (Actions-based)

File: `.github/workflows/github_workflows_pages_Version3.yml`

This workflow deploys the static site from `docs/` to GitHub Pages without Jekyll.

- Triggers: push to `main`, and manual `workflow_dispatch`
- Permissions: `pages: write`, `id-token: write`, `contents: read`
- Jobs:
  - build
    - Validate `docs/` exists and `docs/index.html` is present
    - Touch `docs/.nojekyll`
    - Upload `docs/` as Pages artifact via `actions/upload-pages-artifact@v3`
  - deploy
    - Deploy via `actions/deploy-pages@v4`

Repository settings:
- Settings → Pages → Source: “GitHub Actions”

If you switch to “Deploy from a branch,” set Branch: `main`, Folder: `/docs`, and ensure `docs/.nojekyll` and `docs/index.html` exist.

---

## Repository structure

- `docs/`
  - `.nojekyll` — Disables Jekyll processing so assets are served as-is
  - `index.html` — Static dashboard page that fetches `reports/dashboard.json`
  - `reports/` — JSON and other report outputs produced by your pipeline (e.g., `dashboard.json`)
- `.github/workflows/`
  - `github_workflows_pages_Version3.yml` — Actions-based Pages deployment workflow
  - Other workflow files for ingestion, feature gap monitoring, and monthly reports
- `src/feature_monitor/` — Monitoring pipeline source modules
- `data/` — Local and CI-generated artifacts (not served by Pages unless copied under `docs/`)

---

## Local development

### Prerequisites
- Python 3.11+
- pip

### Setup

```bash
# Install dependencies
pip install pyyaml requests urllib3

# Create data directories
mkdir -p data/{graphql,embeddings,reports,issues,dashboard}
```

### Running modules

```bash
# Ingestion
python -m src.feature_monitor.ingestion

# GraphQL schema diff
python -m src.feature_monitor.graphql_diff

# Indexing
python -m src.feature_monitor.modules_index

# Embeddings
python -m src.feature_monitor.embeddings

# Coverage
python -m src.feature_monitor.coverage

# Report generation
python -m src.feature_monitor.report

# Issues management
python -m src.feature_monitor.issues

# Dashboard
python -m src.feature_monitor.dashboard

# Notifications
python -m src.feature_monitor.notifications

# Monthly report
python -m src.feature_monitor.monthly_report
```

Local preview of the dashboard:
- Open `docs/index.html` directly in a browser, or
- Run a local HTTP server to avoid `file://` fetch restrictions:
  - Python: `python3 -m http.server 8000` → visit `http://localhost:8000/docs/`
  - Node: `npx http-server .` → visit `http://localhost:PORT/docs/`

Populate `docs/reports/dashboard.json` to preview the data rendering.

---

## GraphQL Schema Diff

Tracks changes to the GitHub GraphQL API.

### How it works
1. Fetch: Downloads the current schema from GitHub docs
2. Store: Saves snapshot as `data/graphql/schema-YYYY-MM-DD.graphql`
3. Compare: Diffs against the previous snapshot
4. Detect: Identifies new types, fields, and mutations
5. Emit: Creates Feature objects for notable changes

### What it tracks
- New types: object types, interfaces, inputs, enums
- New fields: additions to important types (Mutation, Query, Repository, etc.)
- Significance: prioritizes mutations, queries, and major types

### Output
Features produced from schema diffs include:
- `source_type`: `graphql_schema_diff`
- `product_area`: `API`
- `tags`: `["graphql", "api", "schema-change", ...]`

---

## Output artifacts

All artifacts are stored in `data/` during processing; reports destined for the dashboard should be copied to `docs/` (e.g., `docs/reports/dashboard.json`).

```
data/
├── features.json                    # Ingested features
├── feature_index.json               # Indexed by product area
├── embeddings/
│   └── features_with_embeddings.json
├── reports/
│   ├── coverage.json
│   ├── report.json
│   ├── report.md
│   └── monthly/
│       ├── YYYY-MM_report.json
│       └── YYYY-MM_report.md
├── issues/
│   └── summary.json
├── dashboard/
│   ├── dashboard_latest.json
│   └── dashboard_YYYYMMDD_HHMMSS.json
└── graphql/
    ├── schema-YYYY-MM-DD.graphql
    └── detected_changes.json
```

Dashboard payload (example) placed at `docs/reports/dashboard.json`:

```json
{
  "generated_at": "2025-12-11T12:34:56Z",
  "features": [
    { "name": "Feature A", "status": "complete" },
    { "name": "Feature B", "status": "in-progress" }
  ],
  "gaps": [
    { "name": "Gap X", "impact": "medium" }
  ],
  "notes": "Optional free-form text"
}
```

---

## Troubleshooting

- Seeing “Pages build and deployment” (Jekyll) logs:
  - Ensure Settings → Pages → Source is “GitHub Actions”
  - The Actions-based workflow should show jobs named `build` and `deploy` and use `actions/deploy-pages`

- Workflow fails with “index.html missing”:
  - Ensure `docs/index.html` exists on `main`

- Dashboard shows “dashboard.json not found”:
  - Ensure the path is exactly `docs/reports/dashboard.json`
  - Confirm the deploy workflow ran after the JSON was added
  - Hard-refresh the page (Ctrl+F5 or Cmd+Shift+R)

- Organization policy blocks Actions-based Pages:
  - Ask an org admin to allow Actions-based Pages deployment
  - As a fallback, set Source to “Deploy from a branch” with `docs/.nojekyll` and `docs/index.html`

---

## Contributing

- PRs should target `main`
- For dashboard changes, update `docs/index.html` and include sample data under `docs/reports/`
- For pipeline changes, propose updates under `.github/workflows/` and document the expected outputs in this README
- Configuration changes should be made in `config.yaml` and tested locally before committing

## License

MIT
