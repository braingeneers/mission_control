# Shared IAM Policy Files

This folder is the shared access-control source for Braingeneers MCP services.

The intended audience for these files is the person who manages who should be allowed to see or control lab resources. You do not need deep IAM experience to maintain them, but you do need to be careful: changing these files can give someone the ability to inspect experiments, send device commands, or bind hardware to an experiment UUID.

## What These Files Do

The MCP service makes access decisions in two stages:

1. The caller must already have a coarse Auth0 role that allows use of the service at all.
2. These YAML files decide which specific resources that caller may access.

For the integrated-system MCP server, the protected resource hierarchy is:

- `experiment UUID`
- then `device`
- then `command`

In plain language:

- first decide which experiment UUID a person may work with
- then decide which device names under that UUID they may touch
- then decide which commands they may run on those devices

The system is deny-by-default. If a user is not explicitly granted access, they are denied.

## Files In This Folder

- `groups.yaml`
  Maps real identities to reusable groups such as readers, operators, or experiment admins.

- `integrated-system-mcp.policy.yaml`
  Grants groups or individuals access to specific UUIDs, devices, and commands for the integrated-system MCP server.

Recommended practice:

- keep identity membership in `groups.yaml`
- keep resource grants in the service policy file
- reuse groups rather than repeating long user lists in every grant

## Mental Model

Think of the policy in three layers:

1. Who is this person?
   This is handled by `groups.yaml`.

2. Which experiment UUID can they work on?
   This is handled by each item under `grants:` in the service policy.

3. What kind of work may they do there?
   This is handled by `access`, `devices`, and optional `command_rules`.

## Before You Edit

Confirm these points before changing access:

- Which exact experiment UUID is affected?
- Which exact device names are affected?
- Does the person need read-only visibility, normal operation, or experiment-binding powers?
- Should this access apply to one person, or to a reusable group of people?

If you are unsure whether a command can actuate hardware, treat it as high risk and ask the device owner before granting it.

## `groups.yaml` Explained

Example:

```yaml
schema_version: 1
kind: braingeneers-iam-groups
groups:
  integrated-system-readers:
    description: Read-only users for integrated-system experiment UUIDs.
    principals:
      subjects:
        - auth0|alice-example
        - auth0|bob-example
  integrated-system-operators:
    description: Users allowed to run device actuation commands.
    principals:
      subjects:
        - auth0|carol-example
  integrated-system-service-accounts:
    description: Machine clients allowed to call MCP.
    principals:
      client_ids:
        - integrated-system-bot
```

### Top-Level Fields

- `schema_version`
  Must currently be `1`.

- `kind`
  Must currently be `braingeneers-iam-groups`.

- `groups`
  A dictionary of group names.

### Inside Each Group

- `description`
  Human-readable explanation of the group.

- `principals`
  The actual identities that belong to the group.

### Inside `principals`

- `subjects`
  Human user identities, usually Auth0 subject strings such as `auth0|...`.

- `client_ids`
  Service accounts or machine clients.

At least one of `subjects` or `client_ids` must be present.

### When To Use `subjects` vs `client_ids`

Use `subjects` when:

- the caller is a person
- the identity comes from an Auth0 login

Use `client_ids` when:

- the caller is a service account or automation
- the identity is an application client rather than a person

### How To Find The Right Identity String

For a human user, the safest identifier is usually their Auth0 `subject`, which looks like:

- `auth0|abc123...`

For a service account, the safest identifier is usually its `client_id`, which is an application-style name or ID.

If you do not know the right value:

- ask the platform or Auth0 administrator for the caller's exact `subject` or `client_id`
- or check MCP audit logs, which record the authenticated principal seen by the service

Do not guess these identifiers. A typo will usually cause a silent deny, and a mistaken identifier could grant access to the wrong principal.

## `integrated-system-mcp.policy.yaml` Explained

Example:

