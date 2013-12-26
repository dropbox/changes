(function(){
  'use strict';

  define([], function () {
    var entityMap = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': '&quot;',
      "'": '&#39;'
    };

    return function escapeHtml(string) {
      return String(string).replace(/[&<>"']/g, function (s) {
        return entityMap[s];
      });
    };
  });
})();
