(function(){
  'use strict';

  define(['app'], function(app) {
    app.directive('buildCommentList', function($filter, $http, $timeout) {
      var Comment = function(data) {
        this.html = $filter('linkify')($filter('escape')(data.text));
        this.user = data.user;
        this.dateCreated = data.dateCreated;
      };

      return {
        templateUrl: 'partials/includes/build-comment-list.html',
        restrict: 'A',
        replace: true,
        scope: {
          build: '=buildCommentList'
        },
        link: function (scope, element, attrs) {
          var endpoint = '/api/0/builds/' + scope.build.id + '/comments/';

          scope.commentsLoaded = false;
          scope.commentList = [];
          scope.commentFormVisible = false;
          scope.commentFormData = {};

          scope.saveComment = function(){
            if (!scope.commentFormData.text.length) {
              return;
            }

            $http.post(endpoint, scope.commentFormData).success(function(data){
              scope.commentList.unshift(new Comment(data));

              scope.commentFormData = {};
              scope.commentFormVisible = false;
            });
          };

          scope.handleKeypress = function($event){
            if ($event.which == 13 && !$event.shiftKey) {
              scope.saveComment();
              return false;
            }
          };

          $http.get(endpoint).success(function(data){
            scope.commentList = $.map(data, function(c) { return new Comment(c); });
            scope.commentsLoaded = true;
          });
        }
      };
    });
  });
})();
