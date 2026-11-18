# Connections graph

Generated: 2026-11-18 | commit: 775a1d79c860b23ddbbf59f5a1ddd1dfc237b3b7 | mode: all

Edges below are source-backed **imports** resolved against the repo root and the importing script's directory (sys.path style), not runtime calls. Dynamic dispatch, `sys.path` hacks to unusual locations, wildcard imports and re-exports can be incomplete. Configured external library imports appear under `**Library:**` in summaries.

## data-lifecycle
Project scripts; see per-file summaries.
- `data-lifecycle.src.generate_cleanup_report` --imports--> `data-lifecycle.src.generate_puts_deletes.apply_last_modified_updates`
- `data-lifecycle.src.generate_cleanup_report` --imports--> `data-lifecycle.src.generate_puts_deletes.build_cleanup_window_entries`
- `data-lifecycle.src.generate_cleanup_report` --imports--> `data-lifecycle.src.generate_puts_deletes.load_config_file`
- `data-lifecycle.src.generate_cleanup_report` --imports--> `data-lifecycle.src.generate_puts_deletes.load_inventories`
- `data-lifecycle.src.generate_cleanup_report` --imports--> `data-lifecycle.src.glacier_cost_analysis_plot.DEFAULT_COST_PER_GB_MONTH`
- `data-lifecycle.src.generate_cleanup_report` --imports--> `data-lifecycle.src.glacier_cost_analysis_plot.DEFAULT_PER_OBJECT_OVERHEAD_BYTES`
- `data-lifecycle.src.generate_cleanup_report` --imports--> `data-lifecycle.src.glacier_cost_analysis_plot.build_retention_points`
- `data-lifecycle.src.generate_cleanup_report` --imports--> `data-lifecycle.src.glacier_cost_analysis_plot.parse_inventory_summary`
- `data-lifecycle.src.generate_puts_deletes` --imports--> `data-lifecycle.src.badkeys.make_badkey_record`
- `data-lifecycle.src.generate_puts_deletes` --imports--> `data-lifecycle.src.badkeys.write_badkeys_tsv`
- `data-lifecycle.src.generate_puts_deletes` --imports--> `data-lifecycle.src.lifecycle_controls.apply_effective_last_modified`
- `data-lifecycle.src.generate_puts_deletes` --imports--> `data-lifecycle.src.lifecycle_controls.is_retention_marker`
- `data-lifecycle.src.generate_puts_deletes` --imports--> `data-lifecycle.src.lifecycle_controls.lifecycle_control_mask`
- `data-lifecycle.src.generate_puts_deletes` --imports--> `data-lifecycle.src.lifecycle_controls.marker_upload_mask`
- `data-lifecycle.src.generate_puts_deletes` --imports--> `data-lifecycle.src.lifecycle_controls.normalize_atomic_directories`
- `data-lifecycle.src.generate_puts_deletes` --imports--> `data-lifecycle.src.lifecycle_controls.scientific_inventory`
- `data-lifecycle.src.generate_puts_deletes` --imports--> `data-lifecycle.src.stage4_keys.normalize_bucket_object_key`
- `data-lifecycle.src.lifecycle_controls` --imports--> `data-lifecycle.src.lifecycle_constants.FILE_RETENTION_SUFFIX`
- `data-lifecycle.src.lifecycle_controls` --imports--> `data-lifecycle.src.lifecycle_constants.NOBACKUP_MARKER_NAME`
- `data-lifecycle.src.lifecycle_controls` --imports--> `data-lifecycle.src.lifecycle_constants.RETENTION_MARKER_NAME`
- `data-lifecycle.src.stage4_process_puts_deletes` --imports--> `data-lifecycle.src.badkeys.SOURCE_GET_FAILED_AFTER_HEAD_SUCCESS`
- `data-lifecycle.src.stage4_process_puts_deletes` --imports--> `data-lifecycle.src.badkeys.append_source_get_failed_slack_section`
- `data-lifecycle.src.stage4_process_puts_deletes` --imports--> `data-lifecycle.src.badkeys.make_badkey_record`
- `data-lifecycle.src.stage4_process_puts_deletes` --imports--> `data-lifecycle.src.badkeys.merge_badkey_records`
- `data-lifecycle.src.stage4_process_puts_deletes` --imports--> `data-lifecycle.src.badkeys.read_badkeys_tsv`
- `data-lifecycle.src.stage4_process_puts_deletes` --imports--> `data-lifecycle.src.badkeys.source_get_failed_records`
- `data-lifecycle.src.stage4_process_puts_deletes` --imports--> `data-lifecycle.src.badkeys.write_badkeys_tsv`
- `data-lifecycle.src.stage4_process_puts_deletes` --imports--> `data-lifecycle.src.lifecycle_controls.is_retention_marker`
- `data-lifecycle.src.stage4_process_puts_deletes` --imports--> `data-lifecycle.src.stage4_keys.build_source_lookup_candidates`
- `data-lifecycle.src.stage4_process_puts_deletes` --imports--> `data-lifecycle.src.stage4_keys.load_put_keys`
- `data-lifecycle.src.stage4_process_puts_deletes` --imports--> `data-lifecycle.src.stage4_keys.normalize_bucket_object_key`

## docker-maintenance
Project scripts; see per-file summaries.

## experiment-dash
Project scripts; see per-file summaries.
- `experiment-dash.experiment-plotly-app` --imports--> `experiment-dash.dashboard_helpers.*`