```yaml
schema_version: 1
kind: braingeneers-mcp-policy
service: integrated-system-mcp
description: >
  UUID-first authorization for the integrated-system MCP server.
group_files:
  - groups.yaml
eligibility:
  required_roles_any:
    - mcp-admin
grants:
  - uuid: 2026-03-12-efi-sandbox
    description: Read-only access for the sandbox experiment.
    principals:
      groups:
        - integrated-system-readers
    access:
      - read
    devices:
      - name: "*"
        access:
          - read
```

### Top-Level Fields

- `schema_version`
  Must currently be `1`.

- `kind`
  Must currently be `braingeneers-mcp-policy`.

- `service`
  The MCP service this policy belongs to. For this file it should be `integrated-system-mcp`.

- `description`
  Human-readable summary of the file.

- `group_files`
  Which group definition files to load. Paths are relative to this folder. Most of the time this should include `groups.yaml`.

- `eligibility.required_roles_any`
  Coarse Auth0 roles that are allowed to use this MCP service at all.

Important:

- This does not replace the YAML grants.
- A user can have the right role and still be denied if there is no UUID grant for them.

- `grants`
  The list of access grants.

## How A `grant` Works

Each item under `grants:` answers:

- for which UUID?
- for which people or groups?
- with what level of access?
- on which devices?
- with which command restrictions?

Example:

```yaml
- uuid: 2026-03-12-efi-sandbox
  description: Dorothy operator access for one UUID.
  principals:
    groups:
      - integrated-system-operators
  access:
    - operate
  devices:
    - name: dorothy
      access:
        - operate
```

### Fields Inside A Grant

- `uuid`
  The experiment UUID this grant applies to.

- `description`
  Human-readable explanation of the grant.

- `principals`
  Who gets this grant.

- `access`
  The permission level at the UUID layer.

- `command_rules`
  Optional command allow or deny rules at the UUID layer.

- `devices`
  Optional device-specific restrictions or additions.

### `principals` Inside A Grant

Supported selectors are:

- `groups`
  Group names from `groups.yaml`

- `subjects`
  Individual human identities

- `client_ids`
  Individual service-account identities

You can use one or more of these. A match on any one of them is enough.

Example:

```yaml
principals:
  groups:
    - integrated-system-readers
  subjects:
    - auth0|special-case-user
```

## Access Levels

The currently supported access levels are:

- `read`
  Read information in a UUID context. This is for discovery and state inspection.

- `operate`
  Run normal device operations. This includes command classes that can actuate hardware.

- `bind`
  Run experiment-binding operations such as `START` and `END`.

Important:

- `bind` is intentionally separate from `operate`.
- Someone with `read` does not automatically get `operate`.
- Someone with `operate` does not automatically get `bind`.
- `START` and `END` are treated as especially sensitive and require explicit allow rules even if `bind` is granted.

## Device Grants

If a UUID grant should apply to all devices, you can use:

```yaml
devices:
  - name: "*"
    access:
      - read
```

If it should apply only to one device:

```yaml
devices:
  - name: dorothy
    access:
      - operate
```

Device names support shell-style matching using `*`.

Examples:

- `name: dorothy`
  Only the device named `dorothy`

- `name: maxwell-*`
  Any device whose name starts with `maxwell-`

- `name: "*"`
  All devices in the UUID

Important:

- if a grant includes a `devices:` list, only matching devices are allowed by that grant
- if the device does not match any listed pattern, the grant does not apply to that device

## Command Rules

Command rules let you narrow or explicitly allow commands.

Each rule has:

- `effect`
  Either `allow` or `deny`

- `commands`
  A list of specific command names such as `START`, `END`, `PING`

- `command_groups`
  A list of broader command categories

You must provide at least one of `commands` or `command_groups`.

### Supported Command Groups

The integrated-system MCP service currently classifies commands into:

- `read-only`
- `experiment-control`
- `actuation`

### Important Behavior

- If a command is explicitly denied, it is denied.
- If a grant contains any allow rules, only matching allowed commands pass that allowlist.
- `experiment-control` commands such as `START` and `END` require an explicit allow rule.

### Example: Explicitly Allow `START` And `END`

