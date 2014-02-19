(function(root){
    require(["config"], function(config){
        require(["app", "angular", "routes"], function(app, angular){
            angular.bootstrap(document, ['app']);
        });
    });
})(this);
