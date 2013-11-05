require.config({
  paths: {
    'angular': '../vendor/angular/angular',
    'angularAnimate': '../vendor/angular-animate/angular-animate',
    'angularLinkify': '../vendor/angular-linkify/angular-linkify',
    'angularRoute': '../vendor/angular-route/angular-route',
    'angularSanitize': '../vendor/angular-sanitize/angular-sanitize',
    'angularLoadingBar': '../vendor/angular-loading-bar/build/loading-bar',
    'bootstrap': '../vendor/bootstrap/dist/js/bootstrap',
    'flot': '../vendor/flot/jquery.flot',
    'jquery': '../vendor/jquery/jquery',
    'jquery.flot.tooltip': '../vendor/jquery.flot.tooltip',
    'jquery.flot.stack': '../vendor/flot/jquery.flot.stack',
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
    'modules/flot': {deps: ['flot', 'angular']},
    'modules/pagination': ['angular'],
    'modules/stream': ['angular'],
    'filters/truncate': ['angular'],
    'jquery': {exports: 'jquery'},
    'bootstrap': {deps: ['jquery']},
    'flot': {deps: ['jquery']},
    'jquery.flot.tooltip': {deps: ['flot']},
    'jquery.flot.stack': {deps: ['flot']}
  },
  priority: [
    "jquery",
    "bootstrap",
    "moment",
    "angular"
  ]
});

require([
  'angular',
  'angularLoadingBar',
  'modules/flash',
  'modules/flot',
  'modules/stream',
  'filters/truncate',
  'routes',
  'jquery',
  'bootstrap',
  'flot',
  'jquery.flot.tooltip',
  'jquery.flot.stack'
], function(angular) {
  'use strict';
  $(function(){
    angular.bootstrap(document, ['app', 'chieffancypants.loadingBar', 'stream', 'flash', 'flot']);
  });
});
