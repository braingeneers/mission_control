# Features

Generated: 2026-11-18 | commit: 775a1d79c860b23ddbbf59f5a1ddd1dfc237b3b7 | mode: all

## 1. data-lifecycle
Project scripts; see per-file summaries.

**Entry points (full tier):** [data-lifecycle.skills.backup-reprocess-check.scripts.analyze_two_run_check](data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py.md), [data-lifecycle.skills.backup-reprocess-check.scripts.run_two_run_check](data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py.md), [data-lifecycle.src.generate_cleanup_report](data-lifecycle/src/generate_cleanup_report.py.md), [data-lifecycle.src.generate_puts_deletes](data-lifecycle/src/generate_puts_deletes.py.md), [data-lifecycle.src.glacier_cost_analysis_plot](data-lifecycle/src/glacier_cost_analysis_plot.py.md), [data-lifecycle.src.stage4_process_puts_deletes](data-lifecycle/src/stage4_process_puts_deletes.py.md), [data-lifecycle.src.stage4_upload_poc](data-lifecycle/src/stage4_upload_poc.py.md)

**Supporting files:**
- [analyze_two_run_check.py](data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py.md) — Analyzes and compares two consecutive backup pipeline execution runs (Run 1 and Run 2) to detect anomalies, regressions, missing source objects, duplicate puts, and activity discrepancies.
- [run_two_run_check.py](data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py.md) — Orchestrates two consecutive containerized backup pipeline execution runs against S3/Glacier inventory manifests to verify idempotent reprocessing and differential correctness.
- [badkeys.py](data-lifecycle/src/badkeys.py.md) — Defines data models, serialization utilities, and Slack formatting for recording problematic S3 bucket keys (control characters, unicode escaping, and HeadObject success followed by GetObject failure).
- [generate_cleanup_report.py](data-lifecycle/src/generate_cleanup_report.py.md) — Generates the monthly data-retention report bundle including interactive HTML, multipage PDF summary charts, Slack notification payload, and retention candidate CSV from scientific and backup inventories.
- [generate_puts_deletes.py](data-lifecycle/src/generate_puts_deletes.py.md) — Stage 3 comparison engine comparing Ceph/NRP scientific storage inventory against Glacier backup inventory; generates put lists for unbacked files, delete lists for expired files per policy, and badkeys lists.
- [glacier_cost_analysis_plot.py](data-lifecycle/src/glacier_cost_analysis_plot.py.md) — Plots estimated AWS Glacier storage costs vs retention policy duration in years, computing cumulative retained volumes and projecting monthly expenses from Ceph/S3 inventory files.
- [lifecycle_constants.py](data-lifecycle/src/lifecycle_constants.py.md) — Defines reserved constant object names and marker suffixes for the Braingeneers data lifecycle retention management subsystem.
- [lifecycle_controls.py](data-lifecycle/src/lifecycle_controls.py.md) — Implements control-object semantics for dataset retention, parsing zero-byte marker objects for atomic directories and individual files to compute effective last-modified dates.
- [stage4_keys.py](data-lifecycle/src/stage4_keys.py.md) — Provides S3 object key sanitization, URL decoding, rclone special dot-segment normalization, and source lookup candidate generation for Stage 4 backup transfers.
- [stage4_process_puts_deletes.py](data-lifecycle/src/stage4_process_puts_deletes.py.md) — Stage 4 parallel execution engine streaming object backups from Ceph/NRP S3 to AWS Glacier S3 using smart-open multipart streams, retry logic, error classification, and progress logging.
- [stage4_upload_poc.py](data-lifecycle/src/stage4_upload_poc.py.md) — Proof-of-concept benchmarking script comparing throughput and memory consumption across smart-open, AWS CLI, and rclone for streaming large dataset uploads to Glacier.

## 2. docker-maintenance
Project scripts; see per-file summaries.

**Entry points (full tier):** [docker-maintenance.maintenance](docker-maintenance/maintenance.py.md)

**Supporting files:**
- [maintenance.py](docker-maintenance/maintenance.py.md) — Autonomous maintenance daemon managing Docker daemon storage: periodically prunes dangling images and builder cache, monitors disk thresholds, and issues Slack alerts on critical disk fill.

## 3. experiment-dash
Project scripts; see per-file summaries.

**Entry points (full tier):** [experiment-dash.experiment-plotly-app](experiment-dash/experiment-plotly-app.py.md)

