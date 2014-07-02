define([
  'angular',
  'angularAnimate',
  'angularBootstrap',
  'angularHighlightjs',
  'angularLinkify',
  'angularLoadingBar',
  'angularRoute',
  'angularSanitize',
  'angularUIRouter',
  'bootstrap/tooltip',
  'jquery',
  'modules/barChart',
  'modules/collection',
  'modules/d3BarChart',
  'modules/flash',
  'modules/pageTitle',
  'modules/paginator',
  'modules/poller',
  'modules/scalyr'
  ], function (angular) {
    'use strict';

    return angular.module('app', [
      'barChart',
      'changes.barchart',
      'changes.pageTitle',
      'changes.paginator',
      'changes.poller',
      'chieffancypants.loadingBar',
      'collection',
      'flash',
      'hljs',
      'linkify',
      'ngAnimate',
      'ngRoute',
      'ngSanitize',
      'sly',
      'ui.bootstrap',
      'ui.router'
    ]);
});
