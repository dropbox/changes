define(['app'], function(app) {
  'use strict';

  app.directive('prettyJson', function() {
    return function prettyJsonDirective(scope, element, attrs) {
      var result = JSON.stringify(scope.$eval(attrs.prettyJson), undefined, 2);
      element.text(result);
    };
  });
});
