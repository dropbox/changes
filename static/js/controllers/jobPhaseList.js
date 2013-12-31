(function(){
  'use strict';

  define(['app'], function(app) {
    app.controller('jobPhaseListCtrl', [
        '$scope', '$rootScope', 'initialJob', 'initialPhaseList',
        function($scope, $rootScope, initialJob, initialPhaseList) {

      $scope.project = initialJob.data.project;
      $scope.job = initialJob.data.job;
      $scope.phaseList = initialPhaseList.data;

      $rootScope.activeProject = $scope.project;
    }]);
  });
})();
