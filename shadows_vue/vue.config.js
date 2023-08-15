// const path = require('path');

const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  publicPath: "/datahub/",
  outputDir: "./dist/datahub/",
//   assetsDir: "./datahub/",
//   baseUrl: "/braingeneers-hub/"
})


// module.exports = {
//     build: {
//         // Template for index.html
//         assetsPublicPath: '/',
//     }
// }


// const publicPath = path.join(__dirname, 'datahub');
// this.express.use('/datahub', express.static(publicPath));