require(['angular', 'notify'], function(angular) {
  'use strict';

  angular.module('notify', [])
    .factory('notify', function(){
      $.notify.addStyle("plain", {
        html: "<div>\n<span data-notify-html></span>\n</div>"
      });

      $.notify.defaults({
        position: 'bottom right',
        style: 'plain'
      });

      return function(html, className) {
        $("#my-builds").notify(html, {
          className: className || 'info'
        });
      };
    });
});
