/*jshint -W024 */

define(['app'], function(app) {
  'use strict';

  function getFormData(planData) {
    return {
      name: planData.name
    };
  }

  return {
    parent: 'admin_layout',
    url: 'plans/:plan_id/',
    templateUrl: 'partials/admin/plan-details.html',
    controller: function($http, $scope, planData, planOptionData, Collection, flash) {
      var booleans = {
        "build.expect-tests": 1
      }, options = {};

      for (var key in planOptionData) {
        var value = planOptionData[key];
        if (booleans[key]) {
          value = parseInt(value, 10) == 1;
        }
        options[key] = value;
      }

      $scope.saveStep = function(step) {
        if (step.saving === true) {
          return;
        }
        step.saving = true;

        var url;
        if (step.id !== undefined) {
          url = '/api/0/steps/' + step.id + '/';
        } else {
          url = '/api/0/plans/' + planData.id + '/steps/';
        }

        var formData = {
          implementation: step.implementation,
          data: step.data,
          order: step.order,
          name: step.name,
        };

        for (var key in step.options) {
          formData[key] = step.options[key];
        }

        $http.post(url, formData).success(function(data){
          step.showForm = false;
          $.extend(true, step, data);
        }).error(function(data){
          flash('error', data.message);
        }).finally(function(){
          step.saving = false;
        });
      };

      $scope.addStep = function() {
        $scope.stepList.push({
          showForm: true,
          data: '{}',
          order: 0,
          name: 'Unsaved step',
          implementation: '',
          options: {
            'build.timeout': '0'
          }});
      };

      $scope.removeStep = function(step) {
        if (step.saving === true) {
          return;
        }
        step.saving = true;
        $http.delete('/api/0/steps/' + step.id + '/').success(function(data){
          $scope.stepList.popItem(step);
        }).error(function(data){
          flash('error', data.message);
        }).finally(function(){
          step.saving = false;
        });
      };

      $scope.addProject = function() {
        var data = {
          id: window.prompt('Enter the project ID or slug')
        };
        if (!data.id) {
          return;
        }

        $http.post('/api/0/plans/' + planData.id + '/projects/', data).success(function(data){
          $scope.projectList.push(data);
        }).error(function(data){
          flash('error', data.message);
        });
      };

      $scope.removeProject = function(project) {
        if (project.saving === true) {
          return;
        }

        project.saving = true;
        $http.delete('/api/0/plans/' + planData.id + '/projects/?id=' + project.id).success(function(data){
          $scope.projectList.popItem(project);
        }).error(function(data){
          flash('error', data.message);
        }).finally(function(){
          project.saving = false;
        });
      };

      $scope.savePlanSettings = function() {
        var options = angular.copy($scope.options);
        for (var key in options) {
          if (booleans[key]) {
            options[key] = options[key] ? '1' : '0';
          }
        }
        // TODO(dcramer): we dont correctly update the URL when the project slug
        // changes
        $http.post('/api/0/plans/' + planData.id + '/options/', options);
        $http.post('/api/0/plans/' + planData.id + '/', $scope.formData)
          .success(function(data){
            $.extend($scope.plan, data);
            $scope.formData = getFormData(data);
          });
          // TODO(dcramer): this is actually invalid
          $scope.planSettingsForm.$setPristine();
      };

      $scope.plan = planData;
      $scope.projectList = new Collection(planData.projects);
      $scope.stepList = new Collection(planData.steps);
      $scope.options = options;
      $scope.formData = getFormData(planData);
    },
    resolve: {
      planData: function($http, $stateParams) {
        return $http.get('/api/0/plans/' + $stateParams.plan_id + '/').then(function(response){
          return response.data;
        });
      },
      planOptionData: function($http, $stateParams) {
        return $http.get('/api/0/plans/' + $stateParams.plan_id + '/options/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
