# Put your Kubernetes manifests here

Delete this file once you've added them.

These are the YAML files you ran `kubectl apply -f` on to get your chatbot running on
the cluster. Copy in whichever ones you had, most people have four or five:

```
k8s/
├── deployment.yaml   the pod that runs your chatbot          <- the important one
├── service.yaml      gives the pod an address in the cluster
├── ingress.yaml      the public HTTPS front door
├── pvc.yaml          storage for your vector database
└── configmap.yaml    non-secret settings (model name, API address)
```

Your chatbot's page **reads these files** and draws the chain from the internet down to
your storage, so what visitors see is what you actually deployed. Nothing here gets
applied to any cluster, it's a record of what you did.

## Getting them back off the cluster

If you didn't keep local copies and still have access:

```bash
kubectl -n rehs-2026-chatbot get deploy,svc,ingress,pvc,configmap

# then, for each one you own:
kubectl -n rehs-2026-chatbot get deploy <your-deployment> -o yaml > deployment.yaml
kubectl -n rehs-2026-chatbot get svc <your-service> -o yaml > service.yaml
```

Those exports contain a lot of cluster bookkeeping (`status:`, `managedFields`,
`resourceVersion`, `uid`). Trimming it down to what you actually wrote makes the file
readable, and the page nicer, but it isn't required.

## Never commit a Secret

Your NRP token was created on the cluster with `kubectl create secret`, and it must stay
there. Do not add `secret.yaml`, do not paste a token into any of these files, and don't
export the Secret from the cluster. The automated check will fail your pull request if
it finds one, because a token in a public repo is a leaked token.
