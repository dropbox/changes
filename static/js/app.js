define([
  'angular',
  'angularLinkify',
  'angularRoute',
  'angularSanitize'
  // 'angularAnimate',
  ], function (angular) {
    'use strict';

    return angular.module('app', [
      'linkify',
      'ngRoute',
      'ngSanitize'
      // 'ngAnimate',
    ]);
});
