requirejs.config({
  paths: {
    'angular': '../vendor/angular/angular.min',
    'angularAnimate': '../vendor/angular-animate/angular-animate.min',
    'angularBootstrap': '../vendor/angular-bootstrap/ui-bootstrap-tpls',
    'angularHighlightjs': '../vendor/angular-highlightjs/angular-highlightjs',
    'angularLinkify': '../vendor/angular-linkify/angular-linkify.min',
    'angularRaven': '../vendor/angular-raven/angular-raven',
    'angularRoute': '../vendor/angular-route/angular-route.min',
    'angularSanitize': '../vendor/angular-sanitize/angular-sanitize.min',
    'angularLoadingBar': '../vendor/angular-loading-bar/build/loading-bar.min',
    'angularUIRouter': '../vendor/angular-ui-router/release/angular-ui-router.min',
    'bootstrap': '../vendor/bootstrap/dist/js/bootstrap.min',
    'd3': '../vendor/d3/d3.min',
    'd3-tip': '../vendor/d3-tip/index',
    'jquery': '../vendor/jquery/jquery',
    'highlightjs': '../vendor/highlightjs/highlight.pack',
    'moment': '../vendor/moment/moment',
    'requirejs': '../vendor/requirejs/require'
  },
  shim: {
    'angular': {
        exports: 'angular',
        deps: ['jquery']
    },
    'angularAnimate': ['angular'],
    'angularBootstrap': ['angular'],
    'angularHighlightjs': {
        deps: ['angular', 'highlightjs']
    },
    'angularLinkify': ['angular'],
    'angularLoadingBar': ['angular'],
    'angularRaven': ['angular'],
    'angularRoute': ['angular'],
    'angularSanitize': ['angular'],
    'angularUIRouter': ['angular'],
    'bootstrap': ['jquery'],
    'modules/barChart': ['bootstrap'],
    'modules/collection': ['angular'],
    'modules/flash': ['angular'],
    'modules/pagination': ['angular'],
    'modules/stream': ['angular'],
    'modules/scalyr': ['angular'],
    'jquery': {
        exports: 'jquery'
    }
  }
});

require(["vendor-angular", "vendor-jquery", "vendor-misc"], function(){
  'use strict';

  require(["app", "angular", "routes"], function(app, angular){
    angular.bootstrap(document, ['app']);
  });
});
