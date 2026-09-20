# Governed Retrieval Agent for Correctional Health Operations

A **Databricks-native, role-aware AI assistant** that combines governed structured data with semantic document retrieval and delivers the result through a deployed conversational application.

This project was built to explore a question that matters in enterprise AI: **How do you give an LLM useful tools without allowing the AI layer to bypass the data-access boundaries underneath it?**

**Stack:** Databricks · Delta Lake · Unity Catalog · AI Search / Vector Search · AI Gateway · Llama 3.3 70B Instruct · Streamlit · Python · SQL

## Project Results

| Result | Recorded project evaluation |
|---|---:|
| Simulated access roles | 4 |
| Access-control tests passed | 6 / 6 |
| Observed cross-role leaks in test set | 0 |
| Governed retrieval corpus | 14 synthetic documents |
| Delivery | Deployed Databricks App |

These are portfolio-scale evaluation results, not a formal security certification.

## Problem

Operational and clinical teams often need answers that span both structured records and unstructured policy/procedure documents. A useful AI assistant therefore needs more than retrieval: it needs explicit boundaries around **which data a requester is allowed to retrieve and which tools the model can invoke**.

The project simulates that environment with four roles:

- **Analyst** — operational encounter metrics without demographics, identifiers, or diagnosis content.
- **Supervisor** — pre-aggregated trends only; no row-level encounter retrieval.
- **Doctor** — the project's full clinical encounter view.
- **Nurse** — medication and monitoring data without diagnosis codes or demographics.

## Architecture

```text
                         User
                          |
                          v
              Databricks App / Streamlit
              role: Analyst | Supervisor
                    Doctor | Nurse
                          |
                          v
                    AI Gateway
                          |
                          v
               Llama 3.3 70B Instruct
                  tool-calling loop
                    /           \
                   /             \
                  v               v
        Role-scoped SQL       Governed document
            function              search
                  |               |
                  v               v
          Role-specific       AI Search index
           Delta view       + role_visibility filter
                  \               /
                   \             /
                    v           v
                 Delta Lake + Unity Catalog
                          |
                          v
                    Final answer
```

See `docs/architecture.md` for the design details.

## Why the Governance Design Matters

The role boundary is not only described in the prompt.

For structured data, the application exposes the model only to the SQL function matching the selected role. Those functions query different Unity Catalog views. The Supervisor view is **pre-aggregated structurally**, so the agent cannot turn a Supervisor query into an individual-record lookup simply by changing its prompt.

For unstructured retrieval, `search_policy_documents` searches the semantic index and then filters documents using the requester's role visibility. This prevents document retrieval from becoming a separate path around the role model.

The role is injected by application logic when a tool executes; it is not accepted as a model-generated tool argument.

> **Important:** the role picker in this public portfolio application simulates identity. A production system should map authenticated enterprise identity/SSO claims to governed roles instead of allowing users to self-select a role.

## Agent Behavior

The model receives two tools per session:

1. the structured-data function associated with the active role;
2. `search_policy_documents` for governed semantic retrieval.

For policy/procedure questions, the system instructs the model to retrieve supporting documents rather than answer from general model knowledge.

The tool loop is capped to prevent unbounded agent iterations.

## Repository Structure

```text
databricks-governed-retrieval-agent/
├── app/
│   ├── app.py
│   ├── app.yaml
│   └── requirements.txt
├── sql/
│   └── governed_serving_layer.sql
├── data/
│   └── README.md
├── docs/
│   ├── architecture.md
│   └── evaluation-and-limitations.md
├── .env.example
├── .gitignore
├── SECURITY.md
└── README.md
```

The original Databricks build notebook also created the curated Delta layer, sensitivity metadata, role policy table, knowledge-document table, AI Search index integration, role views, and Unity Catalog functions. The GitHub version keeps the application and governed serving layer concise and removes environment-specific identifiers.

## Deployment

The project was deployed as a Databricks App and validated through the application UI.

**Demo:** https://agents-app-7474658727378126.aws.databricksapps.com

**Availability note:** this is an on-demand portfolio environment. After periods of inactivity, the Databricks App or supporting AI Search endpoint may become inactive and require a restart before all retrieval-dependent features work again. The repository and documented evaluation should therefore be treated as the durable project artifact.

## Example Structured Query

An Analyst test asked for the length of stay and number of lab procedures for a supplied encounter. The deployed application invoked the Analyst-scoped tool and returned the matching operational fields without exposing demographics or diagnosis content.

## Evaluation

The recorded project evaluation included role-access tests, structured tool-use tests, and semantic retrieval checks.

A notable failure mode was also captured: during testing, the model twice generated a plausible tool parameter when an actual identifier was not supplied. The tool description was strengthened to explicitly prohibit invented encounter IDs.

That mitigation is useful, but prompt/schema instructions alone are not a sufficient production control. A stronger implementation would validate identifiers deterministically before execution and add automated regression tests for missing/invalid parameters.

See `docs/evaluation-and-limitations.md` for the complete limitations summary.

## Running the App

Prerequisites:

- a Databricks workspace with the required AI and Unity Catalog capabilities;
- a SQL warehouse;
- the curated tables/views/functions;
- an AI Search index over the knowledge-document table;
- permissions for the Databricks App service principal.

Configure:

```text
DATABRICKS_WAREHOUSE_ID=YOUR_WAREHOUSE_ID
CATALOG_SCHEMA=corrections_health_demo.curated
MODEL_NAME=system.ai.meta-llama-3-3-70b-instruct
```

Then deploy the contents of `app/` as a Databricks App after replacing the warehouse placeholder in `app.yaml`.

## Security

No Databricks token or service-principal secret is stored in the repository. The app uses Databricks SDK authentication supplied by the Databricks Apps runtime.

Do not use real PHI/PII in a public reproduction of this project. See `SECURITY.md`.

## What This Project Demonstrates

- governed AI application design;
- Delta Lake / Unity Catalog data foundations;
- role-scoped SQL serving layers;
- LLM function/tool calling;
- semantic retrieval over governed documents;
- application-controlled tool exposure;
- Databricks AI Gateway integration;
- Streamlit application delivery;
- explicit service-principal permissions;
- evaluation of both successful behavior and failure modes.

## Next Iteration

- Replace simulated role selection with authenticated SSO/group claims.
- Add deterministic argument validation before tool execution.
- Recreate/restart the AI Search endpoint through deployable infrastructure.
- Add MLflow tracing and a larger automated evaluation suite.
- Add adversarial authorization and prompt-injection tests.
- Add CI/CD and infrastructure/deployment automation.
- Add stronger observability for tool calls, retrieval quality, latency, and failures.

## Portfolio Context

The project is intentionally more than a RAG notebook. It demonstrates how **data engineering, governance, retrieval, agent tool use, evaluation, and application delivery** fit together in an enterprise-style Databricks AI system.
