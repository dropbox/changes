module.exports = function(grunt) {
  "use strict";
  grunt.loadNpmTasks("grunt-contrib-requirejs");

  grunt.initConfig({
    pkg: grunt.file.readJSON("package.json"),
    requirejs: {
      compile: {
        options: {
          baseUrl: "js/",
          mainConfigFile: "static/js/main.js",
          appDir: "static/",
          dir: "static-built/",
          skipDirOptimize: true,
          generateSourceMaps: false,
          findNestedDependencies: true,
          preserveLicenseComments: false,
          removeCombined: true,
          uglify2: {
            mangle: false
          },
          modules: [
            {
              name: "main",
              exclude: ["vendor-angular", "vendor-bootstrap", "vendor-jquery", "vendor-misc"]
            },
            {
              name: "vendor-angular"
            },
            {
              name: "vendor-bootstrap"
            },
            {
              name: "vendor-jquery"
            },
            {
              name: "vendor-misc"
            }
          ],
          optimize: "uglify2",
          optimizeCss: "none"
        }
      }
    }
  });
};
