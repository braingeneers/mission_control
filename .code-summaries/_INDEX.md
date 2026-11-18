# Code summaries

Generated: 2026-11-18 | commit: 775a1d79c860b23ddbbf59f5a1ddd1dfc237b3b7 | mode: all

83 file summaries (83 full, 0 brief); 0 package markers. Scope: all project directories except known holes.

Use `_FEATURES.md` for behavior, `_GRAPH.md` for import consumers. Check freshness with the helper before relying on summaries.
`brief` summaries (figure/scratch scripts) have a reviewed overview plus AST facts only; read source for details.

## Directory tree
```text
data-lifecycle/
  skills/
    backup-reprocess-check/
      scripts/
  src/
docker-maintenance/
experiment-dash/
  assets/
job-h5repack/
logging-s3/
logging-s3-aggregator/
nginx-reverse-proxy/
  static/
oauth2-proxy/
plotly-dash-picroscope-control-console/
  app_elements/
  assets/
service-accounts/
  app/
shadows_vue/
  public/
  src/
    assets/
      css/
    auth/
    router/
skills/
  braingeneers-one/
    scripts/
      _vendor/
        yaml/
  mission-control-services-management/
    scripts/
  nrp-cluster/
    references/
slack-bridge/
smartplug-dash/
strapi-shadows-db/
  config/
  src/
    admin/
    api/
      experiment/
        controllers/
        routes/
        services/
      interaction-thing/
        controllers/
        routes/
        services/
      plate/
        controllers/
        routes/
        services/
      sample/
        controllers/
        routes/
        services/
      well/
        controllers/
        routes/
        services/
```

## data-lifecycle/skills/backup-reprocess-check/scripts
- [analyze_two_run_check.py](data-lifecycle/skills/backup-reprocess-check/scripts/analyze_two_run_check.py.md) — Analyzes and compares two consecutive backup pipeline execution runs (Run 1 and Run 2) to detect anomalies, regressions, missing source objects, duplicate puts, and activity discrepancies. Symbols: MISSING_SOURCE_RE, RunSummary, SOURCE_ACCESS_ISSUE, SOURCE_ERROR_MARKERS, SUMMARY_MISSING_SOURCE_RE, analyze, artifact_line, build_report, duplicates, interesting_log_lines, load_run, main, manifest_uri, md_list, parse_args, parse_missing_sources, read_activity, read_badkeys, read_json, read_lines, … (+5).
- [run_two_run_check.py](data-lifecycle/skills/backup-reprocess-check/scripts/run_two_run_check.py.md) — Orchestrates two consecutive containerized backup pipeline execution runs against S3/Glacier inventory manifests to verify idempotent reprocessing and differential correctness. Symbols: DATE_RE, DEFAULT_BUCKET, DEFAULT_PREFIX, DEFAULT_PROFILE, REPO_ROOT, SCRIPT_DIR, analyze, build_image, head_manifest, latest_manifest_date, main, manifest_key, manifest_uri, next_manifest_date, parse_args, parse_manifest_uri, run_backup_once, run_command, utc_now, utc_stamp, … (+2).

