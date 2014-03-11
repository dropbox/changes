define(['app'], function(app) {
  'use strict';

  return {
    parent: 'project_details',
    url: 'tests/',
    templateUrl: 'partials/project-test-list.html',
    controller: function($scope, testList) {
      $scope.tests = testList.data;
    },
    resolve: {
      testList: function($http, projectData) {
        return $http.get('/api/0/projects/' + projectData.data.id + '/tests/');
      }
    }
  };
});
