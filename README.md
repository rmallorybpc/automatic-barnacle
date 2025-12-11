# automatic-barnacle

GitHub Learn content review and feature monitoring system.

<!-- Read me update -->

## Overview

This repository implements an automated monitoring stack for tracking GitHub product updates, features, and API changes. It ingests data from multiple sources, generates analytics, creates GitHub issues for feature gaps, and sends notifications to team channels.

## Features

- **Multi-source ingestion**: Fetches updates from GitHub changelog, roadmap, and GraphQL schema changes
- **GraphQL schema diff**: Tracks API changes by comparing schema snapshots
- **Embeddings generation**: Creates semantic embeddings for feature similarity analysis
- **Coverage evaluation**: Measures feature coverage across product areas
- **Automated reporting**: Generates JSON and Markdown reports
- **Issue management**: Creates and tracks GitHub issues for feature gaps
- **Dashboard generation**: Produces time-series and breakdown visualizations
- **Notifications**: Sends updates to Slack and Microsoft Teams
- **Monthly reports**: Generates comprehensive monthly summaries

## Architecture

### Components

1. **Ingestion** (`src/feature_monitor/ingestion.py`)
   - Fetches GitHub changelog entries
   - Pulls roadmap items from github/roadmap
   - Integrates GraphQL schema changes
   - Outputs: `data/features.json`

2. **GraphQL Schema Diff** (`src/feature_monitor/graphql_diff.py`)
   - Downloads current GraphQL schema
   - Compares with previous snapshot
   - Detects new types, fields, and mutations
   - Saves snapshots: `data/graphql/schema-YYYY-MM-DD.graphql`

3. **Module Indexing** (`src/feature_monitor/modules_index.py`)
   - Indexes features by product area
   - Outputs: `data/feature_index.json`

4. **Embeddings** (`src/feature_monitor/embeddings.py`)
   - Generates vector embeddings for features
   - Outputs: `data/embeddings/features_with_embeddings.json`

5. **Coverage** (`src/feature_monitor/coverage.py`)
   - Evaluates feature coverage metrics
   - Checks against thresholds
   - Outputs: `data/reports/coverage.json`

6. **Report** (`src/feature_monitor/report.py`)
   - Generates JSON and Markdown reports
   - Outputs: `data/reports/report.{json,md}`

7. **Issues** (`src/feature_monitor/issues.py`)
   - Creates GitHub issues for feature gaps
   - Tracks issue creation
   - Outputs: `data/issues/summary.json`

8. **Dashboard** (`src/feature_monitor/dashboard.py`)
   - Generates dashboard data for visualization
   - Time-series and breakdown analytics
   - Outputs: `data/dashboard/dashboard_latest.json`

9. **Notifications** (`src/feature_monitor/notifications.py`)
   - Sends updates to Slack via webhook
   - Sends updates to Teams via webhook

10. **Monthly Report** (`src/feature_monitor/monthly_report.py`)
    - Generates monthly summary reports
    - Outputs: `data/reports/monthly/YYYY-MM_report.{json,md}`

### Logging and Error Handling

All modules include:
- **Structured logging**: INFO and ERROR levels with timestamps and context
- **Retry logic**: Network calls use exponential backoff (3 retries by default)
- **Data validation**: Checks for missing files with actionable error messages
- **Safe file writing**: Atomic writes prevent artifact corruption
- **Exit codes**: Non-zero exit on critical failures for CI visibility

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

### Environment Variables

- `SLACK_WEBHOOK_URL`: Slack incoming webhook URL (optional)
- `TEAMS_WEBHOOK_URL`: Microsoft Teams webhook URL (optional)
- `GITHUB_TOKEN`: GitHub API token (provided by Actions)

## Workflows

### 1. Run Now (Manual Trigger)

**File**: `.github/workflows/run-now.yml`

Runs the complete monitoring pipeline on demand via `workflow_dispatch`.

**Usage**:
1. Go to Actions → Run Now
2. Click "Run workflow"
3. Optional: Skip notifications

**Pipeline steps**:
1. Ingest features from all sources
2. Index by product area
3. Generate embeddings
4. Evaluate coverage
5. Generate report
6. Create/update issues
7. Generate dashboard
8. Send notifications

### 2. Feature Gap Monitoring (Scheduled)

**File**: `.github/workflows/feature-gap.yml`

Runs daily at 9 AM UTC to monitor for new features and gaps.

### 3. Monthly Issues Report (Scheduled)

**File**: `.github/workflows/monthly-issues-report.yml`

Runs on the 1st of each month to generate monthly summary reports.

## Local Development

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

### Running Modules

Each module can be run independently:

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

## GraphQL Schema Diff

The GraphQL schema diff feature tracks changes to the GitHub GraphQL API:

### How It Works

1. **Fetch**: Downloads the current schema from GitHub docs
2. **Store**: Saves snapshot as `data/graphql/schema-YYYY-MM-DD.graphql`
3. **Compare**: Diffs against the previous snapshot
4. **Detect**: Identifies new types, fields, and mutations
5. **Emit**: Creates Feature objects for notable changes

### What It Tracks

- **New types**: Object types, interfaces, inputs, enums
- **New fields**: Fields added to important types (Mutation, Query, Repository, etc.)
- **Significance**: Prioritizes mutations, queries, and major types

### Output

Features from GraphQL diffs have:
- `source_type`: "graphql_schema_diff"
- `product_area`: "API"
- `tags`: ["graphql", "api", "schema-change", ...]

## Output Artifacts

All artifacts are stored in the `data/` directory:

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

## Error Handling

The system implements robust error handling:

1. **Network Failures**: Retries with exponential backoff
2. **Missing Files**: Clear error messages with required actions
3. **Partial Failures**: Continues pipeline, logs errors, reports status
4. **Data Corruption**: Atomic writes prevent partial updates
5. **CI Integration**: Non-zero exit codes on critical failures

## Contributing

This is an automated monitoring system. Configuration changes should be made in `config.yaml` and tested locally before committing.

## License

MIT
