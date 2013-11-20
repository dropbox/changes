define([
    'app',
    'utils/chartHelpers',
    'utils/duration',
    'utils/escapeHtml',
    'utils/sortBuildList',
    'directives/radialProgressBar',
    'directives/timeSince'], function(app, chartHelpers, duration, escapeHtml, sortBuildList) {
  app.controller('projectLeaderboardCtrl', [
      '$scope', '$rootScope', 'initialProject', 'initialTestData', '$http', '$routeParams', 'stream',
      function($scope, $rootScope, initialProject, initialTestData, $http, $routeParams, Stream) {
    'use strict';
      var bs = initialTestData.data.buildStats;

      if (bs.numBuilds > 0) {
        bs.percentPassed = Math.round(bs.numPassed / (bs.numFailed + bs.numPassed) * 100);
      } else {
        bs.percentPassed = null;
      }

      if (bs.previousPeriod.numBuilds > 0) {
        bs.previousPeriod.percentPassed = Math.round(bs.previousPeriod.numPassed / (bs.previousPeriod.numFailed + bs.previousPeriod.numPassed) * 100);
      } else {
        bs.previousPeriod.percentPassed = null;
      }

      if (bs.avgBuildTime && bs.previousPeriod.avgBuildTime) {
        bs.buildTimeChange = bs.avgBuildTime - bs.previousPeriod.avgBuildTime;
      } else {
        bs.buildTimeChange = null;
      }

      $scope.buildStats = bs
      $scope.newSlowTestGroups = initialTestData.data.newSlowTestGroups;
      $scope.project = initialProject.data.project;

      $rootScope.activeProject = $scope.project;
  }]);
});
