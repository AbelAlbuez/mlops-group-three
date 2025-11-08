# 🚀 Guía de Despliegue Automatizado

Script de despliegue automatizado para Proyecto 3 MLOps en VM Rocky Linux.

## 📋 Prerrequisitos

### En tu Mac:

1. **sshpass** (para automatizar contraseñas SSH)
   ```bash
   brew install hudochenkov/sshpass/sshpass
   ```

2. **rsync** (ya viene instalado en macOS)

3. **Conexión SSH** a la VM (ya configurada)

## 🎯 Uso

### Despliegue completo (recomendado):

```bash
cd ~/Projecto-3
./deploy.sh
```

### Opciones disponibles:

```bash
# Modo dry-run (simular sin ejecutar)
./deploy.sh --dry-run

# Saltar limpieza de VM (útil para re-despliegues)
./deploy.sh --skip-cleanup

# Combinar opciones
./deploy.sh --dry-run --skip-cleanup
```

## 📝 Qué hace el script

El script ejecuta los siguientes pasos en orden:

1. **Verificación de prerrequisitos**
   - Verifica que sshpass y rsync estén instalados
   - Prueba conexión SSH a la VM
   - Verifica Docker y Docker Compose en la VM

2. **Limpieza de VM**
   - Detiene todos los servicios Docker
   - Limpia volúmenes y contenedores
   - Elimina el directorio ~/Projecto-3
   - ⚠️ **Requiere confirmación del usuario**

3. **Transferencia de archivos**
   - Sincroniza archivos con rsync
   - Excluye: .pyc, __pycache__, .git, *.log, venv, node_modules, .DS_Store
   - Muestra progreso en tiempo real
   - Verifica archivos críticos

4. **Verificación de configuración**
   - Crea/actualiza archivo .env
   - Configura variables requeridas:
     - `AIRFLOW_UID=50000`
     - `MLFLOW_PORT=8020`
     - `MINIO_API_PORT=8030`
     - `MINIO_CONSOLE_PORT=8031`

5. **Despliegue de servicios**
   - Configura permisos para Airflow (777)
   - Construye imágenes Docker
   - Levanta servicios con `docker compose up -d`
   - Espera 60 segundos para inicialización

6. **Validación de despliegue**
   - Verifica que todos los servicios estén corriendo
   - Comprueba estados: running, healthy, exited (0)

7. **Pruebas de conectividad**
   - Prueba endpoints HTTP:
     - Airflow: http://localhost:8080/health
     - MLflow: http://localhost:8020
     - MinIO API: http://localhost:8030/minio/health/ready
     - MinIO Console: http://localhost:8031

8. **Verificación de datos**
   - Consulta base de datos raw-db
   - Verifica cantidad de registros (~101,766)

9. **Reporte final**
   - Muestra estado de todos los servicios
   - URLs de acceso con IP de la VM
   - Credenciales de acceso
   - Próximos pasos recomendados

## 🔐 Credenciales por defecto

- **Airflow:**
  - Usuario: `admin`
  - Password: `admin123`
  - URL: http://10.43.100.80:8080

- **MinIO:**
  - Usuario: `admin` (o según .env)
  - Password: `adminadmin` (o según .env)
  - API: http://10.43.100.80:8030
  - Console: http://10.43.100.80:8031

- **MLflow:**
  - URL: http://10.43.100.80:8020
  - No requiere autenticación

## 📊 Servicios desplegados

El script verifica estos servicios:

- ✅ `airflow-webserver` (Up)
- ✅ `airflow-scheduler` (Up)
- ✅ `mlflow` (Up, healthy)
- ✅ `minio` (Up, healthy)
- ✅ `mlflow-db` (Up, healthy)
- ✅ `raw-db` (Up, healthy)
- ✅ `clean-db` (Up, healthy)
- ✅ `airflow-init` (Exited 0 - correcto)

## 🐛 Troubleshooting

### Error: "sshpass: command not found"

```bash
brew install hudochenkov/sshpass/sshpass
```

### Error: "Connection refused" o timeout SSH

- Verifica que la VM esté encendida
- Verifica conectividad de red: `ping 10.43.100.80`
- Verifica que el puerto SSH (22) esté abierto

### Error: "Docker not found" en VM

El script verifica Docker, pero si falla:
```bash
ssh estudiante@10.43.100.80
docker --version
```

### Servicios no inician correctamente

Revisa logs:
```bash
ssh estudiante@10.43.100.80
cd ~/Projecto-3
docker compose logs -f [nombre-servicio]
```

### Error de permisos en Airflow

El script configura permisos 777, pero si persiste:
```bash
ssh estudiante@10.43.100.80
sudo chmod -R 777 ~/Projecto-3/airflow/
```

## 📄 Logs

El script genera un log detallado en:
```
/tmp/deploy_YYYYMMDD_HHMMSS.log
```

Ejemplo: `/tmp/deploy_20251108_153045.log`

## ⚙️ Configuración

### Variables de entorno en VM

El script configura automáticamente estas variables en `.env`:

- `AIRFLOW_UID=50000`
- `MLFLOW_PORT=8020`
- `MINIO_API_PORT=8030`
- `MINIO_CONSOLE_PORT=8031`

Otras variables se toman de `.env.copy` si existe.

### Modificar configuración

Si necesitas cambiar la configuración de la VM, edita las variables al inicio del script:

```bash
VM_HOST="10.43.100.80"
VM_USER="estudiante"
VM_PASSWORD="@A18u3z123098@"
VM_PROJECT_DIR="~/Projecto-3"
```

## 🔄 Re-despliegue

Para hacer un re-despliegue completo:

```bash
./deploy.sh
```

Para re-despliegue sin limpiar (más rápido):

```bash
./deploy.sh --skip-cleanup
```

⚠️ **Nota:** `--skip-cleanup` puede causar problemas si hay cambios en docker-compose.yml o Dockerfiles.

## ✅ Verificación post-despliegue

Después del despliegue, verifica:

1. **Servicios corriendo:**
   ```bash
   ssh estudiante@10.43.100.80
   cd ~/Projecto-3
   docker compose ps
   ```

2. **Acceso web:**
   - Abre http://10.43.100.80:8080 (Airflow)
   - Abre http://10.43.100.80:8020 (MLflow)

3. **Ejecutar DAGs:**
   - En Airflow, ejecuta los DAGs en orden:
     1. `1_raw_batch_ingest_15k`
     2. `2_clean_build`
     3. `3_train_and_register`

## 📞 Soporte

Si encuentras problemas:

1. Revisa el log: `/tmp/deploy_*.log`
2. Verifica logs de Docker: `docker compose logs`
3. Revisa este README
4. Consulta el README.md principal del proyecto

---

**Última actualización:** Noviembre 2025

