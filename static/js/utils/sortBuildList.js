(function(){
  'use strict';

  define(['utils/sortArray'], function(sortArray) {
    return function sortBuildList(arr) {
      function getBuildScore(object) {
        return [-new Date(object.dateCreated).getTime()];
      }

      return sortArray(arr, getBuildScore);
    };
  });
})();
