# All braingeneers services require authentication via Auth0->CILogon (integrates with UCSC authentication)
# A service account token can be obtained in braingeneerspy after successful autentication. This token is automatically
# refreshed once a week as long as the code is used at least once a month.
# A service account token is also stored in the NRP kubernetes secrets, this is needed for jobs run on the NRP.
# Jobs being run on the NRP require user authentication, so keeping the token in kubernetes secrets is secured.
# This cron task updates the service account token in the NRP/kubernetes/secrets daily.

FROM bitnami/kubectl:latest

COPY refresh-braingeneers-jwt-service-account-token.sh /
ENTRYPOINT ["/refresh-braingeneers-jwt-service-account-token.sh"]
