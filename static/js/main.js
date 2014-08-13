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
    'bootstrap': '../vendor/bootstrap/js',
    'bloodhound': '../vendor/typeahead.js/dist/bloodhound.min',
    'd3': '../vendor/d3/d3.min',
    'd3-tip': '../vendor/d3-tip/index',
    'jquery': '../vendor/jquery/jquery',
    'highlightjs': '../vendor/highlightjs/highlight.pack',
    'moment': '../vendor/moment/moment',
    'requirejs': '../vendor/requirejs/require',
    'typeahead': '../vendor/typeahead.js/dist/typeahead.jquery.min'
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
    'bloodhound': {deps: ['jquery'], exports: 'Bloodhound'},
    'bootstrap/affix': {deps: ['jquery'], exports: '$.fn.affix'},
    'bootstrap/alert': {deps: ['jquery'], exports: '$.fn.alert'},
    'bootstrap/button': {deps: ['jquery'], exports: '$.fn.button'},
    'bootstrap/carousel': {deps: ['jquery'], exports: '$.fn.carousel'},
    'bootstrap/collapse': {deps: ['jquery'], exports: '$.fn.collapse'},
    'bootstrap/dropdown': {deps: ['jquery'], exports: '$.fn.dropdown'},
    'bootstrap/modal': {deps: ['jquery'], exports: '$.fn.modal'},
    'bootstrap/popover': {deps: ['jquery'], exports: '$.fn.popover'},
    'bootstrap/scrollspy': {deps: ['jquery'], exports: '$.fn.scrollspy'},
    'bootstrap/tab': {deps: ['jquery'], exports: '$.fn.tab'},
    'bootstrap/tooltip': {deps: ['jquery'], exports: '$.fn.tooltip'},
    'bootstrap/transition': {deps: ['jquery'], exports: '$.fn.transition'},
    'jquery': {
        exports: 'jquery'
    },
    'typeahead': {
        deps: ['bloodhound', 'jquery'],
        exports: '$.fn.typeahead'
    }
  }
});

require(["vendor-angular", "vendor-jquery", "vendor-misc"], function(){
  'use strict';

  require(["app", "angular", "routes"], function(app, angular){
    angular.bootstrap(document, ['app']);
  });
});
