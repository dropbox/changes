define(['app', 'utils/dial'], function(app, Dial) {
  app.directive('radialProgressBar', ['$timeout', function($timeout) {
    return function radialProgressBarLink(scope, element, attrs) {
      var $element = $(element),
          $parent = $element.parent(),
          dial;

      function getResultColor(result) {
        switch (result) {
          case 'failed':
          case 'errored':
          case 'timedout':
            return '#d9322d';
          case 'passed':
            return '#58488a';
          default:
            return '#58488a';
        }
      }

      function update(value) {
        value = parseInt(value, 10);

        if (value === null) {
          return;
        }

        if (value === 100) {
          $parent.removeClass('active');
          if (dial) {
            $parent.empty();
            delete dial;
          }
        } else {
          $parent.addClass('active');
          if (!dial) {
            dial = new Dial($element, {
              width: $element.width(),
              height: $element.height(),
              fgColor: getResultColor(attrs.result),
              thickness: 0.2
            });

            attrs.$observe('result', function(value) {
              dial.set('fgColor', getResultColor(value));
            });
          }
          dial.val(value);
        }
      }

      function tick() {
        var ts_start, ts_now, progress, is_finished;
        var is_finished = attrs.status == 'finished';

        if (is_finished) {
          progress = 100;
        } else {
          ts_start = new Date(attrs.dateStarted).getTime();
          if (!ts_start) {
            progress = 0;
          } else {
            ts_now = Math.max(new Date().getTime(), ts_start);
            progress = Math.min((ts_now - ts_start) / attrs.estimatedDuration * 100, 95);
          }
        }

        update(progress);

        if (!is_finished) {
          $timeout(tick, 500);
        }
      }

      tick();

      // attrs.$observe('radialProgressBar', function(value) {
      //   update(value)
      // });
    }
  }]);
});
