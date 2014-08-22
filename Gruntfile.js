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
          generateSourceMaps: true,
          findNestedDependencies: true,
          preserveLicenseComments: false,
          removeCombined: true,
          modules: [
            {
              name: "main",
              exclude: ["vendor-angular", "vendor-jquery", "vendor-misc"]
            },
            {
              name: "vendor-angular"
            },
            {
              name: "vendor-jquery"
            },
            {
              name: "vendor-misc"
            }
          ],
          optimize: "uglify2",
          optimizeCss: "none",
          useSourceUrl: true,
          wrapShim: true
        }
      }
    }
  });
};
