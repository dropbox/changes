function BuildListCtrl($scope, $http) {
  $scope.builds = [];

  $http.get('/api/0/builds/').success(function(data) {
    $scope.builds = data.builds;
  });

  $scope.timeSince = function timeSince(date) {
    return moment.utc(date).fromNow();
  };

  function addBuild(build) {
    $scope.$apply(function() {
      var updated = false, build_id = build.id;
      if ($scope.builds.length > 0) {
        var result = $.grep($scope.builds, function(e){ return e.id == build_id; });
        if (result.length > 0) {
          var item = result[0];
          for (attr in build) {
            item[attr] = build[attr];
          }
          updated = true;
        }
      }
      if (!updated) {
        $scope.builds.unshift(build);
      }
    });
  }

  function subscribe() {
    if (window.stream) {
      console.log('[Stream] closing connection');
      window.stream.close()
    }
    console.log('[Stream] Initiating connection');

    window.stream = new EventSource('/api/0/stream/');
    window.stream.onopen = function(e) {
      console.log('[Stream] Connection opened');
    }
    window.stream.onerror = function(e) {
      console.log('[Stream] Error!');
    }
    window.stream.onmessage = function(e) {
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

  $scope.timeSince = function timeSince(date) {
    return moment.utc(date).fromNow();
  };

}
