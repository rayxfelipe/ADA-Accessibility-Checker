# Azure Deployment Plan

> **Status:** Validated

Generated: 2026-10-01T22:25:00-07:00

---

## 1. Project Overview

**Goal:** Deploy the customer-feedback fixes in checker commit `7e5903f` and remediator commit `5405c2a` to the existing connected ADA Checker and PDF Remediator POC.

**Path:** Modify existing Azure deployment

**Deployment impact:** Build two immutable container images and update the two existing App Service image references. Preserve the App Service plan, VNet integration, private endpoints, Key Vault references, managed identities, RBAC, Foundry configuration, monitoring, secrets, and public endpoints.

---

## 2. Requirements

| Attribute | Value |
|-----------|-------|
| Classification | POC / staging pilot |
| Scale | Small; two applications on one existing App Service plan |
| Budget | Cost-optimized; retain existing Linux B1 plan |
| Subscription | `rayfelipe-fdpo` (`499bc654-f84c-46c2-952c-b30be508f78c`) - confirmed by user |
| Location | `westus2` - confirmed by user and matches the existing deployment |
| Resource group | `rg-ada-remediation-poc-33f3poc` |
| Checker endpoint | `https://app-ada-checker-poc-33f3poc.azurewebsites.net` |
| Remediator endpoint | `https://app-ada-remediator-poc-33f3poc.azurewebsites.net` |

---

## 3. Components Detected

| Component | Type | Technology | Source |
|-----------|------|------------|--------|
| ADA Accessibility Checker | Frontend and API | FastAPI, static HTML/CSS/JavaScript, Microsoft Foundry | `rayxfelipe/ADA-Accessibility-Checker`, commit `7e5903f` |
| PDF ADA Remediator | API and legacy local workflow | Python 3.12, `pypdf` | `rayxfelipe/PDF-ADA-Remediator`, commit `5405c2a` |
| Checker container | Linux container | `Dockerfile.azure` | Checker repository root |
| Remediator container | Linux container | `Dockerfile.azure` | Remediator repository root |
| Existing infrastructure | Subscription-scoped IaC | Bicep | Checker `infra/poc/` |
| Regression suites | Automated tests | Python `unittest`; browser validation | Both repositories |

---

## 4. Recipe Selection

**Selected:** Azure CLI application-image update

**Rationale:**

- All Azure resources already exist and the two App Services are running.
- The release changes application code and the checker-remediator JSON contract only.
- Re-provisioning the existing Bicep stack would add risk and is unnecessary.
- Azure Container Registry can remotely build both existing Dockerfiles.
- Immutable commit tags provide direct traceability and independent rollback.

**Planned images:**

- `crpdfadastaging33f3.azurecr.io/ada-accessibility-checker:7e5903f`
- `crpdfadastaging33f3.azurecr.io/pdf-ada-remediator:5405c2a`

**Rollback images:**

- Checker: `crpdfadastaging33f3.azurecr.io/ada-accessibility-checker:foundry-v2-agent-v2`  
  Recorded digest: `sha256:01d91b3fedae608ffd3b5d6005af6f12c7faa5d9f0d1a398a501b7fb4f72f852`
- Remediator: `crpdfadastaging33f3.azurecr.io/pdf-ada-remediator:080c5b6`  
  Recorded digest: `sha256:c0e771a643849eb94735768f256ebf8da02e5145233886feb711608be92cc469`

---

## 5. Architecture

**Stack:** Two Linux containers on Azure App Service

### Service Mapping

| Component | Azure Service | SKU |
|-----------|---------------|-----|
| ADA Accessibility Checker | `app-ada-checker-poc-33f3poc` | Existing Linux B1 plan |
| PDF ADA Remediator | `app-ada-remediator-poc-33f3poc` | Existing Linux B1 plan |
| Container images | `crpdfadastaging33f3` | Existing Basic ACR |

### Supporting Services

