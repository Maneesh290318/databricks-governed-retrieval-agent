# Architecture

## End-to-end flow

1. A user opens the Databricks App and selects one of four simulated roles: Analyst, Supervisor, Doctor, or Nurse.
2. The Streamlit application attaches the role to the session and exposes only the matching structured-data tool to the model.
3. The model is called through Databricks AI Gateway using an OpenAI-compatible chat-completions interface.
4. For structured questions, the agent calls a role-scoped Unity Catalog SQL function backed by a role-specific Delta view.
5. For policy/procedure questions, the agent calls `search_policy_documents`, which performs semantic retrieval over the AI Search index and filters results by role visibility.
6. Results return to the model and are synthesized into the user-facing answer.

## Governance design

| Role | Structured access |
|---|---|
| Analyst | Operational encounter metrics; no demographics, identifiers, or diagnosis content |
| Supervisor | Pre-aggregated trend data only |
| Doctor | Clinical encounter view including diagnoses/demographics in the simulated dataset |
| Nurse | Medication and monitoring data; no diagnosis codes or demographics |

The Supervisor boundary is structural: the underlying view is aggregated before the agent can query it. Document retrieval also applies role filtering inside the governed SQL function.

## Identity note

The role picker is an application-level simulation for demonstrating authorization behavior. It is not a replacement for enterprise authentication. A production implementation would map authenticated identity/group claims to governed roles rather than allowing a user to self-select a role.
