(function(){
  'use strict';

  define([], function() {
    return function sortArray(arr, score_fn, reverse) {
      if (reverse === undefined) {
        reverse = true;
      }

      arr.sort(function(a, b){
        var a_score = score_fn(a),
            b_score = score_fn(b),
            result = 0;

        for (var i = 0; i < a_score.length; i++) {
          if (a_score[i] < b_score[i]) {
            result = -1;
          }
          if (a_score[i] > b_score[i]) {
            result = 1;
          }
        }

        if (reverse) {
          reverse = result * -1;
        }
        return result;
      });

      return arr;
    };
  });
})();
