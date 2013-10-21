define(['app'], function (app) {
  app.filter('wordwrap', function(){
    return function(input, break_after) {
      var span = '<span></span>',
          span_length = span.length;
      if (break_after === undefined) {
        var break_after = 10;
      }
      for (var i = break_after; i <= input.length; i += break_after) {
        input = input.slice(0, i) + span + input.slice(i);
        i += span.length;
      }
      return input;
    }
  });
});
