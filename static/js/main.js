require(["config"], function(config){
  'use strict';

  require(["app", "angular", "routes"], function(app, angular){
    angular.bootstrap(document, ['app']);
  });
});
