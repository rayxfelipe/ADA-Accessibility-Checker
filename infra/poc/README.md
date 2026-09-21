# Isolated remediation POC

This subscription-scope Bicep deployment creates a rollback-friendly POC without changing either existing web app. It creates one resource group containing:

- One Linux B1 App Service plan with one instance.
- Separate checker and remediator container apps.
- One Key Vault containing the shared remediator key.
- One Log Analytics workspace and one Application Insights resource.
- One VNet with App Service integration and private-endpoint subnets.
- One Key Vault private endpoint and private DNS zone.

The apps use system-assigned managed identities. Both receive `AcrPull` on the existing private registry, and both receive read access to the POC-only Key Vault secret. Key Vault public network access is disabled; App Service resolves the secret through VNet integration and private DNS. FTP and SCM basic publishing credentials are disabled. The browser calls only the checker; the checker calls the remediator server-to-server.

The default immutable images are:

- `ada-accessibility-checker:foundry-v2-agent-v1`
- `pdf-ada-remediator:4e699a3`

## External dependency

The checker uses the customer-owned `ADAAccessibilityCheckerAgent` prompt agent in the configured Microsoft Foundry project. The agent definition is versioned in `foundry/ADAAccessibilityCheckerAgent.json`, while the authoritative 32-rule audit policy remains in `backend/app/config.py:AUDIT_PROMPT`. This deployment does not create or modify the Foundry project or agent. Grant the checker app's managed identity the `Foundry User` role on the Foundry project before enabling audits. `/api/health` and remediation work independently of the audit dependency.

## Validation

After deployment, validate:

1. Remediator `GET /health` returns HTTP 200.
2. Checker `GET /api/health` returns HTTP 200.
3. A direct authenticated remediator request returns a PDF.
4. A checker audit returns the 32-rule JSON report after Foundry RBAC is granted.
5. **Perform remediation** downloads a PDF through the checker proxy.

## Rollback

Delete the POC resource group emitted as `resourceGroupName`. This removes both apps, their plan, network, and telemetry without touching either existing web app. Key Vault purge protection retains the soft-deleted vault for its retention period. The two image tags and their ACR role assignments can then be removed separately if desired.