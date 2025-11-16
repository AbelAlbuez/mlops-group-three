    kubectl create namespace argocd
kubectl apply -n argocd -f install.yaml
kubectl -n argocd patch configmap argocd-cmd-params-cm \
  -p '{"data": {"server.insecure": "true"}}'

  kubectl -n argocd get configmap argocd-cmd-params-cm -o yaml
kubectl -n argocd rollout restart deployment argocd-server
kubectl -n argocd get pods -n argocd

kubectl port-forward svc/argocd-server -n argocd --address 0.0.0.0 8080:80


admin
NuevaPassword123