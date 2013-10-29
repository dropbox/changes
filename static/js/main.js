require.config({
  paths: {
    'angular': '../vendor/angular/angular',
    'angularAnimate': '../vendor/angular-animate/angular-animate',
    'angularLinkify': '../vendor/angular-linkify/angular-linkify',
    'angularRoute': '../vendor/angular-route/angular-route',
    'angularSanitize': '../vendor/angular-sanitize/angular-sanitize',
    'angularLoadingBar': '../vendor/angular-loading-bar/build/loading-bar',
    'bootstrap': '../vendor/bootstrap/dist/js/bootstrap',
    'jquery': '../vendor/jquery/jquery',
    'moment': '../vendor/moment/moment',
  },
  baseUrl: 'static/js',
  shim: {
    'angular': {exports: 'angular'},
    'angularAnimate': ['angular'],
    'angularLinkify': ['angular'],
    'angularLoadingBar': ['angular'],
    'angularRoute': ['angular'],
    'angularSanitize': ['angular'],
    'modules/flash': ['angular'],
    'modules/pagination': ['angular'],
    'modules/stream': ['angular'],
    'jquery': {exports: 'jquery'},
    'bootstrap': {deps: ['jquery']},
  },
  priority: [
    "jquery",
    "bootstrap",
    "moment",
    "angular"
  ]
});

require([
  'jquery',
  'bootstrap',
  'angular',
  'angularLoadingBar',
  'modules/flash',
  'modules/stream',
  'routes',
], function(jquery, bootstrap, angular, app, routes) {
  'use strict';
  $(function(){
    angular.bootstrap(document, ['app', 'chieffancypants.loadingBar', 'stream', 'flash']);
  });
});
