# Badges para README

Copia y pega estos badges en tu README principal para mostrar el estado de los workflows.

## Badges de GitHub Actions

```markdown
![CI/CD Pipeline](https://github.com/aalbuez/mlops-group-three/workflows/CI/CD%20Pipeline/badge.svg?branch=main)
![Release](https://github.com/aalbuez/mlops-group-three/workflows/Release%20Workflow/badge.svg)
```

**Nota:** Reemplaza `aalbuez/mlops-group-three` con tu usuario y repositorio reales.

## Badges con Shields.io (Más personalizables)

```markdown
![GitHub Actions CI/CD](https://img.shields.io/github/actions/workflow/status/aalbuez/mlops-group-three/ci-cd.yml?branch=main&label=CI/CD&logo=github)
![GitHub Actions Release](https://img.shields.io/github/actions/workflow/status/aalbuez/mlops-group-three/release.yml?label=Release&logo=github)
```

## Badges de Docker Hub

```markdown
![Docker Pulls - API](https://img.shields.io/docker/pulls/aalbuez/mlops-prediction-api?label=API%20Pulls&logo=docker)
![Docker Pulls - UI](https://img.shields.io/docker/pulls/aalbuez/mlops-prediction-ui?label=UI%20Pulls&logo=docker)
![Docker Pulls - Loadtest](https://img.shields.io/docker/pulls/aalbuez/mlops-prediction-loadtest?label=Loadtest%20Pulls&logo=docker)
![Docker Pulls - Pipeline](https://img.shields.io/docker/pulls/aalbuez/mlops-prediction-pipeline?label=Pipeline%20Pulls&logo=docker)
```

## Badge de Versión

```markdown
![Latest Version](https://img.shields.io/github/v/tag/aalbuez/mlops-group-three?label=Latest%20Version&logo=github)
```

## Ejemplo Completo para README

```markdown
# Proyecto MLOps - Predicción de Readmisión de Pacientes Diabéticos

[![CI/CD Pipeline](https://github.com/aalbuez/mlops-group-three/workflows/CI/CD%20Pipeline/badge.svg?branch=main)](https://github.com/aalbuez/mlops-group-three/actions)
[![Release](https://github.com/aalbuez/mlops-group-three/workflows/Release%20Workflow/badge.svg)](https://github.com/aalbuez/mlops-group-three/actions)
[![Latest Version](https://img.shields.io/github/v/tag/aalbuez/mlops-group-three?label=Latest%20Version)](https://github.com/aalbuez/mlops-group-three/releases)

[![Docker Pulls - API](https://img.shields.io/docker/pulls/aalbuez/mlops-prediction-api?label=API)](https://hub.docker.com/r/aalbuez/mlops-prediction-api)
[![Docker Pulls - UI](https://img.shields.io/docker/pulls/aalbuez/mlops-prediction-ui?label=UI)](https://hub.docker.com/r/aalbuez/mlops-prediction-ui)
[![Docker Pulls - Loadtest](https://img.shields.io/docker/pulls/aalbuez/mlops-prediction-loadtest?label=Loadtest)](https://hub.docker.com/r/aalbuez/mlops-prediction-loadtest)
[![Docker Pulls - Pipeline](https://img.shields.io/docker/pulls/aalbuez/mlops-prediction-pipeline?label=Pipeline)](https://hub.docker.com/r/aalbuez/mlops-prediction-pipeline)
```

## Personalización

Para personalizar los badges:

1. **Cambiar colores**: Agrega `&color=blue` o `&color=green` a la URL
2. **Cambiar estilo**: Agrega `&style=flat-square` o `&style=for-the-badge`
3. **Agregar logo**: Agrega `&logo=python` o `&logo=docker`

Ejemplo:
```markdown
![CI/CD](https://img.shields.io/github/actions/workflow/status/USER/REPO/ci-cd.yml?branch=main&label=CI/CD&logo=github&color=green&style=flat-square)
```