## data-lifecycle/src
- [badkeys.py](data-lifecycle/src/badkeys.py.md) — Defines data models, serialization utilities, and Slack formatting for recording problematic S3 bucket keys (control characters, unicode escaping, and HeadObject success followed by GetObject failure). Symbols: BadKeyRecord, CONTROL_CHARACTER_ISSUE, ISSUE_DESCRIPTIONS, SOURCE_GET_FAILED_AFTER_HEAD_SUCCESS, append_source_get_failed_slack_section, dedupe_badkey_records, describe_issue, escape_bucket_key, make_badkey_record, merge_badkey_records, parse_badkeys_tsv_text, read_badkeys_tsv, render_source_get_failed_slack_section, source_get_failed_records, unescape_bucket_key, write_badkeys_tsv.
- [generate_cleanup_report.py](data-lifecycle/src/generate_cleanup_report.py.md) — Generates the monthly data-retention report bundle including interactive HTML, multipage PDF summary charts, Slack notification payload, and retention candidate CSV from scientific and backup inventories. Symbols: MAX_PDF_CANDIDATES, MAX_SLACK_TEXT_CHARS, PDF_INK, PDF_MUTED, PDF_NAVY, PDF_ORANGE, PDF_PALE, PDF_ROWS_PER_PAGE, PDF_RULE, PDF_TEAL, SOURCE_IDS, _candidate_path_parts, _candidate_source, _display_date, _iso, _object_count_label, _pdf_footer, _shorten_middle, _slack_link, _slack_text, … (+11).
- [generate_puts_deletes.py](data-lifecycle/src/generate_puts_deletes.py.md) — Stage 3 comparison engine comparing Ceph/NRP scientific storage inventory against Glacier backup inventory; generates put lists for unbacked files, delete lists for expired files per policy, and badkeys lists. Symbols: CONTROL_CHAR_PATTERN, DEFAULT_PROGRESS_INTERVAL_SECONDS, Stage3ProgressReporter, apply_last_modified_updates, build_cleanup_slack_message, build_cleanup_summary, build_cleanup_window_entries, build_comparison_summary, calculate_expire_date, derive_atomic_group_info, derive_folder_group, find_no_backup_prefixes, generate_put_and_delete_lists, get_required_config_value, load_config_file, load_inventories, main, output_puts_deletes_and_notifications, parse_arguments, parse_days, … (+2).
- [glacier_cost_analysis_plot.py](data-lifecycle/src/glacier_cost_analysis_plot.py.md) — Plots estimated AWS Glacier storage costs vs retention policy duration in years, computing cumulative retained volumes and projecting monthly expenses from Ceph/S3 inventory files. Symbols: DEFAULT_COST_PER_GB_MONTH, DEFAULT_INVENTORY_S3_URI, DEFAULT_NRP_ENDPOINT, DEFAULT_OUTPUT_CSV, DEFAULT_OUTPUT_PNG, DEFAULT_PER_OBJECT_OVERHEAD_BYTES, DEFAULT_POLICY_CONFIG, InventorySummary, RetentionPoint, build_retention_points, coerce_as_of_date, compute_single_retention_point, download_inventory_from_s3, fmt_tib, fmt_usd, list_inventory_candidates, load_cold_storage_expire_days, main, make_s3_client, open_inventory_text, … (+8).
- [lifecycle_constants.py](data-lifecycle/src/lifecycle_constants.py.md) — Defines reserved constant object names and marker suffixes for the Braingeneers data lifecycle retention management subsystem. Symbols: FILE_RETENTION_SUFFIX, NOBACKUP_MARKER_NAME, RETENTION_MARKER_NAME.
- [lifecycle_controls.py](data-lifecycle/src/lifecycle_controls.py.md) — Implements control-object semantics for dataset retention, parsing zero-byte marker objects for atomic directories and individual files to compute effective last-modified dates. Symbols: apply_effective_last_modified, atomic_group_for_key, atomic_retention_marker, file_retention_marker, is_lifecycle_control_key, is_nobackup_marker, is_retention_marker, lifecycle_control_mask, marker_upload_mask, normalize_atomic_directories, retention_marker_mask, retention_marker_target, scientific_inventory.
- [stage4_keys.py](data-lifecycle/src/stage4_keys.py.md) — Provides S3 object key sanitization, URL decoding, rclone special dot-segment normalization, and source lookup candidate generation for Stage 4 backup transfers. Symbols: EMBEDDED_S3_SCHEME_CANONICAL_RE, EMBEDDED_S3_SCHEME_RE, RCLONE_DOT_DOT_SEGMENT, RCLONE_DOT_SEGMENT, build_source_lookup_candidates, collapse_embedded_s3_scheme, denormalize_rclone_dot_segments, load_put_keys, normalize_bucket_object_key, normalize_object_key, normalize_put_key, normalize_rclone_dot_segments, restore_embedded_s3_scheme.
- [stage4_process_puts_deletes.py](data-lifecycle/src/stage4_process_puts_deletes.py.md) — Stage 4 parallel execution engine streaming object backups from Ceph/NRP S3 to AWS Glacier S3 using smart-open multipart streams, retry logic, error classification, and progress logging. Symbols: AWS_PROFILE, ActivityLogger, COPY_CHUNK_BYTES, DEFAULT_AWS_MAX_ATTEMPTS, DEFAULT_AWS_MAX_POOL_CONNECTIONS, DEFAULT_AWS_REGION, DEFAULT_AWS_RETRY_MODE, DEFAULT_MAX_PENDING_TASKS, DEFAULT_NRP_ENDPOINT, DEFAULT_PROGRESS_INTERVAL_SECONDS, DEFAULT_PROGRESS_STALL_ALERT_SECONDS, DEFAULT_RETRIES, DEFAULT_RETRY_BASE_SECONDS, DEFAULT_RETRY_MAX_SECONDS, DEFAULT_WORKERS, EXIT_STAGE4_PUTS_LOAD_FAILURE, EXIT_STAGE4_RUNTIME_FAILURE, EXIT_STAGE4_UPLOAD_FRACTION_GUARD, EXIT_SUCCESS, GLACIER_BUCKET, … (+32).
- [stage4_upload_poc.py](data-lifecycle/src/stage4_upload_poc.py.md) — Proof-of-concept benchmarking script comparing throughput and memory consumption across smart-open, AWS CLI, and rclone for streaming large dataset uploads to Glacier. Symbols: DEFAULT_AWS_PROFILE, DEFAULT_AWS_REGION, DEFAULT_CHUNK_SIZE_MIB, DEFAULT_MULTIPART_UPLOAD, DEFAULT_PART_SIZE_MIB, DEFAULT_RCLONE_CHUNK_SIZE_MIB, DEFAULT_RCLONE_DISABLE_CHECKSUM, DEFAULT_RCLONE_S3_PROVIDER, DEFAULT_RCLONE_UPLOAD_CONCURRENCY, DEFAULT_RCLONE_USE_PRESIGNED_REQUEST, DEFAULT_RCLONE_USE_UNSIGNED_PAYLOAD, DEFAULT_UPLOADER, build_client, main, parse_args, parse_s3_url, upload_with_aws_cli, upload_with_rclone, upload_with_smart_open.

