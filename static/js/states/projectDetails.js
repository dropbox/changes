define([
  'app'
], function(app) {
  'use strict';

  return {
    abstract: true,
    parent: 'projects',
    url: ':project_id/',
    templateUrl: 'partials/project-details.html',
    controller: function($scope, $rootScope, $http, $stateParams, projectData) {
      $scope.project = projectData.data;

      $rootScope.activeProject = $scope.project;
      $rootScope.pageTitle = $scope.project.name;
    },
    resolve: {
      projectData: function(projectList, $http, $q, $location, $stateParams) {
          var deferred = $q.defer();
          var selected = $.grep(projectList.data, function(node){
              return node.slug == $stateParams.project_id;
          })[0];
          if (!selected) {
              // TODO(dcramer): show error message
              deferred.reject();
              $location.path('/');
          } else {
              // refresh the data to attempt correctness
              $http.get('/api/0/projects/' + selected.id + '/')
                  .success(function(data){
                      angular.extend(selected, data);
                      deferred.resolve({data: data});
                  })
                  .error(function(){
                      // TODO(dcramer): show error message
                      deferred.reject();
                      $location.path('/');
                  });
          }
          return deferred.promise;
      }
    }
  };
});
