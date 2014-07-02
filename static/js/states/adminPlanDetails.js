/*jshint -W024 */

define(['app'], function(app) {
  'use strict';

  return {
    parent: 'admin_layout',
    url: 'plans/:plan_id/',
    templateUrl: 'partials/admin/plan-details.html',
    controller: function($http, $scope, planData, Collection, flash) {
      $scope.plan = planData;
      $scope.projectList = new Collection(planData.projects);
      $scope.stepList = new Collection(planData.steps);

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

    },
    resolve: {
      planData: function($http, $stateParams) {
        return $http.get('/api/0/plans/' + $stateParams.plan_id + '/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
