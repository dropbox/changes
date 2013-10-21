define(['app', 'moment'], function(app, moment) {
  app.directive('timeSince', ['$timeout', function($timeout) {
    return function timeSince(scope, element, attrs) {
      var $element = $(element),
          timeout_id;

      function tick(){
        value = scope.$eval(attrs.timeSince);
        element.text(moment.utc(value).fromNow());
        timeout_id = $timeout(tick, 500);
      }

      scope.$watch(attrs.timeSince, function(value){
      	element.text(moment.utc(value).fromNow());
      });

      element.bind('$destroy', function() {
        $timeout.cancel(timeout_id);
      });

      tick();
    }
  }]);
});
