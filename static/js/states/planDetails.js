/*jshint -W024 */

define(['app'], function(app) {
  'use strict';

  return {
    parent: 'plans',
    url: ':plan_id/',
    templateUrl: 'partials/plan-details.html',
    controller: function($http, $scope, planData, Collection) {
      $scope.plan = planData;
      $scope.projectList = new Collection($scope, planData.projects);
      $scope.stepList = new Collection($scope, planData.steps);

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
          angular.extend(step, data);
        }).error(function(data){
          alert('An error ocurred, and we have yet to implement a way to tell you about it.');
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
          alert('An error ocurred, and we have yet to implement a way to tell you about it.');
        }).finally(function(){
          step.saving = false;
        });
      };

      $scope.removeProject = function(project) {
        console.log('Coming soon!');
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
