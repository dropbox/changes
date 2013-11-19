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
        $scope.newSlowTestGroups = data.newSlowTestGroups;
      });

  }]);
});
