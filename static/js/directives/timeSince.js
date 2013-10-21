define(['app', 'moment'], function(app, moment) {
  app.directive('timeSince', ['$timeout', function($timeout) {
    return function timeSince(scope, element, attrs) {
      var $element = $(element);

      function tick(){
      	value = scope.$eval(attrs.timeSince);
        element.text(moment.utc(value).fromNow());
        $timeout(tick, 500);
      }

      scope.$watch(attrs.timeSince, function(value){
      	element.text(moment.utc(value).fromNow());
      });

      tick();
    }
  }]);
});
