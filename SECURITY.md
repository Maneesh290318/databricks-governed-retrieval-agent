# Security

This repository is a portfolio implementation built with public/synthetic project data. Do not use it as-is with protected health information or production credentials.

## Do not commit
- Databricks personal access tokens or OAuth secrets
- service-principal secrets
- private workspace URLs or internal identifiers that are not intended for publication
- real patient/customer records or PHI/PII
- local .env files

The application relies on Databricks application identity and explicit Unity Catalog grants. Production deployments should integrate enterprise identity/SSO, formal secrets management, audit review, and organization-specific security controls.
