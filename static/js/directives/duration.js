define(['app', 'utils'], function(app, utils) {
  'use strict';

  app.directive('duration', function() {
    return function durationDirective(scope, element, attrs) {
      var $element = $(element);
      scope.$watch(attrs.duration, function(value) {
        if (value === null) {
          return 'n/a';
        }
        element.text(utils.time.duration(value));
      });
    };
  });
});
