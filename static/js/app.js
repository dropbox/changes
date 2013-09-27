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
  }]).
  directive('ngRadialProgressBar', function() {
    return {
      restrict: 'A',
      replace: false,
      link: function radialProgressBarLink(scope, element, attrs) {
        var $element = $(element),
            $parent = $element.parent(),
            $knob;

        function getResultColor(result) {
          switch (result) {
            case 'failed':
            case 'errored':
            case 'timedout':
              return '#d9322d';
            case 'passed':
              return '#58488a';
            default:
              return '#58488a';
          }
        }

        function update(value) {
          value = parseInt(value, 10);

          if (!value) {
            return;
          }

          if (value == $element.val(value)) {
            return;
          }

          if (value === 100) {
            $parent.removeClass('active');
            if ($knob) {
              $parent.empty();
              delete $knob;
            }
          } else {
            $parent.addClass('active');
            if (!$knob) {
              $knob = $element.knob({
                readOnly: true,
                displayInput: false,
                width: $element.width(),
                height: $element.height(),
                fgColor: getResultColor(attrs.result),
                thickness: 0.2
              });

              attrs.$observe('result', function(value) {
                $knob.trigger('configure', {
                  'fgColor': getResultColor(value)
                });
              });
            }
            $knob.val(value).trigger('change');
          }
        }

        update(attrs.value);

        attrs.$observe('value', function(value) {
          update(value)
        });
      }
    }
  });