**Supporting files:**
- [style.css](experiment-dash/assets/style.css.md) — Custom stylesheet for the experiment telemetry Plotly Dash application, styling container layout, cards, and hiding Dash debug menus.
- [dashboard_helpers.py](experiment-dash/dashboard_helpers.py.md) — Helper library for the telemetry experiment dashboard, constructing MQTT topic strings and publishing commands (start, end, ping, pause, resume, stop, sched) to Braingeneers IoT devices.
- [experiment-plotly-app.py](experiment-dash/experiment-plotly-app.py.md) — Plotly Dash interactive web application for monitoring and controlling wet lab organoid experiments, device telemetry, status checks, and scheduling.

## 4. job-h5repack
Project scripts; see per-file summaries.

**Entry points (full tier):** [job-h5repack.get_task](job-h5repack/get_task.py.md), [job-h5repack.init](job-h5repack/init.py.md), [job-h5repack.update_metadata](job-h5repack/update_metadata.py.md)

**Supporting files:**
- [get_task.py](job-h5repack/get_task.py.md) — Worker task dequeue script for h5repack batch processing; fetches the next electrophysiology HDF5 data file from an MQTT message queue.
- [init.py](job-h5repack/init.py.md) — Initialization CLI script for electrophysiology h5repack jobs, reading dataset metadata from S3 and populating an MQTT message queue with data files to repack.
- [update_metadata.py](job-h5repack/update_metadata.py.md) — Post-processing task updater acquiring an S3 distributed lock to update electrophysiology experiment metadata when an HDF5 file has been converted to row-major layout.

## 5. logging-s3
Project scripts; see per-file summaries.

**Entry points (full tier):** [logging-s3.log](logging-s3/log.py.md)

**Supporting files:**
- [log.py](logging-s3/log.py.md) — Telemetry daemon listening indefinitely to MQTT topic `telemetry/#` and streaming individual message payloads to S3 as single-message TSV files.

## 6. logging-s3-aggregator
Project scripts; see per-file summaries.

**Entry points (full tier):** [logging-s3-aggregator.log_aggregator](logging-s3-aggregator/log_aggregator.py.md)

**Supporting files:**
- [log_aggregator.py](logging-s3-aggregator/log_aggregator.py.md) — Periodic aggregation service that scans singleton S3 telemetry log files, combines up to 100 entries per batch into cumulative log TSVs, and deletes processed singles.

## 7. nginx-reverse-proxy
Project scripts; see per-file summaries.

**Entry points (full tier):** library-style components below

**Supporting files:**
- [index.html](nginx-reverse-proxy/static/index.html.md) — Static landing page served by Nginx reverse proxy presenting user login prompt and redirect button for CILogon OAuth authentication.

## 8. oauth2-proxy
Project scripts; see per-file summaries.

**Entry points (full tier):** library-style components below

**Supporting files:**
- [error.html](oauth2-proxy/error.html.md) — Custom error template for oauth2-proxy displaying authentication failure explanations, Auth0 role requirements, and Slack #helpdesk troubleshooting guidance.

## 9. plotly-dash-picroscope-control-console
Project scripts; see per-file summaries.

**Entry points (full tier):** [plotly-dash-picroscope-control-console.app](plotly-dash-picroscope-control-console/app.py.md), [plotly-dash-picroscope-control-console.callbacks](plotly-dash-picroscope-control-console/callbacks.py.md)

**Supporting files:**
- [Experiment_Metadata_SQL.py](plotly-dash-picroscope-control-console/Experiment_Metadata_SQL.py.md) — Database query interface module intended for retrieving experiment metadata and device shadow state from SQLite databases.
- [app.py](plotly-dash-picroscope-control-console/app.py.md) — Main web application server for the Picroscope microscope control console, assembling Dash tabs for experiment controls, imaging parameters, and livestream feeds.
- [experiment_panel.py](plotly-dash-picroscope-control-console/app_elements/experiment_panel.py.md) — Defines the experiment setup and metadata management UI tab layout for the Picroscope console, including forms for researchers, organoid lines, and imaging schedules.
- [imaging_panel.py](plotly-dash-picroscope-control-console/app_elements/imaging_panel.py.md) — Defines the camera exposure, focus, stage position, and multi-well plate imaging parameter control panel UI tab for the Picroscope console.
- [livestream_panel.py](plotly-dash-picroscope-control-console/app_elements/livestream_panel.py.md) — Defines the real-time optical livestream viewer tab for the Picroscope console, embedding video streams and current capture previews from active microscopes.
- [resizing_script.js](plotly-dash-picroscope-control-console/assets/resizing_script.js.md) — Clientside JavaScript callback helper for the Picroscope Dash console, triggering window resize events after a timeout to force responsive Plotly charts to recalculate dimensions.
- [styles.css](plotly-dash-picroscope-control-console/assets/styles.css.md) — Comprehensive stylesheet for the Picroscope Dash control console, styling grid structures, typography, buttons, tabs, input controls, and Plotly graph containers.
- [callbacks.py](plotly-dash-picroscope-control-console/callbacks.py.md) — Defines core Dash UI callbacks and database interactions for the Picroscope console, managing GitHub repository issue creation, MQTT message publishing, and device shadow queries.

