define([
  'angular',
  'app'
], function(angular, app) {
  'use strict';

  return {
    parent: 'layout',
    url: '/tasks/:task_id/',
    templateUrl: 'partials/task-details.html',
    controller: function($scope, $http, taskData, PageTitle) {
      $scope.task = taskData;
      $scope.taskArgs = angular.toJson(taskData.args, true);

      PageTitle.set('Task ' + $scope.task.id);
    },
    resolve: {
      taskData: function($http, $stateParams) {
        return $http.get('/api/0/tasks/' + $stateParams.task_id + '/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
