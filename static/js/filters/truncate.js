(function(){
  'use strict';

  define(['app'], function (app) {
    app.filter('truncate', function(){
      return function(input, length) {
        length = length || 100;

        if (input.length < length) {
          return input;
        }

        return input.substr(0, length - 3) + '...';
      };
    });
  });
})();