| Service | Purpose |
|---------|---------|
| Microsoft Foundry | Executes the checker prompt agent |
| Key Vault | Stores the shared remediator API key |
| VNet and private endpoint | Protect server-to-server and Key Vault traffic |
| Managed identities | Pull images and access authorized Azure dependencies |
| Log Analytics and Application Insights | Centralized monitoring and diagnostics |

### Live-state observations

- Both App Services report `Running`.
- The shared App Service plan `asp-ada-poc-33f3poc` reports `Ready`, B1, one instance.
- Checker currently runs `ada-accessibility-checker:foundry-v2-agent-v2`.
- Remediator currently runs `pdf-ada-remediator:080c5b6`.
- No infrastructure, identity, secret, network, or scaling change is planned.

---

## 6. Provisioning Limit Checklist

This release creates no Azure resources and adds no compute instances. The `azure-quotas` workflow was invoked after subscription and region confirmation. Quota usage and fixed monthly cost remain unchanged.

| Resource Type | Number to Deploy | Total After Deployment | Limit/Quota | Notes |
|---------------|------------------|------------------------|-------------|-------|
| New Azure resources | 0 | Existing inventory unchanged | N/A - no quota increment | Application-image update only |
| App Service Plan instances | 0 additional | 1 existing B1 instance | Existing capacity retained | No scale or SKU change |
| ACR registries | 0 additional | 1 existing Basic registry | Existing capacity retained | Two new immutable image tags only |

**Status:** All planned changes are within limits because resource quantities and compute capacity do not increase.

---

## 7. Validation Proof

Preparation evidence collected before Azure validation:

| Check | Result |
|-------|--------|
| Checker automated tests | Pass: 8 tests |
| Checker Python compilation | Pass |
| Checker browser validation | Pass: structured standards, counts, evidence tier, checker version, and rule-level comparison rendered without page errors |
| Audited-file binding | Pass: remediation remained bound to the PDF that produced the displayed report |
| Remediator automated tests | Pass: 19 tests |
| Remediator Python compilation | Pass |
| Contract v2 handoff | Pass: real saved report imported with 32 findings, 14 passes, and standards preserved |
| Git synchronization | Pass: both repositories clean and `0` ahead / `0` behind their tracked origins |

### Prepared image evidence

| Application | ACR run | Immutable image | Digest | Result |
|-------------|---------|-----------------|--------|--------|
| Checker | `ccb` | `ada-accessibility-checker:7e5903f` | `sha256:7e3c3d2056df66a414119f985e057ad45dd97eef2431c228ffaa7b0e88e6994f` | Succeeded |
| Remediator | `ccc` | `pdf-ada-remediator:5405c2a` | `sha256:e9e559566221a57a19f925fb3dc81d1e0896bffdec4f64ed67d38c70b53bcff5` | Succeeded |

### Azure validation evidence

