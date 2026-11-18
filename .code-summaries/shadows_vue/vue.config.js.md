# vue.config.js

**Path:** `shadows_vue/vue.config.js`
**Module:** `shadows_vue.vue.config`
**Feature Area:** `shadows_vue`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Vue CLI configuration defining sub-path routing (`publicPath: '/datahub/'`), output distribution path (`./dist/datahub/`), and dependency transpilation settings.

## Connections
- **Shared data:** Builds Vue distribution bundle served behind Nginx/reverse proxy.

## Dependencies
None

## Classes
None

## Functions
### `defineConfig({ ... })`
> Exports Vue CLI build configuration.
**Source:** `shadows_vue/vue.config.js:4`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `publicPath: '/datahub/'` |
| `outputDir: './dist/datahub/'` |

## Data Shapes
None

## Notes
- Configures sub-path hosting under reverse proxy path `/datahub/`.
