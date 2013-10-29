define(['app'], function(app) {
  'use strict';

  app.controller('projectListCtrl', ['initial', '$scope', 'stream', function(initial, $scope, Stream) {
    var entrypoint = '/api/0/projects/',
        stream;

    $scope.projects = initial.data.projects;

    function sortByDateCreated(a, b){
      if (a.dateCreated < b.dateCreated) {
        return 1
      } else if (a.dateCreated > b.dateCreated) {
        return -1
      } else {
        return 0;
      }
    }

    function addBuild(data) {
      $scope.$apply(function() {
        var updated = false,
            item_id = data.id,
            attr, result, item, project;

        // identify the project that this build belongs to
        result = $.grep($scope.projects, function(e){ return e.id == data.project.id; });
        if (!result.length) {
        	return;
        }
        project = result[0];

        if (project.recentBuilds.length > 0) {
          result = $.grep(project.recentBuilds, function(e){ return e.id == item_id; });
          if (result.length > 0) {
            item = result[0];
            for (attr in data) {
              // ignore dateModified as we're updating this frequently and it causes
              // the dirty checking behavior in angular to respond poorly
              if (item[attr] != data[attr] && attr != 'dateModified') {
                updated = true;
                item[attr] = data[attr];
              }
              if (updated) {
                item.dateModified = data.dateModified;
              }
            }
          }
        }
        if (!updated) {
          project.recentBuilds.unshift(data);
          // TODO(dcramer): we shouldn't be constantly sorting this
          project.recentBuilds.sort(sortByDateCreated);
          project.recentBuilds = project.recentBuilds.slice(0, 3);
        }
      });
    }

    stream = Stream($scope, entrypoint);
    stream.subscribe('build.update', addBuild);
  }]);

});
