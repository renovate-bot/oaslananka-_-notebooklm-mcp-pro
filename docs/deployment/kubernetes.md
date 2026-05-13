# Kubernetes Deployment

Apply the secret first:

```bash
kubectl create secret generic nlm-mcp-secrets \
  --from-literal=auth_mode=token \
  --from-literal=bearer_token=replace-with-generated-token \
  --from-literal=notebooklm_auth_json='{"cookies":[]}'
```

Then apply:

```bash
kubectl apply -f deploy/k8s/deployment.yaml
```

Expose through an ingress with TLS and set `NLM_MCP_BASE_URL` to the public URL.

Production recommendations:

- Use one replica unless session storage is moved to a shared backend.
- Mount secrets from a secret manager.
- Set CPU and memory limits.
- Route only HTTPS traffic to the service.