## docker-maintenance
- [maintenance.py](docker-maintenance/maintenance.py.md) — Autonomous maintenance daemon managing Docker daemon storage: periodically prunes dangling images and builder cache, monitors disk thresholds, and issues Slack alerts on critical disk fill. Symbols: Config, DAY, GIB, HOUR, INTERVAL, LOG, Maintenance, NoRedirect, State, disk_critical, docker, health_reasons, load_state, main, measure_disk, notify, observe_daemon, prune_images, save_state.

## experiment-dash
- [dashboard_helpers.py](experiment-dash/dashboard_helpers.py.md) — Helper library for the telemetry experiment dashboard, constructing MQTT topic strings and publishing commands (start, end, ping, pause, resume, stop, sched) to Braingeneers IoT devices. Symbols: ROOT_TOPIC, check_uuid_format, command, create_uuid, end, generate_topic, logging_token, mb, pause, ping, resume, s3_basepath, sched_add, sched_clear, send_message, send_to_all_teammates, start, status, stop.
- [experiment-plotly-app.py](experiment-dash/experiment-plotly-app.py.md) — Plotly Dash interactive web application for monitoring and controlling wet lab organoid experiments, device telemetry, status checks, and scheduling. Symbols: allow_duplicate, app, handle_command_button, handle_end_button, handle_pause_button, handle_ping_button, handle_resume_button, handle_sched_add_button, handle_sched_clear_button, handle_start_end_button, handle_status_button, handle_stop_button, load_json, populate_device_checklist, toggle_collapse, update_device_states, update_output, update_time, update_value.

## experiment-dash/assets
- [style.css](experiment-dash/assets/style.css.md) — Custom stylesheet for the experiment telemetry Plotly Dash application, styling container layout, cards, and hiding Dash debug menus. Symbols: module-level code.

## job-h5repack
- [get_task.py](job-h5repack/get_task.py.md) — Worker task dequeue script for h5repack batch processing; fetches the next electrophysiology HDF5 data file from an MQTT message queue. Symbols: q, queue_name, uuid.
- [init.py](job-h5repack/init.py.md) — Initialization CLI script for electrophysiology h5repack jobs, reading dataset metadata from S3 and populating an MQTT message queue with data files to repack. Symbols: main.
- [update_metadata.py](job-h5repack/update_metadata.py.md) — Post-processing task updater acquiring an S3 distributed lock to update electrophysiology experiment metadata when an HDF5 file has been converted to row-major layout. Symbols: main, save_metadata.

