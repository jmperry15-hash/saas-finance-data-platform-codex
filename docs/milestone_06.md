# Milestone 6: automation

## Lesson 1: run the existing checks on GitHub

**Why:** a project should work on a fresh computer, without depending on your
local data files or Google login. Continuous integration (CI) checks the code
and data rules whenever a workflow runs. We start with a manual button so you
can understand one run before enabling automatic triggers.

**Current status:** code and the workflow are published to the public
[portfolio repository](https://github.com/jmperry15-hash/saas-finance-data-platform-codex), as Jack explicitly chose.
Local `main` tracks `origin/main`. The user's screenshot confirms hosted run #1
passed on commit `618ae46`. The expanded workflow also passed on `614edb6`
on October 28; see Lesson 3 below.
This lesson does not refresh BigQuery or execute dbt against the warehouse.

**Local verification, October 26:** in a temporary copy containing only tracked
project files, generation and saved-file validation passed all 764 controls,
and all 60 Python tests passed. Google credential paths were set to nonexistent
temporary paths. The existing Python 3.13 ingestion environment passed
`pip check`. Workflow YAML was also parsed and its trigger/permissions checked.
That was a local-only checkpoint. Hosted installation and execution have since
passed; the latest receipt is in Lesson 3 below.

Read [the workflow](../.github/workflows/validate.yml). YAML is a configuration
format: indentation groups settings and steps. It is not SQL.

| Workflow setting | Meaning |
| --- | --- |
| `workflow_dispatch` | Show a manual Run workflow button once the file is on GitHub's default branch |
| `runs-on: ubuntu-24.04` | Use a fresh standard Linux runner |
| `contents: read` | The workflow can read repository code |
| `timeout-minutes: 10` | Stop a job that takes too long |
| `uses` | Reuse an action; the full commit IDs pin the reviewed version |
| `run` | Execute a terminal command, just like on your Mac |

The steps install Python 3.13 and the ingestion dependencies, generate all 14
synthetic CSVs, validate their relationships, and run the Python test suite.
Tests include deliberately bad input, broken API pages, and cloud-loader
safeguards. Cloud requests in those tests are mocked; the API tests use a
temporary local server. No Google credentials are needed.

If a command exits with an error, GitHub marks that step and job as failed;
later ordinary steps do not run. A green result means these checks passed.
It does not establish that warehouse data is current or that dbt models pass.

## Repeat the hosted exercise

The first run is complete. To repeat it, use the steps below in your signed-in
GitHub browser. The current lesson is [reproducible portfolio validation](portfolio_validation.md).

This repository is public and the workflow uses a standard Ubuntu runner, so
runner usage is free under [GitHub's billing rules](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
There are no cache or artifact uploads and no schedule. If you later make the
repository private, check its shared included allowance and block paid overages
before running Actions. BigQuery billing remains separate and should stay disabled.

Open **Actions → Validate synthetic finance
data → Run workflow → main → Run workflow**. Open the run to inspect each
step's log. The workflow must be on the default branch for the manual button
to appear. See [GitHub's manual-run instructions](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

**Lesson gate passed:** one successful hosted validation run, evidenced by the
user's screenshot. A deliberately failing run on a practice branch remains an
optional exercise; automated negative tests already cover invalid inputs.

## Lesson 2: the complete manual refresh

[The refresh pipeline](manual_refresh.md) is implemented and its first complete
live run passed on October 28: all 14 raw tables refreshed and verified,
122 dbt steps passed, and the local dashboard rebuilt from 4,047 reconciled
BigQuery rows. Billing remained disabled.

Next, practice the command and inspect its receipt. The newer code is now on
GitHub with passing CI. The updated private dashboard was separately published
and verified on October 29. Continue with [the final walkthrough](final_walkthrough.md). Remote authentication and a schedule are optional extensions after
understanding the manual pipeline.

The previously skipped manual mock-API failure exercise remains optional;
this milestone does not require reopening it.

## Lesson 3: reproducible portfolio validation

[The new lesson](portfolio_validation.md) extends the manual workflow to rebuild
dashboard inputs in a temporary directory and verify the JavaScript calculations.
It does not use cloud credentials or change the published Site. The [hosted run](https://github.com/jmperry15-hash/saas-finance-data-platform-codex/actions/runs/40796000119)
passed on application commit `614edb6`: 764 source controls, 73 Python tests and
186 dashboard comparisons plus coverage/plan assertions. No cloud credentials
were used. Later documentation-only commits record this result; the tested
application commit is identified explicitly.
