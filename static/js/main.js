require.config({
  paths: {
    'angular': '../vendor/angular/angular',
    'angularAnimate': '../vendor/angular-animate/angular-animate',
    'angularLinkify': '../vendor/angular-linkify/angular-linkify',
    'angularRaven': '../vendor/angular-raven/angular-raven',
    'angularRoute': '../vendor/angular-route/angular-route',
    'angularSanitize': '../vendor/angular-sanitize/angular-sanitize',
    'angularLoadingBar': '../vendor/angular-loading-bar/build/loading-bar',
    'bootstrap': '../vendor/bootstrap/dist/js/bootstrap',
    'd3': '../vendor/d3/d3',
    'jquery': '../vendor/jquery/jquery',
    'moment': '../vendor/moment/moment',
    'nvd3': '../vendor/nvd3/nv.d3'
  },
  baseUrl: 'static/js',
  shim: {
    'angular': {exports: 'angular'},
    'angularAnimate': ['angular'],
    'angularLinkify': ['angular'],
    'angularLoadingBar': ['angular'],
    'angularRaven': ['angular'],
    'angularRoute': ['angular'],
    'angularSanitize': ['angular'],
    'modules/collection': ['angular'],
    'modules/flash': ['angular'],
    'modules/pagination': ['angular'],
    'modules/stream': ['angular'],
    'filters/truncate': ['angular'],
    'jquery': {exports: 'jquery'},
    'bootstrap': {deps: ['jquery']},
    'nvd3': {deps: ['d3']}
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
  'modules/barChart',
  'modules/collection',
  'modules/flash',
  'modules/stream',
  'filters/truncate',
  'routes',
  'jquery',
  'bootstrap'
], function(angular) {
  'use strict';
  $(function(){
    angular.bootstrap(document, ['app', 'chieffancypants.loadingBar', 'barChart', 'collection', 'flash', 'stream']);
  });
});