## logging-s3
- [log.py](logging-s3/log.py.md) — Telemetry daemon listening indefinitely to MQTT topic `telemetry/#` and streaming individual message payloads to S3 as single-message TSV files. Symbols: main.

## logging-s3-aggregator
- [log_aggregator.py](logging-s3-aggregator/log_aggregator.py.md) — Periodic aggregation service that scans singleton S3 telemetry log files, combines up to 100 entries per batch into cumulative log TSVs, and deletes processed singles. Symbols: batch_100_logs, combine_logs, delete_s3_object, format_log_entries, log_to_stderr, main, s3_client.

## nginx-reverse-proxy/static
- [index.html](nginx-reverse-proxy/static/index.html.md) — Static landing page served by Nginx reverse proxy presenting user login prompt and redirect button for CILogon OAuth authentication. Symbols: module-level code.

## oauth2-proxy
- [error.html](oauth2-proxy/error.html.md) — Custom error template for oauth2-proxy displaying authentication failure explanations, Auth0 role requirements, and Slack #helpdesk troubleshooting guidance. Symbols: module-level code.

## plotly-dash-picroscope-control-console
- [Experiment_Metadata_SQL.py](plotly-dash-picroscope-control-console/Experiment_Metadata_SQL.py.md) — Database query interface module intended for retrieving experiment metadata and device shadow state from SQLite databases. Symbols: module-level code.
- [app.py](plotly-dash-picroscope-control-console/app.py.md) — Main web application server for the Picroscope microscope control console, assembling Dash tabs for experiment controls, imaging parameters, and livestream feeds. Symbols: app, base_path.
- [callbacks.py](plotly-dash-picroscope-control-console/callbacks.py.md) — Defines core Dash UI callbacks and database interactions for the Picroscope console, managing GitHub repository issue creation, MQTT message publishing, and device shadow queries. Symbols: brokerString, db_interactor, endpoint, get_callbacks, gh, mb, repo, shadows_api_key.

## plotly-dash-picroscope-control-console/app_elements
- [experiment_panel.py](plotly-dash-picroscope-control-console/app_elements/experiment_panel.py.md) — Defines the experiment setup and metadata management UI tab layout for the Picroscope console, including forms for researchers, organoid lines, and imaging schedules. Symbols: EXPERIMENT_PANEL, get_callbacks.
- [imaging_panel.py](plotly-dash-picroscope-control-console/app_elements/imaging_panel.py.md) — Defines the camera exposure, focus, stage position, and multi-well plate imaging parameter control panel UI tab for the Picroscope console. Symbols: IMAGING_PANEL, alert, base_path, url.
- [livestream_panel.py](plotly-dash-picroscope-control-console/app_elements/livestream_panel.py.md) — Defines the real-time optical livestream viewer tab for the Picroscope console, embedding video streams and current capture previews from active microscopes. Symbols: LIVESTREAM_PANEL.

## plotly-dash-picroscope-control-console/assets
- [resizing_script.js](plotly-dash-picroscope-control-console/assets/resizing_script.js.md) — Clientside JavaScript callback helper for the Picroscope Dash console, triggering window resize events after a timeout to force responsive Plotly charts to recalculate dimensions. Symbols: resize.
- [styles.css](plotly-dash-picroscope-control-console/assets/styles.css.md) — Comprehensive stylesheet for the Picroscope Dash control console, styling grid structures, typography, buttons, tabs, input controls, and Plotly graph containers. Symbols: module-level code.

## service-accounts/app
- [token_service.py](service-accounts/app/token_service.py.md) — Flask microservice providing HTTP endpoints (`/token`, `/healthz`) to mint long-lived Auth0 service account JWT tokens for automated jobs and machine-to-machine integrations. Symbols: AUTH0_API_AUDIENCE, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_DOMAIN, DEFAULT_SERVICE_ACCOUNT_EXPIRATION_DAYS, _format_utc, _json_response, _parse_requested_days, _service_account_token, _utcnow, app, generate_token, healthz.

