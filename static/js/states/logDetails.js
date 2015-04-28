define([
  'app'
], function(app) {
  'use strict';

  // Disable livescroll if log lines is larger than 10K.
  var MAX_LIVESCROLL_LOG_LINES = 10240;

  // Disable log altogether if #logLines >= 40K.
  var MAX_LOG_LINES = 40960;

  function getEndpoint(params) {
    return '/api/0/jobs/' + params.job_id + '/logs/' + params.source_id + '?limit=0';
  }

  return {
    parent: 'job_details',
    url: 'logs/:source_id/',
    templateUrl: 'partials/job-log-details.html',
    controller: function($scope, $timeout, $http, $stateParams, jobData, logData, flash) {
      var logChunkData = {
            size: 0,
            nextOffset: 0,
            lines: 0
          },
          liveScroll = false;

      function updateBuildLog(data) {
        var $el = $('.build-log'),
            source_id = data.source.id,
            chars_to_remove, lines_to_remove,
            frag;

        if (data.offset < logChunkData.nextOffset) {
          return;
        }

        frag = document.createDocumentFragment();

        // add each additional new line
        $.each(data.text.split('\n'), function(_, line){
          // Don't add new rows if we already have too many on screen
          if (logChunkData.lines >= MAX_LOG_LINES) {
            $(document.body).addClass('build-log-viewer-disabled');
            return;
          }

          var div = document.createElement('div');
          div.className = 'line';
          div.innerHTML = line;
          frag.appendChild(div);
          logChunkData.lines += 1;
        });

        $el.append(frag);

        // Disable livescroll if log file is too large.
        if (liveScroll && logChunkData.lines >= MAX_LIVESCROLL_LOG_LINES) {
          liveScroll = false;
          $(document.body).addClass('build-log-stream-disabled');
        }

        if (liveScroll) {
          window.scrollTo(0, document.body.scrollHeight);
        }
      }

      $('.btn-livescroll input[type=checkbox]').change(function(){
        var $el = $(this).parent();

        liveScroll = $(this).is(':checked');

        if (liveScroll) {
          $el.addClass('active');
        } else {
          $el.removeClass('active');
        }
      }).click(function(e){
        e.stopPropagation();
      }).change();

      $('.btn-livescroll').click(function(e){
        var $checkbox = $(this).find('input[type=checkbox]');

        e.preventDefault();

        $checkbox.prop('checked', !$checkbox.is(':checked')).change();
      }).click();

      $scope.logSource = logData.source;
      $scope.step = logData.source.step;
      $scope.MAX_LOG_LINES = MAX_LOG_LINES;

      $timeout(function(){
        $.each(logData.chunks, function(_, chunk){
          updateBuildLog(chunk);
        });
        logChunkData.nextOffset = logData.nextOffset;
      });

      function pollForChanges() {
        var url = getEndpoint($stateParams) + '&offset=' + logChunkData.nextOffset;

        $http.get(url, {
          ignoreLoadingBar: true
        }).success(function(data){
          $timeout(function(){
            $.each(data.chunks, function(_, chunk){
              updateBuildLog(chunk);
            });
            $.extend(true, $scope.logSource, data.source);
            $.extend(true, $scope.step, data.source.step);
            logChunkData.nextOffset = data.nextOffset;
          });

          if (data.chunks.length > 0 || data.source.step.status.id != 'finished') {
            window.setTimeout(pollForChanges, 1000);
          }
        }).error(function(){
          window.setTimeout(pollForChanges, 10000);
        });
      }

      $scope.$watch("job.status.id", function(value) {
        if (value == 'finished') {
          $(document.body).addClass('build-log-stream-inactive');
        }
      });

      window.setTimeout(pollForChanges, 1000);
    },
    resolve: {
      logData: function($http, $stateParams) {
        return $http.get(getEndpoint($stateParams)).then(function(response){
          return response.data;
        });
      }
    },
    onEnter: function(){
      $(document.body).addClass('build-log-container');
    },
    onExit: function(){
      $(document.body).removeClass('build-log-container');
      $(document.body).removeClass('build-log-stream-inactive');
      $(document.body).removeClass('build-log-stream-disabled');
      $(document.body).removeClass('build-log-viewer-disabled');
    }
  };
});
