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
  'bootstrap',
  'jquery',
  'modules/barChart',
  'modules/collection',
  'modules/d3BarChart',
  'modules/flash',
  'modules/pageTitle',
  'modules/pagination',
  'modules/scalyr',
  'modules/stream'
  ], function (angular) {
    'use strict';

    return angular.module('app', [
      'barChart',
      'changes.barchart',
      'changes.pageTitle',
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
      'stream',
      'ui.bootstrap',
      'ui.router'
    ]);
});
