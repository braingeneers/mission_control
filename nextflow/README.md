## Running Nextflow on the [National Research Platform (NRP)](https://portal.nrp-nautilus.io)

#### Instructions for running a toy nextflow workflow on the [NRP kubernetes cluster](https://portal.nrp-nautilus.io) (examples use the `braingeneers` namespace; this should be changed to the relevant namespace for your org in both the commands below and the contents of the yml files included).

### SETUP (note: this only needs to be done once and is here as a record)
1. First, create a [PersistentVolumeClaim (PVC)](https://kubernetes.io/docs/concepts/storage/persistent-volumes/):

```commandline
kubectl apply -f pvc.yml
```

2. Second, create a service account:

```commandline
kubectl create serviceaccount nextflow-sa -n braingeneers
```

3. Create the necessary roles that nextflow needs:

```commandline
kubectl apply -f resources/configmap_role.yml
kubectl apply -f resources/jobs_role.yml
kubectl apply -f resources/pods_role.yml
kubectl apply -f resources/pods_delete_role.yml
kubectl apply -f resources/pvc_role.yml
```

4. Create role bindings to attach those roles to the service account:

```commandline
kubectl apply -f resources/configmap_rolebinding.yml
kubectl apply -f resources/jobs_rolebinding.yml
kubectl apply -f resources/pods_rolebinding.yml
kubectl apply -f resources/pods_delete_rolebinding.yml
kubectl apply -f resources/pvc_rolebinding.yml
```

We now have a service account that should have the permissions necessary to run a nextflow workflow.

5. Create a secret token for the service account (note: this yml produces a token that does not expire):

```commandline
kubectl apply -f resources/sa-secret.yml
```

6. Generate a kube config with the above secret token (`GENERATED-SA-TOKEN`).  The token can be generated with:

```commandline
kubectl get secrets nextflow-sa -o jsonpath='{.data.token}' | base64 --decode
```

7. You'll also need `CLUSTER-TOKEN`, `SERVER_IP`, and `SERVER_PORT`.  These should already be in your current working kube config file.  Copy and paste them over.

The kube config should look like:

```yaml
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {CLUSTER-TOKEN}
    server: https://{SERVER_IP}:{SERVER_PORT}
  name: nautilus
contexts:
- context:
    cluster: nautilus
    namespace: braingeneers
    user: nextflow-sa
  name: nautilus
current-context: nautilus
kind: Config
preferences: {}
users:
- name: nextflow-sa
  user:
    token: {GENERATED-SA-TOKEN}
```

### RUNNING A WORKFLOW

1. If you don't have it installed already, download the latest nextflow binary and make it executable:

```commandline
wget https://github.com/nextflow-io/nextflow/releases/download/v23.10.1/nextflow
sudo chmod 1777 nextflow
```

2. Copy this nextflow config to the current directory:

```commandline
wget https://raw.githubusercontent.com/DailyDreaming/k8-nextflow/master/nextflow.config
```

Then run the workflow with the following command:

```commandline
./nextflow kuberun https://github.com/DailyDreaming/k8-nextflow -v whimvol:/workspace -head-cpus 1 -head-memory 256Mi
```

NOTE: The toy workflow tests two processes sharing a file, which should test shared access to the same file space [this is the purpose of the [PersistentVolumeClaim (PVC)](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)].

NOTE: [FUSE](https://github.com/s3fs-fuse/s3fs-fuse) requires a plug-in installed on each worker, and so does not seem to be currently feasible without security considerations and cluster-wide changes.
