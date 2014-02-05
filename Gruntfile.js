module.exports = function(grunt) {
  "use strict";
  grunt.loadNpmTasks('grunt-contrib-requirejs');

  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    requirejs: {
      compile: {
        options: {
          baseUrl: "js/",
          mainConfigFile: "static/js/main.js",
          appDir: "static/",
          dir: "static-built/",
          skipDirOptimize: true,
          generateSourceMaps: true,
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
