define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'layout',
    url: "/projects/",
    templateUrl: 'partials/project-list.html',
    controller: function(projectList, $scope, Collection, CollectionPoller) {
      function sortByDateCreated(a, b){
        if (a.dateCreated < b.dateCreated) {
          return 1;
        } else if (a.dateCreated > b.dateCreated) {
          return -1;
        } else {
          return 0;
        }
      }

      function getCoveragePercent(lines_covered, lines_uncovered) {
        var total_lines = lines_covered + lines_uncovered;
        if (!total_lines) {
          return 0;
        }
        return parseInt(lines_covered / total_lines * 100, 10);
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
        if (project.lastBuild && data.dateCreated < project.lastBuild.dateCreated) {
          return;
        }

        $scope.$apply(function() {
          project.lastBuild = data;
          if (data.result.id == 'passed') {
            project.lastPassingBuild = data;
          }
        });
      }

      projectList = projectList.data;
      $.each(projectList, function(_, project){
        var lastPassingBuild = project.lastPassingBuild;
        if (!lastPassingBuild) {
          return;
        }
        var linesCovered = lastPassingBuild.stats.lines_covered;
        var linesUncovered = lastPassingBuild.stats.lines_uncovered;
        project.hasCoverage = (linesCovered + linesUncovered > 0);
        project.coveragePercent = getCoveragePercent(linesCovered, linesUncovered);
      });

      $scope.getProjectClass = getProjectClass;
      $scope.projects = new Collection(projectList);

      var poller = new CollectionPoller({
        $scope: $scope,
        collection: $scope.projects,
        endpoint: '/api/0/projects/',
        shouldUpdate: function(item, existing) {
          if (!existing.lastBuild && !item.lastBuild) {
            return false;
          } else if (!existing.lastBuild) {
            return true;
          } else if (existing.lastBuild.dateCreated < item.lastBuild.dateCreated) {
            return true;
          } else if (existing.lastBuild.id == item.lastBuild.id &&
                     existing.lastBuild.dateModified < item.lastBuild.dateModified) {
            return true;
          }
        }
      });
    }
  };
});
