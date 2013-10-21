define(['app'], function (app) {
  app.filter('escape', function(){
    return function(input) {
	  return $("<div>").text(input).html();
    }
  });
});