## 10. service-accounts
Project scripts; see per-file summaries.

**Entry points (full tier):** [service-accounts.app.token_service](service-accounts/app/token_service.py.md)

**Supporting files:**
- [token_service.py](service-accounts/app/token_service.py.md) — Flask microservice providing HTTP endpoints (`/token`, `/healthz`) to mint long-lived Auth0 service account JWT tokens for automated jobs and machine-to-machine integrations.

## 11. shadows_vue
Project scripts; see per-file summaries.

**Entry points (full tier):** library-style components below

**Supporting files:**
- [babel.config.js](shadows_vue/babel.config.js.md) — Babel transpiler configuration for the Shadows Vue.js web application using `@vue/cli-plugin-babel/preset`.
- [index.html](shadows_vue/public/index.html.md) — HTML entry point template for the Shadows Vue single-page application, mounting root `#app` container and defining meta viewport and favicon.
- [styles.css](shadows_vue/src/assets/css/styles.css.md) — Root stylesheet for the Shadows Vue application declaring Tailwind CSS base, component, and utility layers.
- [auth0-plugin.js](shadows_vue/src/auth/auth0-plugin.js.md) — Vue.js authentication wrapper plugin around `@auth0/auth0-spa-js`, managing user authentication state, login redirect/popup flows, token retrieval, and route guards.
- [main.js](shadows_vue/src/main.js.md) — Application bootstrap entry point for the Shadows Vue web client, installing BootstrapVue, VueRouter, VueEllipseProgress, VueLuxon plugins and mounting `App.vue`.
- [index.js](shadows_vue/src/router/index.js.md) — Vue Router configuration for the Shadows web application, establishing client routes for Plates, Wells, Experiments, Devices, Search Results, and Auth0 login redirects with navigation guards.
- [vue.config.js](shadows_vue/vue.config.js.md) — Vue CLI configuration defining sub-path routing (`publicPath: '/datahub/'`), output distribution path (`./dist/datahub/`), and dependency transpilation settings.

## 12. skills
Project scripts; see per-file summaries.

**Entry points (full tier):** [skills.braingeneers-one.scripts._vendor.yaml.constructor](skills/braingeneers-one/scripts/_vendor/yaml/constructor.py.md), [skills.braingeneers-one.scripts._vendor.yaml.representer](skills/braingeneers-one/scripts/_vendor/yaml/representer.py.md), [skills.braingeneers-one.scripts._vendor.yaml.resolver](skills/braingeneers-one/scripts/_vendor/yaml/resolver.py.md), [skills.braingeneers-one.scripts.suite](skills/braingeneers-one/scripts/suite.py.md), [skills.mission-control-services-management.scripts.authenticate](skills/mission-control-services-management/scripts/authenticate.py.md), [skills.nrp-cluster.references.memory_peak](skills/nrp-cluster/references/memory_peak.py.md)

