
function BuildListCtrl($scope, $http) {
  $scope.builds = [];

  $http.get('/api/0/builds/').success(function(data) {
    $scope.builds = data.builds;
  });

  function addBuild(data) {
    $scope.$apply(function() {
      var updated = false, build_id = data.build_id;
      if ($scope.builds.length > 0) {
        var result = $.grep($scope.builds, function(e){ return e.build_id == build_id; });
        if (result.length > 0) {
          var item = result[0];
          for (attr in data) {
            item[attr] = data[attr];
          }
          updated = true;
        }
      }
      if (!updated) {
        $scope.builds.unshift(data);
      }
    });
  }

  function subscribe() {
    var source = new EventSource('/api/0/stream/');
    // source.onopen = function(e) {
    //   console.log('[Stream] Connection opened');
    // }
    // source.onerror = function(e) {
    //   console.log('[Stream] Error!');
    // }
    source.onmessage = function(e) {
      // console.log('[Stream] Received event: ' + e.data);
      data = $.parseJSON(e.data);
      addBuild(data);
    };
  }

  subscribe();
}


function BuildDetailsCtrl($scope, $http, $routeParams) {
  $scope.build = null;
  $scope.phases = [];
  $scope.tests = [];

  $http.get('/api/0/builds/' + $routeParams.build_id + '/').success(function(data) {
    $scope.build = data.build;
    $scope.tests = data.tests;
    $scope.phases = data.phases;
  });

}


var Buildbox = angular.module('Buildbox', []).
  config(['$routeProvider', function($routeProvider) {
  $routeProvider.
      when('/', {
        templateUrl: 'partials/build-list.html',
        controller: BuildListCtrl
      }).
      when('/projects/:project_id/builds/:build_id/', {
        templateUrl: 'partials/build-details.html',
        controller: BuildDetailsCtrl
      }).
      otherwise({redirectTo: '/'});
}]);
