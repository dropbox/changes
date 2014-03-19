define([
  'angular',
  'angularAnimate',
  'angularBootstrap',
  'angularHighlightjs',
  'ngInfiniteScroll',
  'angularLinkify',
  'angularLoadingBar',
  'angularRoute',
  'angularSanitize',
  'angularUIRouter',
  'modules/barChart',
  'modules/collection',
  'modules/flash',
  'modules/notify',
  'modules/pagination',
  'modules/stream'
  ], function (angular) {
    'use strict';

    return angular.module('app', [
      'barChart',
      'chieffancypants.loadingBar',
      'collection',
      'flash',
      'hljs',
      'infinite-scroll',
      'linkify',
      'ngAnimate',
      'ngRoute',
      'ngSanitize',
      'notify',
      'pagination',
      'stream',
      'ui.bootstrap',
      'ui.router'
    ]);
});
