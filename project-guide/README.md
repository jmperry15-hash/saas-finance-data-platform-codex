# SaaS Finance Lab — project guide

A buildless HTML/CSS/JavaScript guide with 13 navigation tabs: overview, seven milestones, API practice, data flow, finance definitions, validation/security and downloads. This is separate from the financial dashboard in `dashboard-site/`.

Run locally from the repository root:

```bash
python3 -m http.server 8892 --bind 127.0.0.1 --directory project-guide
```

Open http://127.0.0.1:8892/. No dependencies, credentials or warehouse calls are required.

The infographic is generated with `scripts/build_project_infographic.py` (ReportLab) and rendered to PNG with Poppler. Its final files are also in `output/pdf/`. Screenshot files are JPEGs, matching their byte format.

Sites hosts a separate owner-private copy. Its deployment manifest and Git credentials are excluded from this public repository. A GitHub push alone does not republish the Site. Source changes must be synchronized through the Sites workflow.

Verified project evidence is dated October 28–29, 2026. All financial and person records are synthetic.
