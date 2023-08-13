'use strict';

/**
 * sample service.
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::sample.sample');
