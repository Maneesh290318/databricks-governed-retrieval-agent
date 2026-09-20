# Evaluation and Limitations

## Validated behavior

The completed project evaluation documented:
- four simulated access roles;
- 6/6 access-control checks passing;
- no observed cross-role data leaks in the recorded test set;
- successful structured-data tool calls from the deployed Databricks App;
- semantic retrieval testing against a 14-document synthetic corpus.

These are project-test results, not claims of formal security certification.

## Known limitations

### Role picker is simulated identity
The public app allows a visitor to select a role. This is useful for demonstrating role behavior, but it is not authentication. Production use should derive authorization from trusted SSO/group claims.

### Model parameter fabrication
During evaluation, the model twice supplied a plausible tool parameter when a real identifier had not been provided. The tool schema was subsequently strengthened to tell the model not to invent encounter IDs. A production implementation should also validate required identifiers deterministically before tool execution.

### Demo resources can become inactive
The Databricks App and supporting AI Search resources are on-demand demo infrastructure. After periods of non-use, the application or retrieval endpoint may need to be restarted before retrieval-dependent queries work.

### Portfolio-scale evaluation
The access-control and retrieval test sets are intentionally small. Production readiness would require larger adversarial authorization tests, retrieval/grounding metrics, regression evaluation, monitoring, and formal threat modeling.
