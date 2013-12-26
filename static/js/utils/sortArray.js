(function(){
  'use strict';

  define([], function() {
    return function sortArray(arr, score_fn) {
      arr.sort(function(a, b){
        var a_score = score_fn(a),
            b_score = score_fn(b);

        for (var i = 0; i < a_score.length; i++) {
          if (a_score[i] < b_score[i]) {
            return 1;
          }
          if (a_score[i] > b_score[i]) {
            return -1;
          }
        }
        return 0;
      });

      return arr;
    };
  });
})();
