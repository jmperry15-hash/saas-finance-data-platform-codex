# Milestone 6: automation

## Lesson 1: run the existing checks on GitHub

**Why:** a project should work on a fresh computer, without depending on your
local data files or Google login. Continuous integration (CI) checks the code
and data rules whenever a workflow runs. We start with a manual button so you
can understand one run before enabling automatic triggers.

**Current status:** the workflow is prepared locally. GitHub execution remains
pending; this checkout has no GitHub remote configured. This lesson does not
refresh BigQuery or execute dbt against the warehouse.

**Local verification, October 26:** in a temporary copy containing only tracked
project files, generation and saved-file validation passed all 764 controls,
and all 60 Python tests passed. Google credential paths were set to nonexistent
temporary paths. The existing Python 3.13 ingestion environment passed
`pip check`. Workflow YAML was also parsed and its trigger/permissions checked.
This verifies the commands locally; installation and execution on GitHub's
Linux runner remain pending.

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

## Your next action

1. In GitHub, create an **empty private** repository named
   `saas-finance-data-platform`. Leave README, license and `.gitignore`
   initialization unchecked because those files already exist locally.
2. Copy the repository URL and share that URL in this chat. If you already
   created a repository, share its URL instead. No password or token is needed
   in chat.

We will then connect the local repository, review the tracked files, and push
the code. Pushing alone will not start this manually triggered workflow.

Before the first hosted run, check your GitHub account's Actions usage and
spending controls. Private repositories draw from a shared included allowance;
overages can be billable. Keep paid overages blocked and use only the included
allowance. If it is unavailable, continue running the checks locally. This
workflow uses a standard runner, no cache or artifact uploads, and no schedule.
See [GitHub's Actions billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

Once those checks are complete, open **Actions → Validate synthetic finance
data → Run workflow → main → Run workflow**. Open the run to inspect each
step's log. The workflow must be on the default branch for the manual button
to appear. See [GitHub's manual-run instructions](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

**Lesson gate:** one successful hosted run with source validation and all
Python tests passing. Then we can demonstrate a deliberately failing run on
a practice branch and fix it. Both hosted exercises are still pending.

## What follows

1. Build a repeatable refresh command for all required raw sources. The
   existing local Python loader refreshes only the GL; the initial bulk upload
   is a separate utility.
2. Run the dbt reporting models and tests after a successful refresh, with the
   existing billing, location, expiration and query-size safeguards.
3. Decide how to run that refresh remotely with short-lived authentication,
   subject to free-tier support. Do not commit service-account key files.
4. Verify one complete manual refresh before considering a schedule.

The previously skipped manual mock-API failure exercise remains optional;
this milestone does not require reopening it.
