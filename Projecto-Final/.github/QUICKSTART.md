# 🚀 Quick Start - GitHub Actions

Guía rápida para configurar y usar los workflows de GitHub Actions.

## ⚡ Configuración Inicial (5 minutos)

### Paso 1: Configurar Secrets en GitHub

1. Ve a tu repositorio en GitHub
2. Click en **Settings** → **Secrets and variables** → **Actions**
3. Click en **New repository secret**

Agrega estos dos secrets:

| Secret | Valor | Cómo obtenerlo |
|--------|-------|----------------|
| `DOCKERHUB_USERNAME` | Tu usuario de DockerHub | Tu nombre de usuario en DockerHub |
| `DOCKERHUB_TOKEN` | Token de acceso | DockerHub → Account Settings → Security → New Access Token |

**⚠️ Importante:** El token solo se muestra una vez. Guárdalo de forma segura.

### Paso 2: Hacer el Primer Push

```bash
# 1. Asegúrate de estar en la rama main
git checkout main

# 2. Agrega los archivos de workflows
git add .github/

# 3. Commit
git commit -m "ci: add GitHub Actions workflows for CI/CD"

# 4. Push
git push origin main
```

### Paso 3: Verificar que Funciona

1. Ve a la pestaña **Actions** en GitHub
2. Deberías ver el workflow "CI/CD Pipeline" ejecutándose
3. Espera a que termine (5-10 minutos la primera vez)
4. Verifica que las imágenes se hayan publicado en DockerHub

## 📦 Hacer un Release

```bash
# 1. Asegúrate de estar en main y actualizado
git checkout main
git pull origin main

# 2. Crea un tag de versión (semantic versioning)
git tag -a v1.0.0 -m "Release version 1.0.0"

# 3. Push el tag
git push origin v1.0.0
```

Esto activará automáticamente:
- ✅ Build de todas las imágenes con el tag de versión
- ✅ Push a DockerHub con tags: `latest`, `1.0.0`, `v1.0.0`
- ✅ Creación de GitHub Release con changelog

## 🔍 Verificar Imágenes en DockerHub

```bash
# Verificar que las imágenes existen
docker pull aalbuez/mlops-prediction-api:latest
docker pull aalbuez/mlops-prediction-ui:latest
docker pull aalbuez/mlops-prediction-loadtest:latest
docker pull aalbuez/mlops-prediction-pipeline:latest
```

## 🐛 Troubleshooting Rápido

### El workflow no se ejecuta

**Causa:** Path filters muy restrictivos

**Solución:** 
- Los workflows solo se ejecutan si cambian archivos en `api/`, `streamlit/`, `locust/`, `airflow/`
- Si cambias solo documentación, el workflow no se ejecutará
- Puedes ejecutar manualmente desde Actions → Run workflow

### Error de autenticación con DockerHub

**Causa:** Token inválido o expirado

**Solución:**
1. Genera un nuevo token en DockerHub
2. Actualiza el secret `DOCKERHUB_TOKEN` en GitHub
3. Re-ejecuta el workflow

### Build falla

**Causa:** Error en Dockerfile o dependencias

**Solución:**
1. Revisa los logs del workflow en GitHub Actions
2. Prueba construir localmente: `docker build -t test ./api`
3. Corrige el error y haz push nuevamente

### Las imágenes no aparecen en DockerHub

**Causa:** El push solo ocurre en push a `main`, no en PRs

**Solución:**
- Los PRs solo construyen las imágenes (no las publican)
- Haz merge del PR a `main` para que se publiquen

## 📊 Monitoreo

### Ver Estado de Workflows

```bash
# Ver workflows recientes
gh workflow list

# Ver runs de un workflow específico
gh run list --workflow=ci-cd.yml

# Ver logs de un run
gh run view <run-id> --log
```

### Ver Imágenes en DockerHub

Visita: https://hub.docker.com/r/aalbuez/

## 🎯 Próximos Pasos

1. ✅ Configurar secrets
2. ✅ Hacer primer push
3. ✅ Verificar que funciona
4. ✅ Hacer un release de prueba
5. ✅ Integrar con Argo CD (opcional)
6. ✅ Agregar badges al README

## 📚 Documentación Completa

Para más detalles, consulta:
- [README.md](workflows/README.md) - Documentación completa de workflows
- [BADGES.md](BADGES.md) - Badges para README

## 💡 Tips

- **Cache de Docker:** El primer build será lento, los siguientes serán más rápidos gracias al cache
- **Builds paralelos:** Las 4 imágenes se construyen en paralelo para ahorrar tiempo
- **Path filters:** Solo se ejecuta si cambian archivos relevantes
- **Security scan:** Trivy escanea automáticamente las imágenes en busca de vulnerabilidades

---

**¿Problemas?** Revisa los logs en GitHub Actions o consulta la [documentación completa](workflows/README.md).

