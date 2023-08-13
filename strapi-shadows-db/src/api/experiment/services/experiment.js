'use strict';

/**
 * experiment service.
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::experiment.experiment');
