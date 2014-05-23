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
  'jquery',
  'modules/barChart',
  'modules/collection',
  'modules/d3BarChart',
  'modules/flash',
  'modules/pageTitle',
  'modules/pagination',
  'modules/poller',
  'modules/scalyr'
  ], function (angular) {
    'use strict';

    return angular.module('app', [
      'barChart',
      'changes.barchart',
      'changes.pageTitle',
      'changes.poller',
      'chieffancypants.loadingBar',
      'collection',
      'flash',
      'hljs',
      'linkify',
      'ngAnimate',
      'ngRoute',
      'ngSanitize',
      'pagination',
      'sly',
      'ui.bootstrap',
      'ui.router'
    ]);
});
