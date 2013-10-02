require.config({
  paths: {
    'angular': 'vendor/angular/angular',
    'angularRoute': 'vendor/angular-route/angular-route',
    'angularAnimate': 'vendor/angular-animate/angular-animate',
    'bootstrap': 'vendor/bootstrap',
    'jquery': 'vendor/jquery/jquery',
    'moment': 'vendor/moment/moment'
  },
  baseUrl: 'static/js',
  shim: {
    'angular': {exports: 'angular'},
    'angularRoute': ['angular'],
    'angularAnimate': ['angular'],
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
  'moment',
  'routes'
], function(jquery, bootstrap, angular, moment, app, routes) {
  'use strict';
  $(function(){
    angular.bootstrap(document, ['app']);
  });
});
