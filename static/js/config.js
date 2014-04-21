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
    'd3': '../vendor/d3/d3',
    'jquery': '../vendor/jquery/jquery',
    'highlightjs': '../vendor/highlightjs/highlight.pack',
    'moment': '../vendor/moment/moment',
    'ngInfiniteScroll': '../vendor/ngInfiniteScroll/ng-infinite-scroll',
    'nvd3': '../vendor/nvd3/nv.d3',
    'notify': 'lib/notify',
    'requirejs': '../vendor/requirejs/requirejs'
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
    'modules/collection': ['angular'],
    'modules/flash': ['angular'],
    'modules/pagination': ['angular'],
    'modules/stream': ['angular'],
    'ngInfiniteScroll': ['angular'],
    'jquery': {
        exports: 'jquery'
    },
    'bootstrap': {
        deps: ['jquery']
    },
    'notify': {
        deps: ['bootstrap']
    },
    'nvd3': {
        exports: 'nvd3',
        deps: ['d3']
    }
  }
});