## job-h5repack
Project scripts; see per-file summaries.

## logging-s3
Project scripts; see per-file summaries.

## logging-s3-aggregator
Project scripts; see per-file summaries.

## nginx-reverse-proxy
Project scripts; see per-file summaries.

## oauth2-proxy
Project scripts; see per-file summaries.

## plotly-dash-picroscope-control-console
Project scripts; see per-file summaries.
- `plotly-dash-picroscope-control-console.app` --imports--> `plotly-dash-picroscope-control-console.app_elements.experiment_panel`
- `plotly-dash-picroscope-control-console.app` --imports--> `plotly-dash-picroscope-control-console.app_elements.imaging_panel`
- `plotly-dash-picroscope-control-console.app` --imports--> `plotly-dash-picroscope-control-console.app_elements.livestream_panel`
- `plotly-dash-picroscope-control-console.app` --imports--> `plotly-dash-picroscope-control-console.callbacks.db_interactor`
- `plotly-dash-picroscope-control-console.app` --imports--> `plotly-dash-picroscope-control-console.callbacks.get_callbacks`
- `plotly-dash-picroscope-control-console.app_elements.experiment_panel` --imports--> `plotly-dash-picroscope-control-console.callbacks.*`
- `plotly-dash-picroscope-control-console.app_elements.imaging_panel` --imports--> `plotly-dash-picroscope-control-console.callbacks.db_interactor`
- `plotly-dash-picroscope-control-console.callbacks` --imports--> `plotly-dash-picroscope-control-console.Experiment_Metadata_SQL.*`

## service-accounts
Project scripts; see per-file summaries.

## shadows_vue
Project scripts; see per-file summaries.

## skills
Project scripts; see per-file summaries.
- `skills.braingeneers-one.scripts._vendor.yaml` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.dumper.*`
- `skills.braingeneers-one.scripts._vendor.yaml` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.error.*`
- `skills.braingeneers-one.scripts._vendor.yaml` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.events.*`
- `skills.braingeneers-one.scripts._vendor.yaml` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.loader.*`
- `skills.braingeneers-one.scripts._vendor.yaml` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.nodes.*`
- `skills.braingeneers-one.scripts._vendor.yaml` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.tokens.*`
- `skills.braingeneers-one.scripts._vendor.yaml.composer` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.error.MarkedYAMLError`
- `skills.braingeneers-one.scripts._vendor.yaml.composer` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.events.*`
- `skills.braingeneers-one.scripts._vendor.yaml.composer` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.nodes.*`
- `skills.braingeneers-one.scripts._vendor.yaml.constructor` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.error.*`
- `skills.braingeneers-one.scripts._vendor.yaml.constructor` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.nodes.*`
- `skills.braingeneers-one.scripts._vendor.yaml.dumper` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.emitter.*`
- `skills.braingeneers-one.scripts._vendor.yaml.dumper` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.representer.*`
- `skills.braingeneers-one.scripts._vendor.yaml.dumper` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.resolver.*`
- `skills.braingeneers-one.scripts._vendor.yaml.dumper` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.serializer.*`
- `skills.braingeneers-one.scripts._vendor.yaml.emitter` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.error.YAMLError`
- `skills.braingeneers-one.scripts._vendor.yaml.emitter` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.events.*`
- `skills.braingeneers-one.scripts._vendor.yaml.loader` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.composer.*`
- `skills.braingeneers-one.scripts._vendor.yaml.loader` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.constructor.*`
- `skills.braingeneers-one.scripts._vendor.yaml.loader` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.parser.*`
- `skills.braingeneers-one.scripts._vendor.yaml.loader` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.reader.*`
- `skills.braingeneers-one.scripts._vendor.yaml.loader` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.resolver.*`
- `skills.braingeneers-one.scripts._vendor.yaml.loader` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.scanner.*`
- `skills.braingeneers-one.scripts._vendor.yaml.parser` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.error.MarkedYAMLError`
- `skills.braingeneers-one.scripts._vendor.yaml.parser` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.events.*`
- `skills.braingeneers-one.scripts._vendor.yaml.parser` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.scanner.*`
- `skills.braingeneers-one.scripts._vendor.yaml.parser` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.tokens.*`
- `skills.braingeneers-one.scripts._vendor.yaml.reader` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.error.Mark`
- `skills.braingeneers-one.scripts._vendor.yaml.reader` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.error.YAMLError`
- `skills.braingeneers-one.scripts._vendor.yaml.representer` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.error.*`
- `skills.braingeneers-one.scripts._vendor.yaml.representer` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.nodes.*`
- `skills.braingeneers-one.scripts._vendor.yaml.resolver` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.error.*`
- `skills.braingeneers-one.scripts._vendor.yaml.resolver` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.nodes.*`
- `skills.braingeneers-one.scripts._vendor.yaml.scanner` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.error.MarkedYAMLError`
- `skills.braingeneers-one.scripts._vendor.yaml.scanner` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.tokens.*`
- `skills.braingeneers-one.scripts._vendor.yaml.serializer` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.error.YAMLError`
- `skills.braingeneers-one.scripts._vendor.yaml.serializer` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.events.*`
- `skills.braingeneers-one.scripts._vendor.yaml.serializer` --imports--> `skills.braingeneers-one.scripts._vendor.yaml.nodes.*`

## slack-bridge
Project scripts; see per-file summaries.

## smartplug-dash
Project scripts; see per-file summaries.

## strapi-shadows-db
Project scripts; see per-file summaries.