| Check | Command or evidence | Result | Timestamp |
|-------|---------------------|--------|-----------|
| Core deployment validation | `validate-deployment.ps1 -Scope sub -Location westus2 -Template .\infra\poc\main.bicep ...` | Pass: CLI, authentication, Bicep compilation, subscription validation, and what-if | 2026-10-01T22:31:00-07:00 |
| Infrastructure what-if | Validation helper | Pass: completed with 13 creates, 24 modifies, and 12 deletes; confirms this release must remain image-only and must not apply the Bicep drift | 2026-10-01T22:31:00-07:00 |
| Container builds | ACR runs `ccb` and `ccc` | Pass: both immutable images built and published with recorded digests | 2026-10-01T22:29:45-07:00 |
| Azure Policy | `az policy assignment list`; `az policy state summarize` | Pass: three Defender assignments; no non-compliant policy or resource count returned for the planned image-reference update | 2026-10-01T22:32:00-07:00 |
| Static RBAC | Review of `acr-role-assignments.bicep`, `foundry-role-assignment.bicep`, and `resources.bicep` | Pass: least-privilege `AcrPull`, `Key Vault Secrets User`, and checker-only `Foundry User` scopes | 2026-10-01T22:32:00-07:00 |
| Live RBAC | Managed-identity role queries for both App Services | Pass: checker has `AcrPull`, `Key Vault Secrets User`, and `Foundry User`; remediator has `AcrPull` and `Key Vault Secrets User` | 2026-10-01T22:32:00-07:00 |
| Existing configuration | App-setting name and VNet integration queries | Pass: required settings remain present; both apps use `snet-app-integration`; no secret values were retrieved | 2026-10-01T22:33:00-07:00 |
| Prepared image manifests | ACR manifest queries | Pass: tags `7e5903f` and `5405c2a` resolve to the recorded immutable digests | 2026-10-01T22:33:00-07:00 |
| Live images unchanged | `az webapp list` image query | Pass: checker remains on `foundry-v2-agent-v2`; remediator remains on `080c5b6` | 2026-10-01T22:33:00-07:00 |
| Existing health endpoints | HTTPS requests to checker `/api/health` and remediator `/health` | Pass: both returned HTTP 200 | 2026-10-01T22:33:00-07:00 |

---

## 8. Execution Checklist

### Phase 1: Planning

- [x] Analyze both repositories
- [x] Confirm subscription and location with the user
- [x] Inspect existing infrastructure and live image references
- [x] Invoke `azure-quotas` and confirm no quota increment
- [x] Select the image-only Azure CLI recipe
- [x] Define immutable target and rollback images
- [x] User approved image builds and validation only

### Phase 2: Preparation and Validation

- [x] Build checker image `7e5903f` in ACR without changing the live app
- [x] Build remediator image `5405c2a` in ACR without changing the live app
- [x] Record immutable image digests
- [x] All validation checks pass
  - [x] Core validation: Azure CLI, authentication, Bicep build, subscription validation, and what-if
  - [x] Container validation: both ACR builds succeeded and immutable digests are recorded
  - [x] Azure Policy validation
  - [x] Static and live RBAC validation
  - [x] Existing App Service, VNet, Key Vault, Foundry, and image configuration validation
- [x] Verify live identities, `AcrPull`, Key Vault access, VNet integration, and Foundry configuration remain healthy
- [x] Update plan status to `Ready for Validation`
- [x] Run `azure-validate` and record proof
- [ ] Obtain final deployment approval

### Phase 3: Deployment

- [ ] Update the remediator App Service to image `5405c2a`
- [ ] Allow the remediator to warm and verify `/health`
- [ ] Update the checker App Service to image `7e5903f`
- [ ] Allow the checker to warm and verify `/api/health`
- [ ] Run a synthetic checker-to-remediator smoke test
- [ ] Verify standards display, consistent overview counts, contract v2, and remediated recheck comparison
- [ ] Record deployed digests and mark the plan `Deployed`

---

## 9. Deployment and Rollback Procedure

### Deployment order

1. Build both immutable images in `crpdfadastaging33f3`.
2. Deploy the backward-compatible remediator image first.
3. Verify remediator health and API-key enforcement.
4. Deploy the checker image, which emits the version 2 envelope while retaining `remediationReport`.
5. Verify checker health, Foundry audit completion, remediation download, and recheck comparison.

### Rollback

If either application fails its validation:

1. Restore the checker image to `ada-accessibility-checker:foundry-v2-agent-v2`.
2. Restore the remediator image to `pdf-ada-remediator:080c5b6`.
3. Restart only the affected App Service.
4. Verify health and the existing checker-to-remediator path.

Rollback changes only container image references. It does not delete or modify resources, identities, secrets, networking, monitoring, or customer data.

---

## 10. Approval Boundary

Plan approval authorizes image builds and the `azure-validate` workflow. It does not authorize switching the two live App Services. A second explicit approval is required after validation proof and image digests are available.
