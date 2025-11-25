# Instalación de ArgoCD

## 1. Crear el namespace de ArgoCD
```bash
kubectl create namespace argocd
```

## 2. Instalar ArgoCD
```bash
kubectl apply -n argocd -f install.yaml
```

## 3. Configurar acceso sin TLS (inseguro)
```bash
kubectl -n argocd patch configmap argocd-cmd-params-cm \
  -p '{"data": {"server.insecure": "true"}}'
```
Esto permite acceso HTTP sin certificados TLS, útil para desarrollo local.

## 4. Verificar la configuración
```bash
kubectl -n argocd get configmap argocd-cmd-params-cm -o yaml
```

## 5. Reiniciar el servidor de ArgoCD
```bash
kubectl -n argocd rollout restart deployment argocd-server
```

## 6. Verificar el estado de los pods
```bash
kubectl -n argocd get pods -n argocd
```

## 7. Acceder a la UI de ArgoCD
```bash
kubectl port-forward svc/argocd-server -n argocd --address 0.0.0.0 8080:80
```
Esto crea un port-forward al puerto local 8080, permitiendo acceso desde cualquier IP.

## Credenciales de acceso
- Usuario: admin
- Contraseña: NuevaPassword123