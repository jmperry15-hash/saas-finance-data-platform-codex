# Interactive project guide

Published October 29, 2026:
https://saas-finance-project-guide.jmperry41.chatgpt.site

This new Site is owner-private and separate from the financial dashboard.
Sign in with the owner ChatGPT account. No warehouse connection or credentials
are bundled in the website.

## Contents

- Overview and screenshots of the three dashboard views.
- Seven milestone chapters: synthetic sources, relational SQL, BigQuery,
  Python ingestion, dbt, GitHub/automation and the dashboard.
- Separate tabs for API practice, data flow, finance definitions, validation
  and security, and downloadable resources.
- Seven knowledge checks, code excerpts, source links and expandable images.
- Downloadable one-page vector PDF and 2,800-pixel PNG data-flow infographic.

The website is explanatory. It does not execute the example commands, connect
to BigQuery, change the original dashboard, or add scheduled refreshes.

## Source and artifacts

- Public source copy: `project-guide/` (buildless HTML, CSS and JavaScript).
- Sites checkout: `work/finance-project-guide/` (ignored by the portfolio repo).
- Infographic generator: `scripts/build_project_infographic.py` (ReportLab).
- Deliverables: `output/pdf/saas_finance_data_flow.pdf` and `.png`.

The new infographic reflects the implemented October 29 architecture. Older
October 26 lineage artifacts remain available as historical snapshots.

## Verification

Local browser checks covered all 13 navigation destinations, a correct-answer
knowledge check, screenshot loading, infographic expansion, desktop layout and
a 390-pixel mobile viewport. No browser console errors were observed. All 30
repository paths used in the lesson content were checked locally.

The PDF was rendered and visually inspected, and its single page and key labels
were checked with pypdf. Its download copy matches the final local deliverable.

Sites confirmed successful private deployment of source commit
`93352e6ac7f17dcec52773af7da25defc9b9313a` as version 1.
The live URL requires owner sign-in; local rendering checks are distinct from
the deployment confirmation.
