define(['app'], function (app) {
  app.filter('orderByBuild', function(){
    return function(input) {
      function getBuildScore(object) {
        var value;
        if (object.dateStarted) {
          value = new Date(object.dateStarted).getTime();
        } else {
          value = new Date(object.dateCreated).getTime();
        }
        return value;
      }

      if (!angular.isObject(input)) return input;

      var arr = [];

      for(var objectKey in input) {
        arr.push(input[objectKey]);
      }

      arr.sort(function(a, b){
        return getBuildScore(b) - getBuildScore(a);
      });

      return arr;
    }
  });
});
