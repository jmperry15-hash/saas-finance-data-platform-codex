# Juniper Cloud dashboard

Private Site: [Juniper Cloud Finance](https://juniper-finance-jack-2026.jmperry41.chatgpt.site). Published October 27, 2026; requires the owner’s ChatGPT sign-in.

The Data + Sites dashboard is implemented in `dashboard-site/`. As of October 28,
the local version uses a snapshot exported from BigQuery after a complete manual
refresh, independently reconciled against SQLite calculations from frozen CSVs.
The browser reads that saved export, not live warehouse queries. See the
[manual refresh lesson](manual_refresh.md). The private hosted version still uses
the earlier October 27 SQLite-derived snapshot until it is republished.

## Coverage and use

- **Financial performance:** January–December 2025 by default; P&L, BUD2025 comparison, monthly revenue/expenses, department expenses, favorable account variance and account-to-month/department detail.
- **ARR & bookings:** October 2025–September 2026 by default; ending ARR/customers, period recognized revenue/bookings, new/renewal bookings, segment composition, customer portfolio and signed-contract detail.
- **Workforce:** October 2025–September 2026 by default; ending headcount/FTE, period personnel costs, weighted cost per FTE-month, trends and departmental composition.

The From/Through controls select complete calendar months. Each tab retains its own filters. Comparisons use BUD2025 for financial selections wholly within 2025; otherwise the immediately preceding equal number of calendar months, requiring complete coverage. There is no substituted 2026 budget. ARR, active customers, headcount and FTE are ending balances. Flow measures sum over the selected period. A zero denominator yields an unavailable ratio. Positive favorable variance means higher revenue or lower expense. Operating profit includes all expense accounts; it is not EBITDA. All records are fictional.

## Reproduce

For a fresh clone, follow [the portfolio validation lesson](portfolio_validation.md)
to regenerate inputs and check calculations without credentials. The commands
below describe the existing local installation.

### Open the local dashboard

Use [the local preview](http://127.0.0.1:60033/). On October 28, the supported
Data preview service was started successfully and the KPI cards/charts were
visually verified. It runs on loopback and restarts at user login. This replaces
the temporary port-8765 server. Serving the publication folder with Python's
generic HTTP server fails because it does not provide the app's presentation
service. The preview repair did not change the reviewed data or published site.

To restart the supported preview if needed:

```sh
/Users/jackperry/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node /Users/jackperry/.codex/plugins/cache/openai-curated-remote/data-analytics/1.1.0-exp-homepage/scripts/data-app-preview.mjs start --project-dir /Users/jackperry/Documents/Codex/saas-finance-data-platform/dashboard-site
```

For the current warehouse-backed refresh, run from the project root:

```sh
.venv-dbt/bin/python scripts/refresh_project.py --run
```

The original standalone SQLite builder remains available for local-only practice:

```sh
.venv/bin/python scripts/build_dashboard_snapshot.py dashboard-site/src/data.json
node tests/test_dashboard_model.mjs
```

The snapshot builder preserves the existing artifact ID, reads source files/database without modifying them, and records source hashes and validation in `work/dashboard-evidence/validation.json`. It sets authoring status to creating; after review, set `buildStatus` to complete and build using the Data plugin command in `dashboard-site/AGENTS.md`. Keep the same Site ID in `.openai/hosting.json` when republishing through Data's publication workflow.

## Validation

764 original source checks passed. Every SQLite field matches its CSV source. All 24 monthly revenue totals reconcile to customer MRR, and all 144 department-month personnel costs reconcile to the GL. The dashboard model passes 186 numeric reconciliations plus plan-coverage and boundary assertions, including independent pre-existing P&L expectations, endpoint balances, missing prior periods, and mixed-year budget unavailability.

Browser review covered all three tabs, rendered charts and detail tables, department selection and return to All, whole-month period changes, account drilldown, source inspection, and responsive layouts. The initial October 27 preview used a temporary server after a service error. On October 28, the supported persistent preview was repaired and verified as described above.

The October 28 manual pipeline refreshes BigQuery and exports a tested local
dashboard. Scheduled refresh, remote execution, forecast selection, retention/ARR
bridges and headcount-plan comparisons remain outside this version.

## Publication receipt

Version 1 deployed successfully with source commit `d56f26f01c19ee0159b37534cdb92a802634c4d1`. All 4 queries / 4,047 rows and the compiled HTML passed full hosted SHA-256/byte-count readback. Access is owner-only (one allowed user, no groups). The normal in-app browser reached the ChatGPT sign-in/security gate; owner editing in a signed-in browser is not yet verified. The deployed snapshot was extracted October 27, 2026 at 10:05 AM Denver time.

## Light theme revision

Version 2 (October 27, 2026) uses a fixed light original theme with white cards, pale gray backgrounds, dark text and muted blue/gray/charcoal chart series. Green/red remain reserved for favorable/unfavorable changes and the variance chart; ambiguous workforce changes remain neutral. Only theme tokens and chart color mappings changed. Snapshot and model SHA-256 fingerprints are unchanged. All three tabs were visually reviewed at the current narrow browser width, with no page overflow or console errors. Hosted asset readback verified all 4,047 rows. Source commit: `aa40b13f3502e54f37ad0eabe9c5d210e1942b13`.
