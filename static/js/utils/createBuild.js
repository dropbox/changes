define([], function() {
  'use strict';

  return function createBuild(http, state, flash, buildData) {
    http.post('/api/0/builds/', buildData)
      .success(function(data) {
        if (data.length === 0) {
          flash('error', 'Unable to create a new build.');
        } else if (data.length > 1) {
          flash('success', data.length + ' new builds created.');
          return state.go('project_details');
        } else {
          return state.go('build_details', {build_id: data[0].id});
        }
      })

      .error(function(data){
        if (data && data.error) {
          flash('error', data.error);
        } else {
          flash('error', 'Unable to create a new build.');
        }
      });
  };
});
