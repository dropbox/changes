define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'job_details',
    url: 'logs/:source_id/',
    templateUrl: 'partials/job-log-details.html',
    controller: function($scope, $timeout, $http, $stateParams, jobData, logData, stream, flash) {
      var logChunkData = {
            text: '',
            size: 0,
            nextOffset: 0
          };

      function updateBuildLog(data) {
        var $el = $('#log-' + data.source.id + ' > .build-log'),
            source_id = data.source.id,
            chars_to_remove, lines_to_remove,
            frag;

        if (data.offset < logChunkData.nextOffset) {
          return;
        }
        logChunkData.nextOffset = data.offset + data.size;

        frag = document.createDocumentFragment();

        // add each additional new line
        $.each(data.text.split('\n'), function(_, line){
          var div = document.createElement('div');
          div.className = 'line';
          div.innerHTML = line;
          frag.appendChild(div);
        });

        logChunkData.text += data.text;
        logChunkData.size += data.size;

        $el.append(frag);
      }

      $scope.logSource = logData.source;
      $scope.step = logData.step;

      $timeout(function(){
        $.each(logData.chunks, function(_, chunk){
          updateBuildLog(chunk);
        });
      });

      stream.addScopedChannels($scope, [
        'logsources:' + $scope.job.id + ':' + $scope.logSource.id
      ]);
      stream.addScopedSubscriber($scope, 'buildlog.update', updateBuildLog);
    },
    resolve: {
      logData: function($http, $stateParams, jobData) {
        return $http.get('/api/0/jobs/' + jobData.data.id + '/logs/' + $stateParams.source_id + '?limit=0').then(function(response){
          return response.data;
        });
      }
    }
  };
});
