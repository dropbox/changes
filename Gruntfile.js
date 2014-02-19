module.exports = function(grunt) {
  "use strict";
  grunt.loadNpmTasks('grunt-contrib-requirejs');

  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    requirejs: {
      compile: {
        options: {
          baseUrl: "js/",
          mainConfigFile: "static/js/config.js",
          appDir: "static/",
          dir: "static-built/",
          skipDirOptimize: true,
          generateSourceMaps: true,
          findNestedDependencies: true,
          preserveLicenseComments: false,
          uglify2: {
            mangle: false
          },
          optimize: "uglify2",
          optimizeCss: "none",
          name: "main"
        }
      }
    }
  });
};
