define(['app'], function(app) {
  'use strict';

  app.controller('planDetailsCtrl', ['initial', '$scope', 'collection', function(initial, $scope, Collection) {
    $scope.plan = initial.data;
    $scope.projectList = new Collection($scope, initial.data.projects);
    $scope.stepList = new Collection($scope, initial.data.steps);
  }]);
});
