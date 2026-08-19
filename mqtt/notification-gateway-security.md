# Notification Gateway MQTT Security Gate

The notification gateway supports MQTT, but Mission Control intentionally
deploys its MQTT adapter disabled at first. The current broker image and ACL
allow broad topic access, so a publisher could otherwise impersonate another
producer by selecting its request topic. HTTP bearer authentication is the
production transport until this gate is complete.

Do not set `notification-gateway` `MQTT_ENABLED` to `true` until an operator has
completed and tested every item below:

1. Inventory current MQTT usernames, client IDs, publish topics, subscribe
   filters, QoS levels, and retained-message use. Include devices and services
   that connect from outside the Compose network.
2. Pin the EMQX base image and Braingeneers MQTT image to reviewed immutable
   versions; remove `latest` from the build and production Compose reference.
3. Enable broker authentication and create one gateway identity plus one
   identity per producer. Credentials remain operator-owned Kubernetes Secrets.
4. Deny anonymous access and make the final ACL rule deny by default.
5. Permit the gateway identity to subscribe only to
   `notifications/v1/requests/+` and publish only to
   `notifications/v1/results/#`.
6. Permit each producer identity to publish only to its exact
   `notifications/v1/requests/<producer-id>` topic and subscribe only to its
   `notifications/v1/results/<producer-id>/+` topic. Do not rely on a producer
   ID supplied inside the JSON payload.
7. Preserve explicitly inventoried legacy topics with least-privilege rules;
   do not translate the old Slack bridge topics into the new contract.
8. Verify positive and negative ACL cases from disposable clients, including
   cross-producer publish/subscribe denial, wildcard denial, retained-message
   rejection for notification requests, and QoS 1 delivery.
9. Roll out the pinned broker separately, monitor client reconnects, then set
   `MQTT_ENABLED: "true"` for only the notification gateway and recreate it.

The authoritative notification request/result contract lives in the
notification gateway repository and the Braingeneers wiki. Broker credentials
or ACL data must never be committed here.
