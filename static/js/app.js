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
  'modules/notify',
  'modules/stream'
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
      'notify',
      'stream',
      'ui.bootstrap'
    ]);
});
