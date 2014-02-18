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
      'linkify',
      'ngRoute',
      'ngSanitize',
      'notify',
      'pagination',
      'stream',
      'ui.bootstrap'
    ]);
});
