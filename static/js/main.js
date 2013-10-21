require.config({
  paths: {
    'angular': '../vendor/angular/angular',
    'angularAnimate': '../vendor/angular-animate/angular-animate',
    'angularLinkify': '../vendor/angular-linkify/angular-linkify',
    'angularRoute': '../vendor/angular-route/angular-route',
    'angularSanitize': '../vendor/angular-sanitize/angular-sanitize',
    'bootstrap': '../vendor/bootstrap/dist/js/bootstrap',
    'jquery': '../vendor/jquery/jquery',
    'moment': '../vendor/moment/moment',
    'ngInfiniteScroll': '../vendor/ngInfiniteScroll/ng-infinite-scroll'
  },
  baseUrl: 'static/js',
  shim: {
    'angular': {exports: 'angular'},
    'angularAnimate': ['angular'],
    'angularLinkify': ['angular'],
    'angularRoute': ['angular'],
    'angularSanitize': ['angular'],
    'modules/pagination': ['angular'],
    'ngInfiniteScroll': ['angular'],
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
  'routes',
], function(jquery, bootstrap, angular, app, routes) {
  'use strict';
  $(function(){
    angular.bootstrap(document, ['app', 'infinite-scroll']);
  });
});