## shadows_vue
- [babel.config.js](shadows_vue/babel.config.js.md) — Babel transpiler configuration for the Shadows Vue.js web application using `@vue/cli-plugin-babel/preset`. Symbols: module-level code.
- [vue.config.js](shadows_vue/vue.config.js.md) — Vue CLI configuration defining sub-path routing (`publicPath: '/datahub/'`), output distribution path (`./dist/datahub/`), and dependency transpilation settings. Symbols: defineConfig.

## shadows_vue/public
- [index.html](shadows_vue/public/index.html.md) — HTML entry point template for the Shadows Vue single-page application, mounting root `#app` container and defining meta viewport and favicon. Symbols: module-level code.

## shadows_vue/src
- [main.js](shadows_vue/src/main.js.md) — Application bootstrap entry point for the Shadows Vue web client, installing BootstrapVue, VueRouter, VueEllipseProgress, VueLuxon plugins and mounting `App.vue`. Symbols: module-level code.

## shadows_vue/src/assets/css
- [styles.css](shadows_vue/src/assets/css/styles.css.md) — Root stylesheet for the Shadows Vue application declaring Tailwind CSS base, component, and utility layers. Symbols: module-level code.

## shadows_vue/src/auth
- [auth0-plugin.js](shadows_vue/src/auth/auth0-plugin.js.md) — Vue.js authentication wrapper plugin around `@auth0/auth0-spa-js`, managing user authentication state, login redirect/popup flows, token retrieval, and route guards. Symbols: getIdTokenClaims, getTokenSilently, loginWithRedirect, logout, useAuth0.

## shadows_vue/src/router
- [index.js](shadows_vue/src/router/index.js.md) — Vue Router configuration for the Shadows web application, establishing client routes for Plates, Wells, Experiments, Devices, Search Results, and Auth0 login redirects with navigation guards. Symbols: module-level code.

## skills/braingeneers-one/scripts
- [suite.py](skills/braingeneers-one/scripts/suite.py.md) — Catalog maintenance and verification script for Braingeneers skills, tracking GitHub tree SHAs, fingerprints, and frontmatter metadata without running lab operations. Symbols: Failure, ONE, Suite, TRACKING, _previous_dont_write_bytecode, _yaml_spec, api, blob_sha, command, files_at, fingerprint, frontmatter, load_catalog, main, without_tracking, yaml.

