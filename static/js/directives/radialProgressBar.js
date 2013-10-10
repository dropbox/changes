define(['app', 'utils/dial'], function(app, Dial) {
  app.directive('radialProgressBar', function() {
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

        if (!value) {
          return;
        }

        if (value == $element.val(value)) {
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

      attrs.$observe('radialProgressBar', function(value) {
        update(value)
      });
    }
  });
});
