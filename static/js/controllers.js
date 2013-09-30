if (window.stream === undefined) {
  streams = {};
}

Stream = {};
Stream.subscribe = function subscribe(channel, callback) {
  "use strict";

  // TODO(dcramer): currently only supports one subscriber per channel
  var stream = window.streams[channel] || null;
  if (stream) {
    console.log('[Stream] closing connection to ' + channel);
    stream.close()
  }
  console.log('[Stream] Initiating connection to ' + channel);

  stream = new EventSource('/api/0/stream/?channel=changes');
  stream.onopen = function(e) {
    console.log('[Stream] Connection opened to ' + channel);
  }
  stream.onerror = function(e) {
    console.log('[Stream] Error on ' + channel);
  }
  stream.onmessage = function(e) {
    var data = $.parseJSON(e.data);
    callback(data);
  };
  window.streams[channel] = stream
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

  Stream.subscribe('changes', addChange);
}

function ChangeDetailsCtrl($scope, $http, $routeParams) {
  "use strict";

  $scope.change = null;
  $scope.builds = [];

  $http.get('/api/0/changes/' + $routeParams.change_id + '/').success(function(data) {
    $scope.change = data.change;
  });

  $http.get('/api/0/changes/' + $routeParams.change_id + '/builds/').success(function(data) {
    $scope.builds = data.builds;
  });

  $scope.timeSince = function timeSince(date) {
    return moment.utc(date).fromNow();
  };
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

  Stream.subscribe('builds', addBuild);
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
}
