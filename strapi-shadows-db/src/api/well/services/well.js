'use strict';

/**
 * well service.
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::well.well');