```yaml
- uuid: 2026-03-12-efi-sandbox
  description: Experiment admins may bind dorothy to this UUID.
  principals:
    groups:
      - integrated-system-experiment-admins
  access:
    - bind
  devices:
    - name: dorothy
      access:
        - bind
      command_rules:
        - effect: allow
          commands:
            - START
            - END
```

### Example: Allow Read-Only Commands But Deny Actuation

```yaml
- uuid: 2026-03-12-efi-sandbox
  description: Read-only visibility across all devices.
  principals:
    groups:
      - integrated-system-readers
  access:
    - read
  devices:
    - name: "*"
      access:
        - read
      command_rules:
        - effect: allow
          command_groups:
            - read-only
```

### Example: Allow Most Operation But Block One Command

```yaml
- uuid: 2026-03-12-efi-sandbox
  description: Operators may control dorothy but not stop active work.
  principals:
    groups:
      - integrated-system-operators
  access:
    - operate
  devices:
    - name: dorothy
      access:
        - operate
      command_rules:
        - effect: deny
          commands:
            - STOP
```

## Common Maintenance Tasks

### 1. Add A New Reader To An Existing Group

Edit `groups.yaml`:

```yaml
groups:
  integrated-system-readers:
    description: Read-only users for integrated-system experiment UUIDs.
    principals:
      subjects:
        - auth0|alice-example
        - auth0|new-reader-subject
```

Use this when the new person should inherit all existing reader grants.

### 2. Give One Person Read Access To One New UUID

If the reader group already exists, add a new grant to `integrated-system-mcp.policy.yaml`:

```yaml
- uuid: 2026-04-01-efi-organoid-a
  description: Readers may inspect the organoid A run.
  principals:
    groups:
      - integrated-system-readers
  access:
    - read
  devices:
    - name: "*"
      access:
        - read
```

### 3. Give An Operator Access To One Device In One UUID

```yaml
- uuid: 2026-04-01-efi-organoid-a
  description: Camera operator access for microscope-1 only.
  principals:
    groups:
      - integrated-system-operators
  access:
    - operate
  devices:
    - name: microscope-1
      access:
        - operate
```

### 4. Give Someone Permission To Start Or End An Experiment

This requires both `bind` access and an explicit command allow rule:

```yaml
- uuid: 2026-04-01-efi-organoid-a
  description: Experiment admin access for dorothy.
  principals:
    groups:
      - integrated-system-experiment-admins
  access:
    - bind
  devices:
    - name: dorothy
      access:
        - bind
      command_rules:
        - effect: allow
          commands:
            - START
            - END
```

### 5. Remove Access

You can remove access in two ways:

- remove the person from the relevant group in `groups.yaml`
- remove or narrow the relevant `grant` in the service policy file

Examples of narrowing a grant:

- change `name: "*"` to `name: dorothy`
- remove `operate` and keep only `read`
- add a `deny` rule for a dangerous command

## Change Strategy

When possible, prefer these patterns:

- add people to existing groups when the access pattern is standard
- create a new group when a stable team needs a distinct access pattern
- create a new grant when the resource scope changes
- use direct `subjects` only for true exceptions

This keeps the files understandable over time.

## Safe Editing Guidelines

- use exact UUID values
- use exact device names unless you intentionally want a wildcard
- keep descriptions clear enough that another person can understand why the grant exists
- avoid broad `name: "*"` plus `operate` unless that breadth is genuinely intended
- treat `START`, `END`, and any actuation command as high risk
- if a grant is temporary, say so in the description and remove it later

## MockOrganoid Example

The broker-backed `mock-organoid-a` device is intended for safe demos and policy testing.
It is still governed by the same YAML model:

- the caller must have a coarse Auth0 role such as `mcp-guest` or `mcp-admin`
- the caller must still have a YAML grant for the MockOrganoid UUID
- access can still be narrowed by device name and command

Example `groups.yaml` additions:

