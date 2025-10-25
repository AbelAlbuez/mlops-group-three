# Cluster de Kubernetes

Esta es la documentación de la configacion realizada en el cluster de kubernetes.

> Se utilizó microk8s ya que ofrece una experiencia mas prod-ready que minikube, haciendolo mas robusto y extensible.

## Guia de pasos seguidos
1. Instalar microk8s y dependencias necesarias.
2. Habilitar los add-ons principales: DNS, Storage, MetalLB, Ingress, Helm3 y Registry.
3. Crear los namespaces: `apps` y `monitoring`.
4. Configurar almacenamiento persistente .
5. Desplegar Prometheus y Grafana.
6. Asegurar el acceso mediante Ingress.
7. Validar la recopilación de métricas y visualizar datos en Grafana.

### Preparar el entorno

1. Actualiza tu sistema operativo y dependencias.
2. Instala `snapd` si no está instalado:  
   ```sh
   sudo apt update
   sudo apt install snapd
   ```
3. Verifica que tienes permisos de superusuario (sudo) disponibles.

### Instalar MicroK8s

```sh
# instalar microk8s
sudo snap install microk8s --classic --channel=1.30/stable

# dar permisos
sudo usermod -aG microk8s $USER
sudo chown -R $USER ~/.kube
newgrp microk8s

# Add-ons esenciales
microk8s status --wait-ready
microk8s enable dns storage metallb:192.168.1.240-192.168.1.250 ingress helm3 registry

# Agregar alias kubectl
sudo snap alias microk8s.kubectl kubectl


# instalar helm
microk8s enable helm3
microk8s helm3 version

```


### Crear el namespace y la estructura

```sh

kubectl create ns apps    # FastAPI, Streamlit
kubectl create ns monitoring   # Prometheus, Grafana


# habilitar storage
microk8s enable storage
kubectl get storageclass

```

### Instalar Grafana y Prometheus

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

Se crea el archivo `prometheus-datasource.yaml` para crear grafana con prometheus ya configurado.


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



### Exponer grafana

Se utiliza el archivo `init-forward.sh` para exponer el puerto 3000 en background.

- Grafana (puerto 3010)
- Prometheus (puerto 3011)

### Revisar

Ahora deberia estar disponible en `http://http://10.43.100.87:3010`