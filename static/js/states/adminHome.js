define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'admin_layout',
    url: '',
    templateUrl: 'partials/admin/home.html',
    controller: function($scope, $http, flash) {
      var timeoutId;

      $scope.loading = true;

      $scope.$on('$destory', function(){
        if (timeoutId) {
          window.cancelTimeout(timeoutId);
        }
      });

      function tick() {
        $http.get('/api/0/systemstats/').success(function(data){
          $scope.statusCounts = data.statusCounts;
          $scope.resultCounts = data.resultCounts;
        }).error(function(){
          flash('error', 'There was an error loading system statistics.');
        }).finally(function(){
          $scope.loading = false;
        });

        timeoutId = window.setTimeout(tick, 5000);
      }

      tick();
    }
  };
});
