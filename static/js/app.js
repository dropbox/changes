define([
  'angular',
  'angularLinkify',
  'angularRoute',
  'angularSanitize'
  // 'angularAnimate',
  ], function (angular) {
    return angular.module('app', [
      'linkify',
      'ngRoute',
      'ngSanitize'
      // 'ngAnimate',
    ]);
});