**Supporting files:**
- [__init__.py](skills/braingeneers-one/scripts/_vendor/yaml/__init__.py.md) — Vendored PyYAML package root providing public serialization and deserialization APIs (`load`, `safe_load`, `dump`, `safe_dump`, `scan`, `parse`, `compose`).
- [composer.py](skills/braingeneers-one/scripts/_vendor/yaml/composer.py.md) — PyYAML composer module building abstract syntax representation trees (`Node`, `ScalarNode`, `SequenceNode`, `MappingNode`) from parser event streams.
- [constructor.py](skills/braingeneers-one/scripts/_vendor/yaml/constructor.py.md) — PyYAML constructor engine transforming abstract representation nodes (`MappingNode`, `SequenceNode`, `ScalarNode`) into native Python objects, mappings, lists, and primitives.
- [dumper.py](skills/braingeneers-one/scripts/_vendor/yaml/dumper.py.md) — PyYAML dumper composite classes uniting emitter, serializer, representer, and resolver components to serialize Python objects into YAML streams.
- [emitter.py](skills/braingeneers-one/scripts/_vendor/yaml/emitter.py.md) — Low-level YAML character stream emitter formatting parser events into formatted text with proper indentation, line wrapping, block/flow collection styles, and scalar quoting.
- [error.py](skills/braingeneers-one/scripts/_vendor/yaml/error.py.md) — Defines base exception hierarchy and source location marker (`Mark`) tracking line, column, snippet, and buffer index for precise YAML diagnostic messages.
- [events.py](skills/braingeneers-one/scripts/_vendor/yaml/events.py.md) — Defines parser and emitter event data classes representing the abstract syntactic event stream between the parser/scanner and composer/emitter.
- [loader.py](skills/braingeneers-one/scripts/_vendor/yaml/loader.py.md) — Defines composite loader classes (`BaseLoader`, `FullLoader`, `SafeLoader`, `Loader`, `UnsafeLoader`) combining reader, scanner, parser, composer, constructor, and resolver components.
- [nodes.py](skills/braingeneers-one/scripts/_vendor/yaml/nodes.py.md) — Defines abstract syntax graph representation node classes (`Node`, `ScalarNode`, `SequenceNode`, `MappingNode`) used between composition and construction.
- [parser.py](skills/braingeneers-one/scripts/_vendor/yaml/parser.py.md) — Recursive descent event-driven parser transforming token streams from the scanner into high-level parsing events according to YAML grammar productions.
- [reader.py](skills/braingeneers-one/scripts/_vendor/yaml/reader.py.md) — Unicode input stream reader handling byte decoding, BOM detection, character filtering, lookahead buffering, and coordinate tracking (index, line, column).
- [representer.py](skills/braingeneers-one/scripts/_vendor/yaml/representer.py.md) — PyYAML representer engine converting native Python objects, containers, and primitives into abstract representation node trees.
- [resolver.py](skills/braingeneers-one/scripts/_vendor/yaml/resolver.py.md) — Implicit tag resolution engine using compiled regular expression tables to determine data types (bool, int, float, null, timestamp) for untagged plain scalars.
- [scanner.py](skills/braingeneers-one/scripts/_vendor/yaml/scanner.py.md) — Low-level lexical tokenizer and scanner scanning Unicode character streams into YAML tokens (directives, document markers, block/flow collections, keys, values, and scalars).
- [serializer.py](skills/braingeneers-one/scripts/_vendor/yaml/serializer.py.md) — Serializes representation node graphs (`Node`, `MappingNode`, `SequenceNode`) into linearized event streams (`events.py`) with document boundaries and anchor alias references.
- [tokens.py](skills/braingeneers-one/scripts/_vendor/yaml/tokens.py.md) — Defines lexical token data classes generated by the scanner to represent lexical YAML primitives (directives, stream/document boundaries, block/flow delimiters, keys, values, and scalars).
- [suite.py](skills/braingeneers-one/scripts/suite.py.md) — Catalog maintenance and verification script for Braingeneers skills, tracking GitHub tree SHAs, fingerprints, and frontmatter metadata without running lab operations.
- [authenticate.py](skills/mission-control-services-management/scripts/authenticate.py.md) — CLI utility for managing local Braingeneers service credentials, validating JWT token structure and expiration, opening browser sign-in if needed, and saving tokens with restrictive file permissions.
- [memory_peak.py](skills/nrp-cluster/references/memory_peak.py.md) — Process wrapper script that executes an arbitrary child command, measures cgroup v1/v2 memory peak usage upon exit, preserves exit status, and records memory metrics into a done JSON file.

## 13. slack-bridge
Project scripts; see per-file summaries.

**Entry points (full tier):** [slack-bridge.slack_bridge](slack-bridge/slack_bridge.py.md)

**Supporting files:**
- [slack_bridge.py](slack-bridge/slack_bridge.py.md) — Flask and MQTT bidirectional bridge microservice routing telemetry alerts and hardware messages from Braingeneers MQTT message broker to Slack channels, and forwarding Slack interactive events back to MQTT.

## 14. smartplug-dash
Project scripts; see per-file summaries.

**Entry points (full tier):** [smartplug-dash.smartplug-dashboard](smartplug-dash/smartplug-dashboard.py.md)

**Supporting files:**
- [smartplug-dashboard.py](smartplug-dash/smartplug-dashboard.py.md) — Streamlit dashboard application for discovering, monitoring, and toggling power state of Tasmota smart plugs connected to the Braingeneers laboratory MQTT network.

