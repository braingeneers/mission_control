#!/usr/bin/env bash
#
# To manage Braingeneers services first configure kubectl to work on the server you want to manage services on
# (e.g. the "braingeneers.gi.ucsc.edu server"), then run this script `authenticate.sh`. This script will check
# that you have kubectl working and if so will pull a service account kubernetes configuration from our namespace
# secrets so that services that rely on secrets in our namespace have access to them (via the secret-fetcher service,
# which starts automatically and is defined in docker-compose.yaml with all the other services).
#
set -euo pipefail

# --- CONFIGURABLE PARAMETERS ---
NAMESPACE="braingeneers"          # Namespace where the kube-config secret lives
SECRET_NAME="kube-config"         # Secret that holds the kubeconfig
SECRET_KEY="config"               # Key inside the secret data that contains the kubeconfig
OUT_FILE="${HOME}/.kube/braingeneers-service.yaml"  # Where to write the local kubeconfig
# --------------------------------

info()  { printf '%s\n' "==> $*"; }
warn()  { printf '%s\n' "WARN: $*" >&2; }
fail()  { printf '%s\n' "ERROR: $*" >&2; exit 1; }

# Detect a portable base64 decode flag (Linux/BSD)
detect_base64_decode_flag() {
  if base64 --help 2>&1 | grep -q -- '--decode'; then
    echo "--decode"
  else
    echo "-d"
  fi
}

info "Braingeneers authentication bootstrap"
info "Namespace: ${NAMESPACE}, Secret: ${SECRET_NAME}, Output: ${OUT_FILE}"
echo

# 1. Check kubectl exists
if ! command -v kubectl >/dev/null 2>&1; then
  fail "kubectl is not installed or not on your PATH.
Please install kubectl and ensure you can run:
  kubectl version --client
before running this script."
fi

# 2. Check current context
info "Checking kubectl configuration..."
if ! kubectl config current-context >/dev/null 2>&1; then
  fail "kubectl has no current context configured.
Make sure you have downloaded and configured the Braingeneers kubeconfig
(from the cluster's OIDC flow) and that it is active."
fi

CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || echo "<unknown>")
info "Current kubectl context: ${CURRENT_CONTEXT}"

# 3. Verify you can reach the cluster / namespace
info "Verifying access to namespace '${NAMESPACE}'..."
if ! kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1; then
  fail "Cannot access namespace '${NAMESPACE}'.
Possible causes:
  - Your current context is not pointing at the Braingeneers cluster.
  - Your account does not have access to this namespace.
Try:
  kubectl get namespaces
and confirm '${NAMESPACE}' is visible."
fi

# 4. Verify you can read the kube-config secret
info "Checking access to secret '${SECRET_NAME}' in namespace '${NAMESPACE}'..."
if ! kubectl get secret "${SECRET_NAME}" -n "${NAMESPACE}" >/dev/null 2>&1; then
  CAN_I=$(kubectl auth can-i get secret "${SECRET_NAME}" -n "${NAMESPACE}" 2>/dev/null || echo "unknown")
  if [ "${CAN_I}" = "no" ]; then
    fail "kubectl is working, but you are NOT authorized to read secret '${SECRET_NAME}'.
Please ask the cluster admin to grant you access to this secret."
  else
    fail "kubectl cannot read secret '${SECRET_NAME}' in namespace '${NAMESPACE}'.
Possible causes:
  - The secret does not exist.
  - Your context/permissions are misconfigured.
Ask the cluster admin to verify the secret and your access."
  fi
fi

# 5. Extract kubeconfig from the secret
info "Downloading kubeconfig from secret '${SECRET_NAME}'..."
SECRET_DATA=$(kubectl get secret "${SECRET_NAME}" -n "${NAMESPACE}" \
  -o "jsonpath={.data.${SECRET_KEY}}" 2>/dev/null || true)

if [ -z "${SECRET_DATA}" ]; then
  fail "Secret '${SECRET_NAME}' does not contain a '${SECRET_KEY}' key.
Ask the cluster admin to ensure the secret stores the kubeconfig under this key."
fi

mkdir -p "$(dirname "${OUT_FILE}")"

DECODE_FLAG=$(detect_base64_decode_flag)
printf '%s' "${SECRET_DATA}" | base64 "${DECODE_FLAG}" > "${OUT_FILE}"
chmod 600 "${OUT_FILE}"

info "Wrote service kubeconfig to: ${OUT_FILE}"

# 6. Sanity check with the generated kubeconfig
info "Verifying the generated kubeconfig works..."
if KUBECONFIG="${OUT_FILE}" kubectl --namespace "${NAMESPACE}" get secret "${SECRET_NAME}" >/dev/null 2>&1; then
  echo
  echo "✅ Authentication check succeeded."
  echo "   You now have a Braingeneers service kubeconfig at:"
  echo "     ${OUT_FILE}"
  echo
  echo "   Our docker-compose setup can mount this file into the key service"
  echo "   container to fetch secrets from the '${NAMESPACE}' namespace."
  echo
else
  fail "The generated kubeconfig could not be used to read secret '${SECRET_NAME}'.
Something is inconsistent between the secret and cluster configuration.
Please contact the cluster admin."
fi
