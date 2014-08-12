(function(){
  'use strict';

  define(['app'], function(app) {
    app.directive('commitInfo', function() {
      var templateContent = '' +
          '<div>' +
            '<h5><a ui-sref="build_details({project_id: commit.project.slug, build_id: commit.id})">{{title}}</a></h5>' +
            '<div class="info">' +
              '<span ng-if="showProject"><a ui-sref="project_builds({project_id: commit.project.slug})">{{commit.project.name}}</a> &mdash;</span>' +
              '<span class="branch" ng-repeat="branch in commit.source.revision.branches" ng-if="showBranches">{{branch}}</span>' +
              '<a ui-sref="project_source_details({project_id: commit.project.slug, source_id: commit.source.id})">{{commit.target}}</a>' +
              '<span ng-if="commit.author">&mdash; {{commit.author.name}}</span>' +
              '<span ng-if="commit.stats.test_failures"> &mdash; <span style="color:red">{{commit.stats.test_failures}} test failures</span></span>' +
            '</div>' +
          '</div>';

      return {
        restrict: 'E',
        // Workaround for a bug in Angular 1.2.1: use template instead of templateUrl.
        //    For more details, see https://github.com/angular/angular.js/issues/2151.
        //templateUrl: 'partials/includes/commit-info.html',
        template: templateContent,
        scope: {
          commit: '=',
          title: '=',
          showBranches: '=',
          showProject: '=',
        },
        replace: true,
      };
    });
  });

})();
