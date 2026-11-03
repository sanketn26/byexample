# Creating a Kubernetes cluster

The lessons only need a cluster that `kubectl` can reach and that you can
create namespaces in. Pick one of the three below. Check any of them with:

```bash
kubectl config current-context
kubectl get nodes
```

Every lesson creates and deletes its own namespace, so it never touches
other workloads. Do not point them at a shared production cluster.

## Option 1: local, free (kind) — recommended for the lessons

Needs Docker (or Podman) running.

```bash
# install: https://kind.sigs.k8s.io/docs/user/quick-start/#installation
#   macOS: brew install kind kubectl
#   Linux: download the kind and kubectl binaries onto your PATH
kind create cluster --name byexample --wait 120s
kubectl cluster-info --context kind-byexample

# tear down
kind delete cluster --name byexample
```

CI uses this too (`helm/kind-action`). `minikube start` and Docker
Desktop's built-in Kubernetes work equally well.

## Option 2: AWS (EKS)

Costs money while it exists: roughly $0.10/hour for the control plane plus
the EC2 nodes. Delete it when you finish.

Prerequisites: an AWS account, the [AWS CLI](https://aws.amazon.com/cli/)
configured (`aws configure` or SSO), [`eksctl`](https://eksctl.io), and
`kubectl`. Your IAM user or role needs permission to create EKS, EC2, VPC
and CloudFormation resources.

```bash
aws sts get-caller-identity          # confirm which account you are in

eksctl create cluster \
  --name byexample \
  --region us-east-1 \
  --nodegroup-name workers \
  --node-type t3.medium \
  --nodes 2
# takes 15-20 minutes; it writes the kubeconfig entry for you

kubectl get nodes

# if you ever need to regenerate the kubeconfig entry:
aws eks update-kubeconfig --name byexample --region us-east-1

# tear down (removes nodes, VPC, control plane)
eksctl delete cluster --name byexample --region us-east-1
```

Notes:

- Pick a region close to you and keep `--region` on every command.
- A `Service` of type `LoadBalancer` creates an AWS load balancer that
  bills separately and can block VPC deletion. Delete those Services
  before deleting the cluster.
- `eksctl` is the quickest route. For repeatable infrastructure use
  Terraform (`terraform-aws-modules/eks/aws`) instead.

## Option 3: Google Cloud (GKE)

Costs money while it exists. GKE has a monthly free credit that covers one
zonal or Autopilot cluster's management fee; nodes and Autopilot Pods are
still billed.

Prerequisites: a Google Cloud project with billing enabled, the
[`gcloud` CLI](https://cloud.google.com/sdk/docs/install), and `kubectl`.

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable container.googleapis.com

# the auth plugin kubectl needs to talk to GKE
gcloud components install gke-gcloud-auth-plugin

# Autopilot: Google manages the nodes, you pay per Pod (simplest)
gcloud container clusters create-auto byexample --region us-central1

# or Standard: you choose the nodes (a zonal cluster is cheapest)
# gcloud container clusters create byexample \
#   --zone us-central1-a --num-nodes 2 --machine-type e2-medium

# fetch credentials into your kubeconfig
gcloud container clusters get-credentials byexample --region us-central1
# (use --zone us-central1-a instead of --region for the Standard example)

kubectl get nodes

# tear down
gcloud container clusters delete byexample --region us-central1
```

Notes:

- Autopilot enforces resource requests and rejects some privileged Pod
  settings. The lessons' Pods are small and unprivileged, but a Pod with no
  `resources` gets defaults, and the first Pod can take a minute or two
  while capacity is provisioned.
- As on AWS, delete `LoadBalancer` Services and any persistent disks you
  created before deleting the cluster, or they keep billing.

## Switching between clusters

```bash
kubectl config get-contexts                 # list
kubectl config use-context kind-byexample   # switch
```

Always read the current context before running anything destructive.
