define([
  'angular',
  'angularBootstrap',
  'angularHighlightjs',
  'angularLinkify',
  'angularLoadingBar',
  'angularRoute',
  'angularSanitize',
  'modules/barChart',
  'modules/collection',
  'modules/flash',
  'modules/stream',
  'filters/truncate',
  'jquery',
  'bootstrap'
  ], function (angular) {
    'use strict';

    return angular.module('app', [
      'barChart',
      'chieffancypants.loadingBar',
      'collection',
      'flash',
      'hljs',
      'linkify',
      'ngRoute',
      'ngSanitize',
      'stream',
      'ui.bootstrap'
    ]);
});
