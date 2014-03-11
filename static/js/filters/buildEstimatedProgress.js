define(['app'], function(app) {
  'use strict';

  app.filter('buildEstimatedProgress', function(){
    return function(build) {
      if (build.status.id == 'finished') {
        return 100;
      }

      var ts_start = new Date(build.dateStarted).getTime();
      if (!ts_start) {
        return 0;
      }

      var ts_now = Math.max(new Date().getTime(), ts_start);
      return Math.min((ts_now - ts_start) / build.estimatedDuration * 100, 95);
    };
  });
});
