define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'layout',
    url: '/tasks/:task_id/',
    templateUrl: 'partials/task-details.html',
    controller: function($scope, $http, taskData, PageTitle) {
      $scope.task = taskData.data;

      PageTitle.set('Task ' + $scope.task.id);
    },
    resolve: {
      taskData: function($http, $stateParams) {
        return $http.get('/api/0/tasks/' + $stateParams.task_id + '/');
      }
    }
  };
});
