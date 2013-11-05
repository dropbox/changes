define(['app', 'utils/duration'], function(app, duration) {
  app.directive('duration', function() {
    return function durationDirective(scope, element, attrs) {
      var $element = $(element);
      scope.$watch(attrs.duration, function(value) {
        element.text(duration(value));
      });
    }
  });
});
