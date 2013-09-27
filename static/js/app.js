var Changes = angular.module('Changes', []).
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
            dial;

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
            if (dial) {
              $parent.empty();
              delete dial;
            }
          } else {
            $parent.addClass('active');
            if (!dial) {
              dial = new Dial($element, {
                width: $element.width(),
                height: $element.height(),
                fgColor: getResultColor(attrs.result),
                thickness: 0.2
              });

              attrs.$observe('result', function(value) {
                dial.set('fgColor', getResultColor(value));
              });
            }
            dial.val(value);
          }
        }

        update(attrs.value);

        attrs.$observe('value', function(value) {
          update(value)
        });
      }
    }
  });
