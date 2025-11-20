# Instalación de ArgoCD

## 1. Crear el namespace de ArgoCD
```bash
kubectl create namespace argocd
```
Crea un namespace dedicado llamado `argocd` donde se desplegarán todos los componentes de ArgoCD.

## 2. Instalar ArgoCD
```bash
kubectl apply -n argocd -f install.yaml
```
Aplica el archivo de instalación de ArgoCD que contiene todos los recursos necesarios (deployments, services, configmaps, etc.).

## 3. Configurar acceso sin TLS (inseguro)
```bash
kubectl -n argocd patch configmap argocd-cmd-params-cm \
  -p '{"data": {"server.insecure": "true"}}'
```
Modifica el ConfigMap para permitir acceso HTTP sin certificados TLS. Útil para desarrollo local.

## 4. Verificar la configuración
```bash
kubectl -n argocd get configmap argocd-cmd-params-cm -o yaml
```
Muestra el ConfigMap en formato YAML para verificar que el parámetro `server.insecure` se aplicó correctamente.

## 5. Reiniciar el servidor de ArgoCD
```bash
kubectl -n argocd rollout restart deployment argocd-server
```
Reinicia el deployment del servidor de ArgoCD para que aplique los cambios de configuración.

## 6. Verificar el estado de los pods
```bash
kubectl -n argocd get pods -n argocd
```
Lista todos los pods en el namespace de ArgoCD para confirmar que están corriendo correctamente.

## 7. Acceder a la UI de ArgoCD
```bash
kubectl port-forward svc/argocd-server -n argocd --address 0.0.0.0 8080:80
```
Crea un port-forward del servicio de ArgoCD al puerto local 8080, permitiendo acceso desde cualquier IP (0.0.0.0).

## Credenciales de acceso
- **Usuario:** admin
- **Contraseña:** NuevaPassword123