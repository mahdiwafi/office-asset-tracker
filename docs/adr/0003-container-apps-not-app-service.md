# ADR 0003 — Host on Azure Container Apps, not App Service

## Status

Accepted (deviation from ADR 0001, hosting line)

## Context

ADR 0001 chose Azure App Service as the hosting target. Provisioning on the free-trial subscription failed twice with the same error:

```
Operation cannot be completed without additional quota.
Current Limit (Total VMs): 0
Amount required for this deployment (Total VMs): 1
```

Investigation (via `az vm list-usage` and `az containerapp list-usages`) showed the failing quota is **"Total VMs" under the `Microsoft.Web` resource provider** — a different bucket from `Microsoft.Compute`, which has 4 regional vCPUs and 25,000 VMs available. Free-trial subscriptions are hard-set to 0 on the App Service quota in every region, and Microsoft does not permit quota adjustments on free trials ("Free trials are not eligible for quota adjustment. Upgrade your subscription first."). The candidate is not a student (no Azure for Students) and chose not to upgrade to Pay-As-You-Go (no card on file).

The same subscription does expose Container Apps capacity: `ManagedEnvironmentCount` limit 1, `SessionPools` limit 1 — an environment is available in Canada Central, the same region as the Postgres server (same-region rule preserved, no cross-region egress).

## Decision

Host the backend on **Azure Container Apps** (consumption plan, public HTTPS ingress, scale-to-zero) instead of App Service.

- The runtime is frozen in a committed `Dockerfile` (`python:3.12-slim`, dependencies installed from the committed `requirements.txt` — the same `uv export --no-dev` artifact Oryx would have consumed).
- Migrations and the idempotent demo seed run at **container boot**, mirroring the App Service startup-command pattern. The build never touches the database.
- Images are built in GitHub Actions, pushed to the **public GitHub Container Registry** (no pull credentials needed on the Azure side), and deployed with `azure/container-apps-deploy-action`.
- Secrets stay out of the image: `DATABASE_URL` and the Entra settings arrive as container-app environment variables, exactly where the App Service application settings would have been.

## Consequences

- **No perpetual free tier.** App Service F1 is free forever; Container Apps bills per-second compute and is only cheap *because scale-to-zero means it sleeps*. The $200 credit is the deployment's expiry clock; when it runs out the subscription disables. Revisit App Service if a paid subscription ever appears — the image is hosting-agnostic.
- **"Scale to two instances" (Day 5) becomes `minReplicas` / scale rules** — an autoscaling demo, which is the better interview story.
- The frontend will be containerized the same way later (`next.config.ts` already outputs `standalone`).
- Application Insights wiring (Day 5) is unchanged in shape: the monitoring agent attaches to the container app.