## skills/braingeneers-one/scripts/_vendor/yaml
- [__init__.py](skills/braingeneers-one/scripts/_vendor/yaml/__init__.py.md) — Vendored PyYAML package root providing public serialization and deserialization APIs (`load`, `safe_load`, `dump`, `safe_dump`, `scan`, `parse`, `compose`). Symbols: YAMLObject, YAMLObjectMetaclass, __version__, add_constructor, add_implicit_resolver, add_multi_constructor, add_multi_representer, add_path_resolver, add_representer, compose, compose_all, dump, dump_all, emit, full_load, full_load_all, load, load_all, parse, safe_dump, … (+9).
- [composer.py](skills/braingeneers-one/scripts/_vendor/yaml/composer.py.md) — PyYAML composer module building abstract syntax representation trees (`Node`, `ScalarNode`, `SequenceNode`, `MappingNode`) from parser event streams. Symbols: Composer, ComposerError, __all__.
- [constructor.py](skills/braingeneers-one/scripts/_vendor/yaml/constructor.py.md) — PyYAML constructor engine transforming abstract representation nodes (`MappingNode`, `SequenceNode`, `ScalarNode`) into native Python objects, mappings, lists, and primitives. Symbols: BaseConstructor, Constructor, ConstructorError, FullConstructor, SafeConstructor, UnsafeConstructor, __all__.
- [dumper.py](skills/braingeneers-one/scripts/_vendor/yaml/dumper.py.md) — PyYAML dumper composite classes uniting emitter, serializer, representer, and resolver components to serialize Python objects into YAML streams. Symbols: BaseDumper, Dumper, SafeDumper, __all__.
- [emitter.py](skills/braingeneers-one/scripts/_vendor/yaml/emitter.py.md) — Low-level YAML character stream emitter formatting parser events into formatted text with proper indentation, line wrapping, block/flow collection styles, and scalar quoting. Symbols: Emitter, EmitterError, ScalarAnalysis, __all__.
- [error.py](skills/braingeneers-one/scripts/_vendor/yaml/error.py.md) — Defines base exception hierarchy and source location marker (`Mark`) tracking line, column, snippet, and buffer index for precise YAML diagnostic messages. Symbols: Mark, MarkedYAMLError, YAMLError, __all__.
- [events.py](skills/braingeneers-one/scripts/_vendor/yaml/events.py.md) — Defines parser and emitter event data classes representing the abstract syntactic event stream between the parser/scanner and composer/emitter. Symbols: AliasEvent, CollectionEndEvent, CollectionStartEvent, DocumentEndEvent, DocumentStartEvent, Event, MappingEndEvent, MappingStartEvent, NodeEvent, ScalarEvent, SequenceEndEvent, SequenceStartEvent, StreamEndEvent, StreamStartEvent.
- [loader.py](skills/braingeneers-one/scripts/_vendor/yaml/loader.py.md) — Defines composite loader classes (`BaseLoader`, `FullLoader`, `SafeLoader`, `Loader`, `UnsafeLoader`) combining reader, scanner, parser, composer, constructor, and resolver components. Symbols: BaseLoader, FullLoader, Loader, SafeLoader, UnsafeLoader, __all__.
- [nodes.py](skills/braingeneers-one/scripts/_vendor/yaml/nodes.py.md) — Defines abstract syntax graph representation node classes (`Node`, `ScalarNode`, `SequenceNode`, `MappingNode`) used between composition and construction. Symbols: CollectionNode, MappingNode, Node, ScalarNode, SequenceNode.
- [parser.py](skills/braingeneers-one/scripts/_vendor/yaml/parser.py.md) — Recursive descent event-driven parser transforming token streams from the scanner into high-level parsing events according to YAML grammar productions. Symbols: Parser, ParserError, __all__.
- [reader.py](skills/braingeneers-one/scripts/_vendor/yaml/reader.py.md) — Unicode input stream reader handling byte decoding, BOM detection, character filtering, lookahead buffering, and coordinate tracking (index, line, column). Symbols: Reader, ReaderError, __all__.
- [representer.py](skills/braingeneers-one/scripts/_vendor/yaml/representer.py.md) — PyYAML representer engine converting native Python objects, containers, and primitives into abstract representation node trees. Symbols: BaseRepresenter, Representer, RepresenterError, SafeRepresenter, __all__.
- [resolver.py](skills/braingeneers-one/scripts/_vendor/yaml/resolver.py.md) — Implicit tag resolution engine using compiled regular expression tables to determine data types (bool, int, float, null, timestamp) for untagged plain scalars. Symbols: BaseResolver, Resolver, ResolverError, __all__.
- [scanner.py](skills/braingeneers-one/scripts/_vendor/yaml/scanner.py.md) — Low-level lexical tokenizer and scanner scanning Unicode character streams into YAML tokens (directives, document markers, block/flow collections, keys, values, and scalars). Symbols: Scanner, ScannerError, SimpleKey, __all__.
- [serializer.py](skills/braingeneers-one/scripts/_vendor/yaml/serializer.py.md) — Serializes representation node graphs (`Node`, `MappingNode`, `SequenceNode`) into linearized event streams (`events.py`) with document boundaries and anchor alias references. Symbols: Serializer, SerializerError, __all__.
- [tokens.py](skills/braingeneers-one/scripts/_vendor/yaml/tokens.py.md) — Defines lexical token data classes generated by the scanner to represent lexical YAML primitives (directives, stream/document boundaries, block/flow delimiters, keys, values, and scalars). Symbols: AliasToken, AnchorToken, BlockEndToken, BlockEntryToken, BlockMappingStartToken, BlockSequenceStartToken, DirectiveToken, DocumentEndToken, DocumentStartToken, FlowEntryToken, FlowMappingEndToken, FlowMappingStartToken, FlowSequenceEndToken, FlowSequenceStartToken, KeyToken, ScalarToken, StreamEndToken, StreamStartToken, TagToken, Token, … (+1).

