/*jshint -W024 */

define(['app'], function(app) {
  'use strict';

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

      $scope.plan = planData;
      $scope.projectList = new Collection(planData.projects);
      $scope.stepList = new Collection(planData.steps);
      $scope.options = options;

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
        $http.post(url, angular.copy(step)).success(function(data){
          step.showForm = false;
          $.extend(true, step, data);
        }).error(function(data){
          console.log(data);
          flash('error', data.message);
        }).finally(function(){
          step.saving = false;
        });
      };

      $scope.addStep = function() {
        $scope.stepList.push({showForm: true, data: '{}', order: 0, name: 'Unsaved step'});
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

      $scope.saveOption = function(option) {
        var value, data = {};

        if (booleans[option]) {
          value = $scope.options[option] ? '1' : '0';
        } else {
          value = $scope.options[option];
        }

        data[option] = value;

        $http.post('/api/0/plans/' + planData.id + '/options/', data);
      };

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