```yaml
groups:
  integrated-system-mock-organoid-guests:
    description: Guest users limited to the mock organoid demo device.
    principals:
      subjects:
        - auth0|guest-user-1
```

Example `integrated-system-mcp.policy.yaml` additions:

```yaml
eligibility:
  required_roles_any:
    - mcp-admin
    - mcp-guest

grants:
  - uuid: 2026-03-12-efi-mock-organoid
    description: Guests may inspect the mock organoid demo UUID.
    principals:
      groups:
        - integrated-system-mock-organoid-guests
    access:
      - read
    devices:
      - name: mock-organoid-a
        access:
          - read

  - uuid: 2026-03-12-efi-mock-organoid
    description: Guests may use safe demo commands on the mock organoid.
    principals:
      groups:
        - integrated-system-mock-organoid-guests
    access:
      - operate
    devices:
      - name: mock-organoid-a
        access:
          - operate
        command_rules:
          - effect: allow
            commands:
              - PING
              - STATUS
              - TWIDDLE

  - uuid: 2026-03-12-efi-mock-organoid
    description: Guests may bind the mock organoid to or from its demo UUID.
    principals:
      groups:
        - integrated-system-mock-organoid-guests
    access:
      - bind
    devices:
      - name: mock-organoid-a
        access:
          - bind
        command_rules:
          - effect: allow
            commands:
              - START
              - END
```

Important points:

- `mock-organoid-a` is still a normal device name in the policy file; it is not a special syntax
- keeping it on its own UUID makes the grant easy to reason about
- if you add command rules, only the listed commands will be allowed for that grant
- `START` and `END` still require an explicit allow rule even for mock devices

## Troubleshooting

If someone says they still cannot access a resource, check these in order:

1. Are they in the right `subjects` or `client_ids` list, or in a group referenced by the grant?
2. Do they have the required coarse Auth0 role such as `mcp-admin`?
3. Is the UUID correct?
4. Does the device name match the `name` pattern?
5. Does the grant include the needed `access` level?
6. If the command is `START` or `END`, is there an explicit `allow` rule?
7. If there are command rules, is the command being blocked by an allowlist or a deny rule?

## Minimal Working Example

This is a small but complete example that gives:

- Alice read-only access to one UUID
- Carol operator access to `dorothy`
- David experiment-binding access to `dorothy`

`groups.yaml`

```yaml
schema_version: 1
kind: braingeneers-iam-groups
groups:
  integrated-system-readers:
    description: Read-only users.
    principals:
      subjects:
        - auth0|alice
  integrated-system-operators:
    description: Device operators.
    principals:
      subjects:
        - auth0|carol
  integrated-system-experiment-admins:
    description: People allowed to start and end experiments.
    principals:
      subjects:
        - auth0|david
```

`integrated-system-mcp.policy.yaml`

```yaml
schema_version: 1
kind: braingeneers-mcp-policy
service: integrated-system-mcp
group_files:
  - groups.yaml
eligibility:
  required_roles_any:
    - mcp-admin
grants:
  - uuid: 2026-04-01-efi-organoid-a
    description: Alice can inspect this UUID.
    principals:
      groups:
        - integrated-system-readers
    access:
      - read
    devices:
      - name: "*"
        access:
          - read
  - uuid: 2026-04-01-efi-organoid-a
    description: Carol can operate dorothy.
    principals:
      groups:
        - integrated-system-operators
    access:
      - operate
    devices:
      - name: dorothy
        access:
          - operate
  - uuid: 2026-04-01-efi-organoid-a
    description: David can start and end dorothy for this UUID.
    principals:
      groups:
        - integrated-system-experiment-admins
    access:
      - bind
    devices:
      - name: dorothy
        access:
          - bind
        command_rules:
          - effect: allow
            commands:
              - START
              - END
```

## Final Advice

These files are not just paperwork. They are the control boundary for real lab resources.

When in doubt:

- start narrow
- grant only the minimum needed access
- prefer read-only first
- avoid wildcard operation rights unless they are clearly justified
- ask the device or experiment owner before granting high-risk commands
