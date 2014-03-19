define(['angular'], function($) {
  'use strict';

  angular.module('changes.pageTitle', [])
    .service('PageTitle', function($rootScope, $window) {
      $rootScope.$on('$stateChangeStart', function(){
       $window.document.title = 'Changes';
      });

      return {
        set: function(documentTitle) {
          $window.document.title = documentTitle;
        },
        get: function() {
          return $window.document.title;
        }
      };
    });
});
