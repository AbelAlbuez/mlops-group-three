# GitHub Actions Workflows

Este directorio contiene los workflows de CI/CD para el proyecto MLOps de predicción de readmisión de pacientes diabéticos.

## 📋 Workflows Disponibles

### 1. CI/CD Pipeline (`ci-cd.yml`)

**Trigger:** Push a `main` o Pull Request

**Jobs:**

- **Lint & Code Quality**: Valida el código Python con `black`, `flake8`, y `pylint`
- **Build & Push Docker Images**: Construye y publica imágenes Docker en paralelo usando matrix strategy
- **Security Scan**: Escanea imágenes con Trivy para vulnerabilidades
- **Test API**: Ejecuta tests básicos de la API
- **Notify Status**: Notifica el estado final del pipeline

**Características:**

- ✅ Build paralelo de imágenes (matrix strategy)
- ✅ Cache de layers de Docker para builds más rápidos
- ✅ Path filters para optimizar ejecuciones (solo build si cambian archivos relevantes)
- ✅ Escaneo de seguridad con Trivy
- ✅ Validación de estructura de código

**Imágenes construidas:**

- `aalbuez/mlops-prediction-api:latest`
- `aalbuez/mlops-prediction-ui:latest`
- `aalbuez/mlops-prediction-loadtest:latest`
- `aalbuez/mlops-prediction-pipeline:latest`

### 2. Release Workflow (`release.yml`)

**Trigger:** Push de tag `v*.*.*` (ejemplo: `v1.0.0`)

**Jobs:**

- **Build Release Images**: Construye todas las imágenes con tags de versión
- **Create GitHub Release**: Genera changelog automático y crea release en GitHub
- **Update Kubernetes Manifests**: (Opcional) Actualiza manifiestos de K8s para Argo CD

**Tags generados:**

Para cada imagen se crean 3 tags:
- `latest`
- `{version}` (ej: `1.0.0`)
- `{tag}` (ej: `v1.0.0`)

**Ejemplo:**

```bash
# Al hacer push de tag v1.0.0, se crean:
aalbuez/mlops-prediction-api:latest
aalbuez/mlops-prediction-api:1.0.0
aalbuez/mlops-prediction-api:v1.0.0
```

## 🔐 Configuración de Secrets

Para que los workflows funcionen correctamente, necesitas configurar los siguientes secrets en GitHub:

### Pasos para configurar secrets:

1. Ve a tu repositorio en GitHub
2. Click en **Settings** → **Secrets and variables** → **Actions**
3. Click en **New repository secret**
4. Agrega los siguientes secrets:

| Secret Name | Descripción | Ejemplo |
|------------|-------------|---------|
| `DOCKERHUB_USERNAME` | Tu usuario de DockerHub | `aalbuez` |
| `DOCKERHUB_TOKEN` | Token de acceso de DockerHub | `dckr_pat_...` |

### Cómo obtener el token de DockerHub:

