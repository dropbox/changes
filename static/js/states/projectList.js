define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'layout',
    url: "/projects/",
    templateUrl: 'partials/project-list.html',
    controller: function(projectList, $scope, Collection, Stream) {
      var entrypoint = '/api/0/projects/',
          stream;

      function sortByDateCreated(a, b){
        if (a.dateCreated < b.dateCreated) {
          return 1;
        } else if (a.dateCreated > b.dateCreated) {
          return -1;
        } else {
          return 0;
        }
      }

      function getProjectClass(project) {
        if (project.lastBuild) {
          return 'result-' + project.lastBuild.result.id;
        }
        return 'result-unknown';
      }

      function addBuild(data) {
        var project_id = data.project.id,
            result, project;

        if (data.source && data.source.patch) {
          return;
        }

        result = $.grep($scope.projects, function(e){
          return e.id == project_id;
        });
        if (!result.length) {
          // project not found
          return;
        }

        project = result[0];

        if (data.status.id != 'finished') {
          // not finished, so not relevant
          return;
        }

        // older than the 'current' last build
        if (!project.lastBuild || data.dateCreated < project.lastBuild.dateCreated) {
          return;
        }

        $scope.$apply(function() {
          project.lastBuild = data;
        });
      }

      $scope.getProjectClass = getProjectClass;
      $scope.projects = new Collection($scope, projectList.data);

      stream = new Stream($scope, entrypoint);
      stream.subscribe('project.update', $scope.projects.updateItem);
      stream.subscribe('build.update', addBuild);
    }
  };
});
