var Buildbox = angular.module('Buildbox', []);

function BuildListCtrl($scope, $http) {
  $scope.builds = [];

  $http.get('/api/0/builds/').success(function(data) {
    $scope.builds = data.builds;
  });

  $scope.failedFilter = function(test) {
    return test ? (test.status == 2 || test.status == 3) : false;
  };

  $scope.timeSinceBuild = function(build) {
    return moment.utc(build.created_date).fromNow();
  };

  $scope.displayDate = function(build) {
    return build ? moment(build.created_date).format("dddd, MMMM Do YYYY, h:mm:ss a") : '';
  };

  // function add_or_update_build(data) {
  //   $scope.$apply(function() {
  //     var updated = false, build_id = data.build_id;
  //     if ($scope.builds.length > 0) {
  //       var result = $.grep($scope.builds, function(e){ return e.build_id == build_id; });
  //       if (result.length > 0) {
  //         var item = result[0];
  //         for (attr in data) {
  //           item[attr] = data[attr];
  //         }
  //         updated = true;
  //       }
  //     }
  //     if (!updated) {
  //       $scope.builds.unshift(data);
  //     }
  //   });
  // }

  // function server_sent_events() {
  //   var source = new EventSource('/stream');
  //   // source.onopen = function(e) {
  //   //   console.log('[Stream] Connection opened');
  //   // }
  //   // source.onerror = function(e) {
  //   //   console.log('[Stream] Error!');
  //   // }
  //   source.onmessage = function(e) {
  //     // console.log('[Stream] Received event: ' + e.data);
  //     data = $.parseJSON(e.data);
  //     add_or_update_build(data);
  //   };
  // }

  // server_sent_events();
}
