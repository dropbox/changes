(function(){
  'use strict';

  define([], function() {
    return function parseLinkHeader(header) {
      if (header === null) {
        return {};
      }

      var header_vals = header.split(','),
          links = {};

      $.each(header_vals, function(_, val){
          var match = /<([^>]+)>; rel="([^"]+)"/g.exec(val);

          links[match[2]] = match[1];
      });

      return links;
    };
  });
})();
