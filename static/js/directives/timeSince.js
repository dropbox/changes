define([
  'app', 
  'utils', 
  'bootstrap/tooltip'
], function(app, utils, tooltip_func) {
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
      var tagname = element[0].tagName.toLowerCase();
      if (tagname == 'td' || tagname == 'dd') {
        var err = "applying the timeSince directive to <" + tagname + "> tags" +
          " can cause rendering issues. Instead, please put this on an" +
          " inner <span> tag";
        console.warn(err);
      }
      var value = scope.$eval(attrs.timeSince);
      element.addClass('ng-timesince');
      element.data('datetime', value);

      element.attr('title', (new Date(value)).toUTCString());
      element.attr('data-placement', 'left');
      tooltip_func.bind(element)();
    };
  }]);
});
