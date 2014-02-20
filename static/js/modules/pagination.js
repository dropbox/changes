require(['angular'], function(angular) {
  'use strict';

  angular.module('pagination', [])
    .factory('pagination', function() {
      // TODO(dcramer): we should clean this up so the filters are just handled internally by a results list
      return {
        create: function(results, options) {
          if (options === undefined) {
            options = {};
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

          paginator.getPageRange = function(limit) {
            if (limit === undefined) {
              limit = 10;
            }

            var half = limit / 2;
            var start = Math.floor(paginator.page - half);
            var end = Math.ceil(paginator.page + half);

            if (start < 0) {
              end += (0 - start);
              start = 0;
            }
            if (end > paginator.numPages - 1) {
              if (start > 0) {
                start = Math.max(start - (end - paginator.numPages + 1), 0);
              }
              end = paginator.numPages - 1;
            }

            var output = [];
            for (var i = start; i <= end; i++) {
              output.push(i);
            }
            return output;
          };

          return paginator;
        }
      };
    })
    .filter('startFrom', function() {
       return function(input, start) {
         return input.slice(+start);
       };
    });
});