## 15. strapi-shadows-db
Project scripts; see per-file summaries.

**Entry points (full tier):** library-style components below

**Supporting files:**
- [admin.js](strapi-shadows-db/config/admin.js.md) — Strapi admin panel authentication configuration loading administrator JWT signing secret and API token salt from environment variables.
- [api.js](strapi-shadows-db/config/api.js.md) — Strapi REST API pagination and query configuration setting default and maximum record limits to 100 with total count inclusion.
- [database.js](strapi-shadows-db/config/database.js.md) — Strapi database client configuration setting SQLite as the connection engine and resolving database file path from environment variables.
- [middlewares.js](strapi-shadows-db/config/middlewares.js.md) — Strapi middleware pipeline array configuring error handling, security headers, CORS, request logging, query parsing, body parsing, and session state.
- [plugins.js](strapi-shadows-db/config/plugins.js.md) — Strapi plugin configuration enabling fuzzy search integration across laboratory data models (experiments, plates, samples, and wells).
- [server.js](strapi-shadows-db/config/server.js.md) — Strapi HTTP server configuration defining host, port, external public URL (`https://shadows-db.braingeneers.gi.ucsc.edu/`), proxy trust, and session secret keys.
- [app.example.js](strapi-shadows-db/src/admin/app.example.js.md) — Example template configuration for customizing the Strapi admin UI panel, including internationalization locale configuration and admin bootstrap hook.
- [webpack.config.example.js](strapi-shadows-db/src/admin/webpack.config.example.js.md) — Example template for customizing Webpack compilation options used when building the Strapi admin panel frontend.
- [experiment.js](strapi-shadows-db/src/api/experiment/controllers/experiment.js.md) — Strapi core controller for the Experiment content type generated via `@strapi/strapi` factories, handling CRUD HTTP requests for laboratory experiments.
- [experiment.js](strapi-shadows-db/src/api/experiment/routes/experiment.js.md) — Strapi core router configuration for the Experiment content type defining REST API routes for experiment records.
- [experiment.js](strapi-shadows-db/src/api/experiment/services/experiment.js.md) — Strapi core service for the Experiment content type providing business logic and database queries for laboratory experiment records.
- [interaction-thing.js](strapi-shadows-db/src/api/interaction-thing/controllers/interaction-thing.js.md) — Strapi core controller for the Interaction Thing content type, handling CRUD operations for IoT laboratory hardware interaction targets.
- [interaction-thing.js](strapi-shadows-db/src/api/interaction-thing/routes/interaction-thing.js.md) — Strapi core router configuration for the Interaction Thing content type, defining REST endpoints for hardware interaction entities.
- [interaction-thing.js](strapi-shadows-db/src/api/interaction-thing/services/interaction-thing.js.md) — Strapi core service for the Interaction Thing content type, managing persistence and business logic for IoT interaction devices.
- [plate.js](strapi-shadows-db/src/api/plate/controllers/plate.js.md) — Strapi core controller for the Plate content type, handling HTTP requests for multi-well experimental cell culture plates.
- [plate.js](strapi-shadows-db/src/api/plate/routes/plate.js.md) — Strapi core router for the Plate content type, configuring REST API routing for cell culture plates.
- [plate.js](strapi-shadows-db/src/api/plate/services/plate.js.md) — Strapi core service for the Plate content type, implementing database queries and business logic for multi-well plates.
- [sample.js](strapi-shadows-db/src/api/sample/controllers/sample.js.md) — Strapi core controller for the Sample content type, handling HTTP requests for biological organoid cell samples.
- [sample.js](strapi-shadows-db/src/api/sample/routes/sample.js.md) — Strapi core router configuration for the Sample content type, exposing REST API routes for organoid samples.
- [sample.js](strapi-shadows-db/src/api/sample/services/sample.js.md) — Strapi core service for the Sample content type, managing data queries and persistence logic for cell culture samples.
- [well.js](strapi-shadows-db/src/api/well/controllers/well.js.md) — Strapi core controller for the Well content type, handling HTTP requests for individual plate wells (position, media, organoid contents).
- [well.js](strapi-shadows-db/src/api/well/routes/well.js.md) — Strapi core router configuration for the Well content type, exposing REST endpoints for well records.
- [well.js](strapi-shadows-db/src/api/well/services/well.js.md) — Strapi core service for the Well content type, managing database operations and relations for plate well records.
- [index.js](strapi-shadows-db/src/index.js.md) — Strapi application lifecycle root module providing extension lifecycle hooks (`register` and `bootstrap`) called during server startup.
