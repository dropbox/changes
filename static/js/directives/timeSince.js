define(['app', 'moment'], function(app, moment) {
  app.directive('timeSince', function() {
    return function timeSince(scope, element, attrs) {
      var $element = $(element);
      scope.$watch(attrs.timeSince, function(value) {
        element.text(moment.utc(value).fromNow());
      });
    }
  });
});
