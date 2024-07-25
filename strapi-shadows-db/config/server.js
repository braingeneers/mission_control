module.exports = ({ env }) => ({
  host: env('HOST', '0.0.0.0'),
  port: env.int('PORT', 1337),
  url: 'https://shadows-db.braingeneers.gi.ucsc.edu/',
  proxy: true, 
  app: {
    keys: env.array('APP_KEYS'),
  },

   // Middleware to ignore Authorization header for public routes (if needed)
  middleware: {
    settings: {
      public: {
        enabled: true,
        config: {
          ignoreAuthorization: true,
        },
      },
    },
  },
});
