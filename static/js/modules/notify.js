(function() {
  'use strict';

  define(['angular', 'notify'], function(angular) {
    angular.module('notify', [])
      .factory('notify', function(){
        $.notify.addStyle("plain", {
          html: "<div>\n<span data-notify-text></span>\n</div>"
        });

        return function(text) {
          $("#my-builds").notify(text, {
              position: "bottom right",
              style: 'plain'
            }
          );
        };
      });
  });
})();
