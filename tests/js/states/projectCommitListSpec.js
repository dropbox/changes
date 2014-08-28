define(['app', 'states/layout', 'states/projectDetails',
        'states/projectCommitList'], function(app, LayoutState,
         ProjectDetailsState, ProjectCommitListState) {

  beforeEach(module('app'));

  describe('Test Project Commit List ensureDefaults', function() {
    it('should not add default branch parameter',
      inject(function($filter) {
        // Don't add branch if the repository doesn't have any branches
        var params = {};
        ProjectCommitListState.custom.ensureDefaults($filter('lowercase'), params, {});
        expect(params.branch).to.not.be.ok;

        // Don't add branch unless the repository has names
        var branch = { defaultBranch: 'imabranch' };
        ProjectCommitListState.custom.ensureDefaults($filter('lowercase'), params, branch);
        expect(params.branch).to.not.be.ok;
      })
    );

    it('should add default branch',
      inject(function($filter) {
        // Add the branch if the repository doesn't have any branches
        var params = {};
        var branch = { defaultBranch: 'imabranch', branches: [ {name: 'imabranch'} ] };
        ProjectCommitListState.custom.ensureDefaults($filter('lowercase'), params, branch);
        expect(params.branch).to.equal('imabranch');

        // Keep the existing branch if it's already specified
        branch = {
          defaultBranch: 'ignore_branch',
          branches: [ {name: 'imabranch'}, {name: 'ignore_branch'} ]
        };
        ProjectCommitListState.custom.ensureDefaults($filter('lowercase'), params, branch);
        expect(params.branch).to.equal('imabranch');

        // Keep the existing branch even if it's not the names list
        ProjectCommitListState.custom.ensureDefaults($filter('lowercase'), params, {});
        expect(params.branch).to.equal('imabranch');
      })
    );

    it('should lower branch name',
      inject(function($filter) {
        var params = {};
        var branch = { defaultBranch: 'MASTER', branches: [ {name: 'MASTER'} ] };
        ProjectCommitListState.custom.ensureDefaults($filter('lowercase'), params, branch);
        expect(params.branch).to.equal('master');

        params = { branch: 'MASTER' };
        branch.defaultBranch = 'foo';
        ProjectCommitListState.custom.ensureDefaults($filter('lowercase'), params, branch);
        expect(params.branch).to.equal('master');
      })
    );
  });
});
