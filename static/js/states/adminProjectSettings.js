define([
  'app'
], function(app) {
  'use strict';

  function getFormData(projectData) {
    return {
      name: projectData.name,
      slug: projectData.slug,
      repository: projectData.repository.url,
      status: projectData.status.id == 'inactive' ? 'inactive' : 'active'
    };
  }

  return {
    parent: 'admin_project_details',
    url: '',
    templateUrl: 'partials/admin/project-settings.html',
    controller: function($scope, $http, $state, $stateParams, flash, projectData) {
      var booleans = {
        "build.allow-patches": 1,
        "build.commit-trigger": 1,
        "green-build.notify": 1,
        "mail.notify-author": 1,
        "hipchat.notify": 1,
        "ui.show-coverage": 1,
        "ui.show-tests": 1,
        "phabricator.notify": 1
      }, options = {
        "build.branch-names": "*",
        "build.file-whitelist": ""
      };

      for (var key in projectData.options) {
        var value = projectData.options[key];
        if (booleans[key]) {
          value = parseInt(value, 10) == 1;
        }
        options[key] = value;
      }

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

      $scope.saveProjectSettings = function() {
        var options = angular.copy($scope.options);
        for (var key in options) {
          if (booleans[key]) {
            options[key] = options[key] ? '1' : '0';
          }
        }
        // TODO(dcramer): we dont correctly update the URL when the project slug
        // changes
        $http.post('/api/0/projects/' + $scope.project.slug + '/options/', options);
        $http.post('/api/0/projects/' + $scope.project.slug + '/', $scope.formData)
          .success(function(data){
            if ($scope.project.slug != data.slug) {
              return $state.go('admin_project_details', {project_id: data.slug});
            }
            $scope.project = data;
            $scope.formData = getFormData(data);
            $scope.projectSettingsForm.$setPristine();
            flash('success', 'Project saved successfully.');
          });
      };

      $scope.project = projectData;
      $scope.repo = projectData.repository;
      $scope.options = options;
      $scope.formData = getFormData(projectData);
    },
    resolve: {
      projectData: function($http, $stateParams) {
        return $http.get('/api/0/projects/' + $stateParams.project_id + '/')
          .then(function(response){
            return response.data;
          });
      }
    }
  };
});
