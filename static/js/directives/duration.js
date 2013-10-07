define(['app', 'moment'], function(app, moment) {
  app.directive('duration', function() {
  	function round(value) {
  		return parseInt(value * 100, 10) / 100;
  	}

    return function duration(scope, element, attrs) {
      var $element = $(element);
      scope.$watch(attrs.duration, function(value) {
      	var result;
      	if (value > 7200000) {
      		result = round(value / 3600000) + 'h';
      	} else if (value > 120000) {
      		result = round(value / 60000) + 'm';
      	} else if (value > 1000) {
      		result = round(value / 1000) + 's';
      	} else {
      		result = parseInt(value, 10) + 'ms';
      	}

        element.text(result);
      });
    }
  });
});
