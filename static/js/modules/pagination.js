define(['app'], function(app, Dial) {
  'use strict';

  app.factory('pagination', function() {
    // TODO(dcramer): we should clean this up so the filters are just handled internally by a results list
    return {
      create: function(results, options) {
        if (options === undefined) {
          var options = {};
        }
        var perPage = options.perPage || 25;
        var paginator = {
          numPages: Math.ceil(results.length / perPage),
          perPage: perPage,
          page: 0,
          offset: 0
        };

        paginator.prevPage = function() {
          if (paginator.page > 0) {
            paginator.page -= 1;
          }
          paginator.setOffset();
        };

        paginator.nextPage = function() {
          if (paginator.page < paginator.numPages - 1) {
            paginator.page += 1;
          }
          paginator.setOffset();
        };

        paginator.jumpToPage = function(num) {
          if (num >= 0 && num <= paginator.numPages - 1) {
            paginator.page = num;
          }
          paginator.setOffset();
        };

        paginator.setOffset = function() {
          paginator.offset = paginator.page * paginator.perPage;
        };

        return paginator;
      }
    }
  })
  .filter('startFrom', function() {
     return function(input, start) {
       return input.slice(+start);
     }
  })
  .filter('range', function() {
    return function(input, total) {
      total = parseInt(total);
      for (var i = 0; i < total; i++) {
        input.push(i);
      }
      return input;
    }
  });
});
