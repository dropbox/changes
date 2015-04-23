define(['app', 'utils'], function(app, utils) {
  'use strict';

  // we use a shared timeout for the page loop to avoid
  // extremely large amounts of $digest cycles and wasteful
  // amounts of defers
  window.setInterval(function(){
    $('.ng-timesince').each(function(_, element){
      var $element = angular.element(element),
          value = $element.data('datetime');

      $element.text(utils.time.timeSince(value));
    });
  }, 1000);

  app.directive('timeSince', ['$timeout', function($timeout) {
    return function timeSince(scope, element, attrs) {
      var value = scope.$eval(attrs.timeSince);
      element.addClass('ng-timesince');
      element.data('datetime', value);
      element.attr('title', new Date(value));
      element.text(utils.time.timeSince(value));
    };
  }]);
});
