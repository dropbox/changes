if (window.stream === undefined) {
  streams = {};
}

Stream = {};
Stream.subscribe = function subscribe($scope, url, callback) {
  "use strict";

  // TODO(dcramer): currently only supports one subscriber per channel
  if (!window.streams) {
    window.streams = {};
  }

  if (window.streams[url]) {
    console.log('[Stream] Closing connection to ' + url);
    window.streams[url].close()
  }
  console.log('[Stream] Initiating connection to ' + url);

  $scope.$on('routeChangeStart', function(e){
    if (window.streams) {
      $.each(window.streams, function(_, stream){
        stream.close();
      });
    }
  });

  window.streams[url] = new EventSource(url + '?_=' + new Date().getTime());
  window.streams[url].onopen = function(e) {
    console.log('[Stream] Connection opened to ' + url);
  }
  window.streams[url].onmessage = function(e) {
    var data = $.parseJSON(e.data);
    callback(data);
  };
};

function ChangeListCtrl($scope, $http) {
  "use strict";

  $scope.changes = [];

  $http.get('/api/0/changes/').success(function(data) {
    $scope.changes = data.changes;
  });

  $scope.timeSince = function timeSince(date) {
    return moment.utc(date).fromNow();
  };

  function addChange(change) {
    $scope.$apply(function() {
      var updated = false,
          change_id = change.id,
          attr, result, item;

      if ($scope.changes.length > 0) {
        result = $.grep($scope.changes, function(e){ return e.id == change_id; });
        if (result.length > 0) {
          item = result[0];
          for (attr in change) {
            item[attr] = change[attr];
          }
          updated = true;
        }
      }
      if (!updated) {
        $scope.changes.unshift(change);
      }
    });
  }

  Stream.subscribe($scope, '/api/0/changes/', addChange);
}

function ChangeDetailsCtrl($scope, $http, $routeParams) {
  "use strict";

  $scope.change = null;

  $http.get('/api/0/changes/' + $routeParams.change_id + '/').success(function(data) {
    $scope.change = data.change;
  });

  $scope.timeSince = function timeSince(date) {
    return moment.utc(date).fromNow();
  };

  function updateChange(data){
    $scope.$apply(function() {
      $scope.change = change;
    });
  }

  Stream.subscribe($scope, '/api/0/changes/' + $routeParams.change_id + '/', updateChange);

  // TODO(dcramer): this probably isnt the right way to do this in Angular
  new BuildListCtrl($scope, $http, $routeParams);
}

function BuildListCtrl($scope, $http, $routeParams) {
  "use strict";

  $scope.builds = [];

  $http.get('/api/0/changes/' + $routeParams.change_id + '/builds/').success(function(data) {
    $scope.builds = data.builds;
  });

  $scope.timeSince = function timeSince(date) {
    return moment.utc(date).fromNow();
  };

  function addBuild(build) {
    $scope.$apply(function() {
      var updated = false,
          build_id = build.id,
          attr, result, item;

      if ($scope.builds.length > 0) {
        result = $.grep($scope.builds, function(e){ return e.id == build_id; });
        if (result.length > 0) {
          item = result[0];
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

  Stream.subscribe($scope, '/api/0/changes/' + $routeParams.change_id + '/builds/', addBuild);
}


function BuildDetailsCtrl($scope, $http, $routeParams) {
  "use strict";

  $scope.build = null;
  $scope.phases = [];
  $scope.tests = [];

  $http.get('/api/0/changes/' + $routeParams.change_id + '/builds/' + $routeParams.build_id + '/').success(function(data) {
    $scope.build = data.build;
    $scope.tests = data.tests;
    $scope.phases = data.phases;
  });

  $scope.timeSince = function timeSince(date) {
    return moment.utc(date).fromNow();
  };

  function updateBuild(data){
    $scope.$apply(function() {
      $scope.build = data;
    });
  }

  Stream.subscribe($scope, '/api/0/changes/' + $routeParams.change_id + '/builds/' + $routeParams.build_id + '/', updateBuild);
}
