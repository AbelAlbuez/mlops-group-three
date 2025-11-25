# Guía de Despliegue Automatizado

Script para desplegar el Proyecto 3 MLOps en una VM Rocky Linux.

## Prerrequisitos

En tu Mac necesitas:

1. **sshpass** para automatizar las contraseñas SSH:
   ```bash
   brew install hudochenkov/sshpass/sshpass
   ```

2. **rsync** (ya viene instalado en macOS)

3. **Conexión SSH** a la VM configurada

## Uso

Despliegue completo:
```bash
cd ~/Projecto-3
./deploy.sh
```

Opciones disponibles:
```bash
# Modo dry-run (simular sin ejecutar)
./deploy.sh --dry-run

# Saltar limpieza de VM (útil para re-despliegues)
./deploy.sh --skip-cleanup

# Combinar opciones
./deploy.sh --dry-run --skip-cleanup
```

## Qué hace el script

El script ejecuta estos pasos:

1. **Verificación de prerrequisitos**
   Verifica que sshpass y rsync estén instalados, prueba la conexión SSH a la VM, y verifica Docker y Docker Compose en la VM.

2. **Limpieza de VM**
   Detiene todos los servicios Docker, limpia volúmenes y contenedores, y elimina el directorio ~/Projecto-3. Requiere confirmación del usuario.

3. **Transferencia de archivos**
   Sincroniza archivos con rsync, excluyendo .pyc, __pycache__, .git, *.log, venv, node_modules, .DS_Store. Muestra progreso y verifica archivos críticos.

4. **Verificación de configuración**
   Crea/actualiza el archivo .env con estas variables:
   - `AIRFLOW_UID=50000`
   - `MLFLOW_PORT=8020`
   - `MINIO_API_PORT=8030`
   - `MINIO_CONSOLE_PORT=8031`

5. **Despliegue de servicios**
   Configura permisos para Airflow (777), construye imágenes Docker, levanta servicios con `docker compose up -d`, y espera 60 segundos para la inicialización.

6. **Validación de despliegue**
   Verifica que todos los servicios estén corriendo (running, healthy, exited 0).

7. **Pruebas de conectividad**
   Prueba endpoints HTTP:
   - Airflow: http://localhost:8080/health
   - MLflow: http://localhost:8020
   - MinIO API: http://localhost:8030/minio/health/ready
   - MinIO Console: http://localhost:8031

8. **Verificación de datos**
   Consulta la base de datos raw-db y verifica que haya ~101,766 registros.

9. **Reporte final**
   Muestra el estado de todos los servicios, URLs de acceso con IP de la VM, credenciales, y próximos pasos.

## Credenciales por defecto

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

## Servicios desplegados

El script verifica que estos servicios estén corriendo:
- `airflow-webserver` (Up)
- `airflow-scheduler` (Up)
- `mlflow` (Up, healthy)
- `minio` (Up, healthy)
- `mlflow-db` (Up, healthy)
- `raw-db` (Up, healthy)
- `clean-db` (Up, healthy)
- `airflow-init` (Exited 0 - esto es correcto)

## Troubleshooting

### Error: "sshpass: command not found"

```bash
brew install hudochenkov/sshpass/sshpass
```

### Error: "Connection refused" o timeout SSH

Verifica que la VM esté encendida, prueba la conectividad con `ping 10.43.100.80`, y asegúrate de que el puerto SSH (22) esté abierto.

### Error: "Docker not found" en VM

El script verifica Docker, pero si falla:
```bash
ssh estudiante@10.43.100.80
docker --version
```

### Servicios no inician correctamente

Revisa los logs:
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

## Logs

El script genera un log detallado en `/tmp/deploy_YYYYMMDD_HHMMSS.log` (ejemplo: `/tmp/deploy_20251108_153045.log`).

## Configuración

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

## Re-despliegue

Para hacer un re-despliegue completo:
```bash
./deploy.sh
```

Para re-despliegue sin limpiar (más rápido):
```bash
./deploy.sh --skip-cleanup
```

Nota: `--skip-cleanup` puede causar problemas si hay cambios en docker-compose.yml o Dockerfiles.

## Verificación post-despliegue

Después del despliegue:

1. Verifica que los servicios estén corriendo:
   ```bash
   ssh estudiante@10.43.100.80
   cd ~/Projecto-3
   docker compose ps
   ```

2. Accede a las interfaces web:
   - http://10.43.100.80:8080 (Airflow)
   - http://10.43.100.80:8020 (MLflow)

3. Ejecuta los DAGs en Airflow en este orden:
   - `1_raw_batch_ingest_15k`
   - `2_clean_build`
   - `3_train_and_register`

## Soporte

Si encuentras problemas:
1. Revisa el log: `/tmp/deploy_*.log`
2. Verifica logs de Docker: `docker compose logs`
3. Revisa este README
4. Consulta el README.md principal del proyecto

---

Última actualización: Noviembre 2025