## skills/mission-control-services-management/scripts
- [authenticate.py](skills/mission-control-services-management/scripts/authenticate.py.md) — CLI utility for managing local Braingeneers service credentials, validating JWT token structure and expiration, opening browser sign-in if needed, and saving tokens with restrictive file permissions. Symbols: LOGIN_URL, MAX_RESPONSE, SignInError, check_response, collect_response, load_response, main, read_private_response, save_response, select_path, validate_response.

## skills/nrp-cluster/references
- [memory_peak.py](skills/nrp-cluster/references/memory_peak.py.md) — Process wrapper script that executes an arbitrary child command, measures cgroup v1/v2 memory peak usage upon exit, preserves exit status, and records memory metrics into a done JSON file. Symbols: main, measure.

## slack-bridge
- [slack_bridge.py](slack-bridge/slack_bridge.py.md) — Flask and MQTT bidirectional bridge microservice routing telemetry alerts and hardware messages from Braingeneers MQTT message broker to Slack channels, and forwarding Slack interactive events back to MQTT. Symbols: _graceful_shutdown, _handler, _post_message_with_retry, _retry_after, _upload_file_with_retry, app, config, get_channel_name, handle_slack_event, healthz, mb, mqtt_to_slack_callback, safe_publish, shutdown_flag, slack_client, slack_signing_secret, slack_token.

## smartplug-dash
- [smartplug-dashboard.py](smartplug-dash/smartplug-dashboard.py.md) — Streamlit dashboard application for discovering, monitoring, and toggling power state of Tasmota smart plugs connected to the Braingeneers laboratory MQTT network. Symbols: smartplug, smartplugs_list, toggle_smartplugs.

## strapi-shadows-db/config
- [admin.js](strapi-shadows-db/config/admin.js.md) — Strapi admin panel authentication configuration loading administrator JWT signing secret and API token salt from environment variables. Symbols: module-level code.
- [api.js](strapi-shadows-db/config/api.js.md) — Strapi REST API pagination and query configuration setting default and maximum record limits to 100 with total count inclusion. Symbols: module-level code.
- [database.js](strapi-shadows-db/config/database.js.md) — Strapi database client configuration setting SQLite as the connection engine and resolving database file path from environment variables. Symbols: module-level code.
- [middlewares.js](strapi-shadows-db/config/middlewares.js.md) — Strapi middleware pipeline array configuring error handling, security headers, CORS, request logging, query parsing, body parsing, and session state. Symbols: module-level code.
- [plugins.js](strapi-shadows-db/config/plugins.js.md) — Strapi plugin configuration enabling fuzzy search integration across laboratory data models (experiments, plates, samples, and wells). Symbols: module-level code.
- [server.js](strapi-shadows-db/config/server.js.md) — Strapi HTTP server configuration defining host, port, external public URL (`https://shadows-db.braingeneers.gi.ucsc.edu/`), proxy trust, and session secret keys. Symbols: module-level code.

## strapi-shadows-db/src
- [index.js](strapi-shadows-db/src/index.js.md) — Strapi application lifecycle root module providing extension lifecycle hooks (`register` and `bootstrap`) called during server startup. Symbols: bootstrap, register.

## strapi-shadows-db/src/admin
- [app.example.js](strapi-shadows-db/src/admin/app.example.js.md) — Example template configuration for customizing the Strapi admin UI panel, including internationalization locale configuration and admin bootstrap hook. Symbols: module-level code.
- [webpack.config.example.js](strapi-shadows-db/src/admin/webpack.config.example.js.md) — Example template for customizing Webpack compilation options used when building the Strapi admin panel frontend. Symbols: module-level code.

## strapi-shadows-db/src/api/experiment/controllers
- [experiment.js](strapi-shadows-db/src/api/experiment/controllers/experiment.js.md) — Strapi core controller for the Experiment content type generated via `@strapi/strapi` factories, handling CRUD HTTP requests for laboratory experiments. Symbols: createCoreController.

## strapi-shadows-db/src/api/experiment/routes
- [experiment.js](strapi-shadows-db/src/api/experiment/routes/experiment.js.md) — Strapi core router configuration for the Experiment content type defining REST API routes for experiment records. Symbols: createCoreRouter.

