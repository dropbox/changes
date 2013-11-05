define(['app'], function (app) {
  app.filter('truncate', function(){
    return function(input, length) {
      if (input.length < length) {
        return input;
      }

      var chars = length - 3,
          front = Math.ceil(chars / 2),
          back = Math.floor(chars / 2);

      return input.substr(0, front) + '...' + input.substr(input.length - back);
    }
  });
});