1. Ve a [DockerHub](https://hub.docker.com/)
2. Click en tu perfil → **Account Settings**
3. Ve a **Security** → **New Access Token**
4. Dale un nombre (ej: `github-actions`)
5. Copia el token generado (solo se muestra una vez)
6. Pégalo en el secret `DOCKERHUB_TOKEN` de GitHub

## 🚀 Uso

### Primer Push

Para activar los workflows por primera vez:

```bash
# 1. Asegúrate de estar en la rama main
git checkout main

# 2. Haz un commit (si hay cambios)
git add .
git commit -m "chore: add GitHub Actions workflows"

# 3. Push a GitHub
git push origin main
```

Los workflows se ejecutarán automáticamente. Puedes ver el progreso en la pestaña **Actions** de tu repositorio.

### Hacer un Release

Para crear una nueva versión:

```bash
# 1. Crea un tag de versión
git tag -a v1.0.0 -m "Release version 1.0.0"

# 2. Push el tag
git push origin v1.0.0
```

Esto activará el workflow de release que:
- Construirá todas las imágenes con el tag de versión
- Las publicará en DockerHub
- Creará un GitHub Release con changelog automático

### Verificar Builds

1. Ve a la pestaña **Actions** en GitHub
2. Selecciona el workflow que quieres ver
3. Click en el run específico para ver logs detallados

## 📊 Badges para README

Puedes agregar estos badges a tu README principal:

```markdown
![CI/CD Pipeline](https://github.com/TU_USUARIO/TU_REPO/workflows/CI/CD%20Pipeline/badge.svg)
![Release](https://github.com/TU_USUARIO/TU_REPO/workflows/Release%20Workflow/badge.svg)
```

O usando shields.io:

```markdown
![GitHub Actions](https://img.shields.io/github/actions/workflow/status/TU_USUARIO/TU_REPO/ci-cd.yml?branch=main&label=CI/CD)
![Docker](https://img.shields.io/docker/pulls/aalbuez/mlops-prediction-api?label=API%20Pulls)
```

## 🔧 Optimizaciones Implementadas

### 1. Path Filters
Los workflows solo se ejecutan si cambian archivos relevantes:
- `api/**`
- `streamlit/**`
- `locust/**`
- `airflow/**`
- `.github/workflows/**`
- `docker-compose*.yml`

### 2. Docker Layer Caching
Usamos cache de registry para acelerar builds:
- Cache key: `{image}:buildcache`
- Modo: `max` (cachea todas las layers)

### 3. Matrix Strategy
Builds paralelos de todas las imágenes usando matrix strategy para reducir tiempo total.

### 4. Fail-Fast Deshabilitado
`fail-fast: false` permite que todas las imágenes se construyan incluso si una falla, facilitando debugging.

## 🐛 Troubleshooting

### Error: "Docker login failed"

**Causa:** Token de DockerHub inválido o expirado.

**Solución:**
1. Verifica que el secret `DOCKERHUB_TOKEN` esté configurado correctamente
2. Genera un nuevo token en DockerHub
3. Actualiza el secret en GitHub

### Error: "Image push failed"

**Causa:** Permisos insuficientes o imagen ya existe.

**Solución:**
1. Verifica que el usuario de DockerHub tenga permisos de push
2. Asegúrate de que el nombre de la imagen sea único
3. Revisa los logs del workflow para más detalles

### Workflow no se ejecuta

**Causa:** Path filters muy restrictivos o trigger incorrecto.

**Solución:**
1. Verifica que los archivos cambiados estén en los paths filtrados
2. Revisa la configuración de `on:` en el workflow
3. Puedes ejecutar manualmente desde la pestaña Actions

### Build muy lento

**Causa:** Cache no está funcionando o primera ejecución.

**Solución:**
1. El primer build siempre será más lento (sin cache)
2. Verifica que el cache esté configurado correctamente
3. Los builds subsecuentes deberían ser más rápidos

## 📚 Recursos Adicionales

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Buildx](https://docs.docker.com/buildx/)
- [Trivy Security Scanner](https://github.com/aquasecurity/trivy)
- [DockerHub Documentation](https://docs.docker.com/docker-hub/)

## 🤝 Contribuciones

Si necesitas modificar los workflows:

1. Edita los archivos `.yml` en `.github/workflows/`
2. Haz commit y push
3. Los cambios se aplicarán en el próximo run

**Nota:** Los workflows usan versiones específicas de actions para garantizar estabilidad. Actualiza con cuidado.

## 📝 Notas Importantes

- ⚠️ **No construyas imágenes en la máquina de despliegue**: Los workflows se encargan de esto
- ✅ **Las imágenes están en DockerHub**: Puedes consumirlas directamente en Kubernetes
- 🔒 **Secrets son sensibles**: Nunca los expongas en logs o código
- 🚀 **Releases son inmutables**: Una vez creado un tag, no lo modifiques

---

**Última actualización:** Noviembre 2025

