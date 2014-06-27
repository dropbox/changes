define([], function() {
  'use strict';

  return function sortArray(arr, score_fn, reverse) {
    arr.sort(function(a, b){
      var a_score = score_fn(a),
          b_score = score_fn(b),
          modifier = (reverse === true ? -1 : 1);

      for (var i = 0; i < a_score.length; i++) {
        if (a_score[i] < b_score[i]) {
          return -1 * modifier;
        }
        if (a_score[i] > b_score[i]) {
          return 1 * modifier;
        }
      }
      return 0;
    });

    return arr;
  };
});