## strapi-shadows-db/src/api/experiment/services
- [experiment.js](strapi-shadows-db/src/api/experiment/services/experiment.js.md) — Strapi core service for the Experiment content type providing business logic and database queries for laboratory experiment records. Symbols: createCoreService.

## strapi-shadows-db/src/api/interaction-thing/controllers
- [interaction-thing.js](strapi-shadows-db/src/api/interaction-thing/controllers/interaction-thing.js.md) — Strapi core controller for the Interaction Thing content type, handling CRUD operations for IoT laboratory hardware interaction targets. Symbols: createCoreController.

## strapi-shadows-db/src/api/interaction-thing/routes
- [interaction-thing.js](strapi-shadows-db/src/api/interaction-thing/routes/interaction-thing.js.md) — Strapi core router configuration for the Interaction Thing content type, defining REST endpoints for hardware interaction entities. Symbols: createCoreRouter.

## strapi-shadows-db/src/api/interaction-thing/services
- [interaction-thing.js](strapi-shadows-db/src/api/interaction-thing/services/interaction-thing.js.md) — Strapi core service for the Interaction Thing content type, managing persistence and business logic for IoT interaction devices. Symbols: createCoreService.

## strapi-shadows-db/src/api/plate/controllers
- [plate.js](strapi-shadows-db/src/api/plate/controllers/plate.js.md) — Strapi core controller for the Plate content type, handling HTTP requests for multi-well experimental cell culture plates. Symbols: createCoreController.

## strapi-shadows-db/src/api/plate/routes
- [plate.js](strapi-shadows-db/src/api/plate/routes/plate.js.md) — Strapi core router for the Plate content type, configuring REST API routing for cell culture plates. Symbols: createCoreRouter.

## strapi-shadows-db/src/api/plate/services
- [plate.js](strapi-shadows-db/src/api/plate/services/plate.js.md) — Strapi core service for the Plate content type, implementing database queries and business logic for multi-well plates. Symbols: createCoreService.

## strapi-shadows-db/src/api/sample/controllers
- [sample.js](strapi-shadows-db/src/api/sample/controllers/sample.js.md) — Strapi core controller for the Sample content type, handling HTTP requests for biological organoid cell samples. Symbols: createCoreController.

## strapi-shadows-db/src/api/sample/routes
- [sample.js](strapi-shadows-db/src/api/sample/routes/sample.js.md) — Strapi core router configuration for the Sample content type, exposing REST API routes for organoid samples. Symbols: createCoreRouter.

## strapi-shadows-db/src/api/sample/services
- [sample.js](strapi-shadows-db/src/api/sample/services/sample.js.md) — Strapi core service for the Sample content type, managing data queries and persistence logic for cell culture samples. Symbols: createCoreService.

## strapi-shadows-db/src/api/well/controllers
- [well.js](strapi-shadows-db/src/api/well/controllers/well.js.md) — Strapi core controller for the Well content type, handling HTTP requests for individual plate wells (position, media, organoid contents). Symbols: createCoreController.

## strapi-shadows-db/src/api/well/routes
- [well.js](strapi-shadows-db/src/api/well/routes/well.js.md) — Strapi core router configuration for the Well content type, exposing REST endpoints for well records. Symbols: createCoreRouter.

## strapi-shadows-db/src/api/well/services
- [well.js](strapi-shadows-db/src/api/well/services/well.js.md) — Strapi core service for the Well content type, managing database operations and relations for plate well records. Symbols: createCoreService.

## Package markers and re-exports (no per-file summary)

## Known holes
- Skipped directory names anywhere in the tree: `__pycache__`, `build`, `dist`, `generated`, `internal_tests`, `node_modules`, `site-packages`, `test`, `testing`, `tests`, `third_party`, `vendor`, `vendored`; dot-directories; repo-root files.
- Notebooks, data, weights, images, shell/SLURM/YAML files, and other non-source assets are not summarized.
- `data-lifecycle/src/generate_puts_deletes_test.py` — test or placeholder.
- `data-lifecycle/tests/` — excluded directory.
- `docker-maintenance/test_maintenance.py` — test or placeholder.
- `skills/nrp-monitor/scripts/tests/` — excluded directory.
- `tests/` — excluded directory.
