## Dashboard (GitHub Pages)

This repository publishes a static dashboard to GitHub Pages.

Steps to enable:
1. Ensure `docs/index.html` exists (provided) and the workflow copies `reports/dashboard.json` to `docs/reports/dashboard.json`.
2. In the repository: Settings → Pages → Source: “Deploy from a branch”, Branch: `main`, Folder: `/docs`.
3. After enabling, access: https://rmallorybpc.github.io/automatic-barnacle

You can also trigger a manual run to generate the initial `reports/dashboard.json` using the “Run pipeline” Action (workflow_dispatch). The workflow will copy the JSON to `docs/reports/dashboard.json` and commit it.