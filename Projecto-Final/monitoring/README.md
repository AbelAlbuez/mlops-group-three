# Cluster de Kubernetes

Documentación de la configuración del cluster de Kubernetes.

Usamos MicroK8s porque ofrece una experiencia más prod-ready que Minikube, haciéndolo más robusto y extensible.

## Pasos seguidos

1. Instalar MicroK8s y dependencias necesarias
2. Habilitar los add-ons principales: DNS, Storage, MetalLB, Ingress, Helm3 y Registry
3. Crear los namespaces: `apps` y `monitoring`
4. Configurar almacenamiento persistente
5. Desplegar Prometheus y Grafana
6. Configurar acceso mediante port-forward
7. Validar la recopilación de métricas y visualizar datos en Grafana

### Preparar el entorno

Antes de empezar, necesitas:

1. Sistema operativo actualizado (Rocky Linux)
2. `snapd` instalado. Si no está:
   ```sh
   sudo apt update
   sudo apt install snapd
   ```
3. Permisos de superusuario (sudo)

### Instalar MicroK8s

```sh
# Instalar MicroK8s
sudo snap install microk8s --classic --channel=1.30/stable

# Configurar permisos de usuario
sudo usermod -aG microk8s $USER
sudo chown -R $USER ~/.kube
newgrp microk8s

# Esperar a que MicroK8s esté listo
microk8s status --wait-ready

# Habilitar add-ons esenciales
microk8s enable dns storage metallb:192.168.1.240-192.168.1.250 ingress helm3 registry

# Agregar alias para kubectl (opcional, para facilitar el uso)
sudo snap alias microk8s.kubectl kubectl

# Verificar instalación de Helm
microk8s enable helm3
microk8s helm3 version
```


### Crear namespaces y configurar almacenamiento

```sh
# Crear namespaces para organizar los recursos
kubectl create ns apps          # Para aplicaciones (FastAPI, Streamlit)
kubectl create ns monitoring    # Para herramientas de monitoreo (Prometheus, Grafana)

# Habilitar storage class (si no se habilitó anteriormente)
microk8s enable storage

# Verificar que el storage class esté disponible
kubectl get storageclass
```

### Instalar Prometheus

```sh
microk8s helm3 -n monitoring upgrade --install prometheus prometheus-community/prometheus \
  --set alertmanager.enabled=false \
  --set pushgateway.enabled=false \
  --set kubeStateMetrics.enabled=true \
  --set server.persistentVolume.enabled=false \
  --set server.resources.requests.cpu=100m \
  --set server.resources.requests.memory=256Mi \
  --set server.resources.limits.cpu=500m \
  --set server.resources.limits.memory=1Gi \
  --set nodeExporter.resources.requests.memory=64Mi
```

### Instalar Grafana

Grafana se configura automáticamente con Prometheus como fuente de datos usando los parámetros de Helm:

```sh
microk8s helm3 -n monitoring upgrade --install grafana grafana/grafana \
  --set persistence.enabled=false \
  --set adminPassword=admin123 \
  --set datasources."datasources\.yaml".apiVersion=1 \
  --set datasources."datasources\.yaml".datasources[0].name=Prometheus \
  --set datasources."datasources\.yaml".datasources[0].type=prometheus \
  --set datasources."datasources\.yaml".datasources[0].url=http://prometheus-server.monitoring.svc.cluster.local \
  --set datasources."datasources\.yaml".datasources[0].access=proxy \
  --set datasources."datasources\.yaml".datasources[0].isDefault=true
```

Nota: También existe el archivo `prometheus-datasource.yml` como referencia para configuración manual de datasources en Grafana.



### Exponer servicios mediante Port-Forward

Para acceder a los servicios desde fuera del cluster, usa el script `init-forward.sh` que configura port-forward en background:

```sh
chmod +x init-forward.sh
./init-forward.sh
```

El script expone:
- Grafana: `http://localhost:3010` (usuario: `admin`, contraseña: `admin123`)
- Prometheus: `http://localhost:3011`

Los logs y PIDs de los procesos de port-forward se guardan en `./logs/`.

Para detener los port-forwards:
```sh
pkill -f 'kubectl port-forward'
# o
kill $(cat logs/grafana-forward.pid) $(cat logs/prometheus-forward.pid)
```

### Verificar instalación

Una vez configurado el port-forward, los servicios deberían estar disponibles en:
- Grafana: `http://localhost:3010`
- Prometheus: `http://localhost:3011`

Si accedes desde otra máquina en la red, reemplaza `localhost` con la IP del servidor (ej: `http://10.43.100.87:3010`).
