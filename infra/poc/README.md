# Isolated remediation POC

This subscription-scope Bicep deployment creates a rollback-friendly POC without changing either existing web app. It creates one resource group containing:

- One Linux B1 App Service plan with one instance.
- Separate checker and remediator container apps.
- One Key Vault containing the shared remediator key.
- One Log Analytics workspace and one Application Insights resource.

The apps use system-assigned managed identities. Both receive `AcrPull` on the existing private registry, and both receive read access to the POC-only Key Vault secret. FTP and SCM basic publishing credentials are disabled. The browser calls only the checker; the checker calls the remediator server-to-server.

The default immutable images are:

- `ada-accessibility-checker:407150b`
- `pdf-ada-remediator:4e699a3`

## External dependency

The checker uses the configured Microsoft Foundry project and agent. That project is not created or modified by this deployment. Grant the checker app's output `checkerPrincipalId` the project role required to list and invoke `ADAAccessibilityCheckerAgent`. Until that grant is made, `/api/health` and remediation can work while new audit requests fail authentication.

## Validation

After deployment, validate:

1. Remediator `GET /health` returns HTTP 200.
2. Checker `GET /api/health` returns HTTP 200.
3. A direct authenticated remediator request returns a PDF.
4. A checker audit returns the 32-rule JSON report after Foundry RBAC is granted.
5. **Perform remediation** downloads a PDF through the checker proxy.

## Rollback

Delete the POC resource group emitted as `resourceGroupName`. This removes both apps, their plan, vault, and telemetry without touching either existing web app. The two image tags and their ACR role assignments can then be removed separately if desired.