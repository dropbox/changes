define([
    'app',
    'utils/chartHelpers',
    'utils/duration',
    'utils/escapeHtml',
    'utils/sortBuildList',
    'directives/radialProgressBar',
    'directives/timeSince'], function(app, chartHelpers, duration, escapeHtml, sortBuildList) {
  app.controller('projectLeaderboardCtrl', ['$scope', 'initialProject', '$http', '$routeParams', 'stream', function($scope, initialProject, $http, $routeParams, Stream) {
    'use strict';

    $http.get('/api/0/projects/' + $routeParams.project_id + '/testgroups/')
      .success(function(data){
        var bs = data.buildStats;

        bs.numBuilds = bs.numFailed + bs.numPassed;
        if (bs.numBuilds > 0) {
          bs.percentPassed = Math.round(bs.numPassed / bs.numBuilds * 100);
        } else {
          bs.percentPassed = null;
        }

        bs.previousPeriod.numBuilds = bs.previousPeriod.numFailed + bs.previousPeriod.numPassed;
        if (bs.previousPeriod.numBuilds > 0) {
          bs.previousPeriod.percentPassed = Math.round(bs.previousPeriod.numPassed / bs.previousPeriod.numBuilds * 100);
        } else {
          bs.previousPeriod.percentPassed = null;
        }

        $scope.buildStats = bs
        $scope.newSlowTestGroups = data.newSlowTestGroups;
      });

  }]);
});
