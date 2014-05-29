define([
  'app',
  'utils/parseLinkHeader'
], function(app, parseLinkHeader) {
  'use strict';

  return {
    parent: 'layout',
    url: '/tasks/',
    templateUrl: 'partials/task-list.html',
    controller: function($scope, $http, taskList, PageTitle) {
      function loadTaskList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.taskList = new Collection(data);
            $scope.pageLinks = parseLinkHeader(headers('Link'));
          });
      }

      $scope.loadPreviousPage = function() {
        $(document.body).scrollTop(0);
        loadTaskList($scope.pageLinks.previous);
      };

      $scope.loadNextPage = function() {
        $(document.body).scrollTop(0);
        loadTaskList($scope.pageLinks.next);
      };

      $scope.$watch("pageLinks", function(value) {
        $scope.nextPage = value.next || null;
        $scope.previousPage = value.previous || null;
      });

      $scope.pageLinks = parseLinkHeader(taskList.headers('Link'));
      $scope.taskList = taskList.data;

      PageTitle.set('Tasks');
    },
    resolve: {
      taskList: function($http) {
        return $http.get('/api/0/tasks/');
      }
    }
  };
});
