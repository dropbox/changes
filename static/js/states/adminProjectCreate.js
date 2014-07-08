define(['app', 'bloodhound'], function(app, Bloodhound) {
  'use strict';

  return {
    parent: 'admin_layout',
    url: 'new/project/',
    templateUrl: 'partials/admin/project-create.html',
    controller: function($scope, $http, $state) {
      $scope.searchRepositories = function(value) {
        return $http.get('/api/0/repositories/', {
          params: {
            query: value
          }
        }).success(function(data){
          var results = [];
          angular.forEach(data, function(item){
            results.push(item.url);
          });
          return results;
        });
      };

      var bloodhound = new Bloodhound({
        datumTokenizer: function(d) { return Bloodhound.tokenizers.whitespace(d.url); },
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: '/api/0/repositories/?query=%QUERY'
      });
      bloodhound.initialize();

      $scope.repoTypeaheadData = {
        displayKey: 'url',
        source: bloodhound.ttAdapter()
      };

      $scope.createProject = function() {
        $http.post('/api/0/projects/', $scope.project)
          .success(function(data){
            return $state.go('admin_project_settings', {project_id: data.slug});
          });
      };

      $scope.project = {};
    }
  };
});
