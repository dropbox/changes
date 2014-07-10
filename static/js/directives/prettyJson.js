define(['app'], function(app) {
  'use strict';

  app.directive('prettyJson', function() {
    return function prettyJsonDirective(scope, element, attrs) {
      var result = JSON.stringify(attrs.prettyJson, undefined, 2).slice(1, -1);
      element.text(result);
    };
  });
});
