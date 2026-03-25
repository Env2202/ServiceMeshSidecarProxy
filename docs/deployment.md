# Deployment (placeholder)

## POC: Container/Standalone Only

No K8s integration per POC scope.

### Docker
```bash
docker build -t sidecar .
docker run -v ./config.yaml:/config/sidecar-config.yaml sidecar
```

### Standalone
```bash
python -m sidecar --config ./sidecar-config.yaml
```
