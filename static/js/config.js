requirejs.config({
  paths: {
    'angular': '../vendor/angular/angular',
    'angularAnimate': '../vendor/angular-animate/angular-animate',
    'angularBootstrap': '../vendor/angular-bootstrap/ui-bootstrap-tpls',
    'angularHighlightjs': '../vendor/angular-highlightjs/angular-highlightjs',
    'angularLinkify': '../vendor/angular-linkify/angular-linkify',
    'angularRaven': '../vendor/angular-raven/angular-raven',
    'angularRoute': '../vendor/angular-route/angular-route',
    'angularSanitize': '../vendor/angular-sanitize/angular-sanitize',
    'angularLoadingBar': '../vendor/angular-loading-bar/build/loading-bar',
    'angularUIRouter': '../vendor/angular-ui-router/release/angular-ui-router',
    'bootstrap': '../vendor/bootstrap/dist/js/bootstrap',
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
