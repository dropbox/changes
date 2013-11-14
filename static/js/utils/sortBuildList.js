define(['utils/sortArray'], function(sortArray) {
  'use strict';

  return function sortBuildList(arr) {
    function getBuildScore(object) {
      return new Date(object.dateCreated).getTime();
    }

    return sortArray(arr, getBuildScore);
  }
});
