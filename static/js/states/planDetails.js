/*jshint -W024 */

define(['app'], function(app) {
  'use strict';

  return {
    parent: 'plans',
    url: ':plan_id/',
    templateUrl: 'partials/plan-details.html',
    controller: function($http, $scope, planData, Collection) {
      $scope.plan = planData.data;
      $scope.projectList = new Collection($scope, planData.data.projects);
      $scope.stepList = new Collection($scope, planData.data.steps);

      $scope.saveStep = function(step) {
        if (step.saving === true) {
          return;
        }
        step.saving = true;
        $http.post('/api/0/steps/' + step.id + '/', angular.copy(step)).success(function(data){
          step.showForm = false;
          angular.extend(step, data);
        }).error(function(data){
          alert('An error ocurred, and we have yet to implement a way to tell you about it.');
        }).finally(function(){
          step.saving = false;
        });
      };

      $scope.removeStep = function(step) {
        console.log('Coming soon!');
      };

      $scope.removeProject = function(project) {
        console.log('Coming soon!');
      };

    },
    resolve: {
      planData: function($http, $stateParams) {
        return $http.get('/api/0/plans/' + $stateParams.plan_id + '/');
      }
    }
  };
});
