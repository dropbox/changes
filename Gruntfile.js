module.exports = function(grunt) {
  "use strict";
  grunt.loadNpmTasks("grunt-contrib-requirejs");

  grunt.initConfig({
    pkg: grunt.file.readJSON("package.json"),
    requirejs: {
      compile2: {
        options: {
          baseUrl: "webapp/",
          name: "entry", // assumes a production build using almond
          out: "webapp/dist/built.js",

          // the paths config attribute in entry.js uses URL paths (which are 
          // completely controlled by the flask app.) This attribute uses the
          // actual file locations on disk
          'paths': {
              'babel': '../static/vendor/requirejs-babel/babel-4.6.6.min',
              'classnames': '../static/vendor/classnames/index',
              'es6': '../static/vendor/requirejs-babel/es6',
              'moment': "../static/vendor/moment/min/moment.min",
              'react': '../static/vendor/react/react-with-addons',
              'react-dom': '../static/vendor/react/react-dom',
              'react_bootstrap': '../static/vendor/react-bootstrap/react-bootstrap',
              'requirejs': '../static/vendor/requirejs/require',
              'underscore': '../static/vendor/underscore/underscore',
              'uriJS': '../static/vendor/uri.js/src'
          },

          config: {
            'es6': {
              'optional': ['es7.objectRestSpread'],
            }
          },

          shim: {
            underscore: {
              exports: '_'
            },
          },

          // Increase the require.js load timeout threshold, since the ES6
          // compilation step in development mode often exceeds the default
          // 7-second threshold.
          waitSeconds: 15,

          'stubModules': ['es6', 'babel'],

          // uglify would cut the final file size by 50%, but make debugging 
          // more difficult. Not to mention that we rely on window.* globals 
          // a fair amount
          'optimize': 'none',

          // hmm..I've completely forgetten what this does
          'pragmasOnSave': {
              'excludeBabel': true
          }
        }
      }
    }
  });

  grunt.registerTask('compile-static', ['requirejs']);
  grunt.registerTask('compile-reactjs', ['requirejs']);
};
