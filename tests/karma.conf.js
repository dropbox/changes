// Karma configuration
// Generated on Tue May 27 2014 23:33:33 GMT-0700 (PDT)

module.exports = function(config) {
  config.set({

    // base path, that will be used to resolve files and exclude
    basePath: '../',


    // frameworks to use
    frameworks: ['mocha', 'requirejs'],


    // list of files / patterns to load in the browser
    files: [
      {pattern: 'node_modules/chai/chai.js', included: false},
      {pattern: 'node_modules/sinon/pkg/sinon.js', included: false},
      {pattern: 'static/js/**/*.js', included: false},
      {pattern: 'static/vendor/**/*.js', included: false},
      {pattern: 'tests/js/**/*Spec.js', included: false},
      'tests/test-main.js'
    ],

    // test results reporter to use
    // possible values: 'dots', 'progress', 'junit', 'growl', 'coverage'
    reporters: ['progress', 'junit'],


    // web server port
    port: 9876,


    // enable / disable colors in the output (reporters and logs)
    colors: true,


    // level of logging
    // possible values: config.LOG_DISABLE || config.LOG_ERROR || config.LOG_WARN || config.LOG_INFO || config.LOG_DEBUG
    logLevel: config.LOG_INFO,


    // enable / disable watching file and executing tests whenever any file changes
    autoWatch: true,


    // Start these browsers, currently available:
    // - Chrome
    // - ChromeCanary
    // - Firefox
    // - Opera
    // - Safari (only Mac)
    // - PhantomJS
    // - IE (only Windows)
    browsers: ['PhantomJS'],


    // If browser does not capture in given timeout [ms], kill it
    captureTimeout: 60000,


    // Continuous Integration mode
    // if true, it capture browsers, run tests and exit
    singleRun: false,


    junitReporter: {
      outputFile: 'js.junit.xml',
      suite: ''
    }
  });
};
