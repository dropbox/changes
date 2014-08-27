define(['app', 'states/layout', 'states/projectDetails',
        'states/projectCommitList'], function(app, LayoutState,
         ProjectDetailsState, ProjectCommitListState) {

  beforeEach(module('app'));

  describe('Test Project Commit List createRepositoryBranchData', function() {

    it('should handle no primary property',
      inject(function() {
        var rawBranchData = [ ];
        branchData = ProjectCommitListState.custom.createRepositoryBranchData(rawBranchData);
        expect(branchData).not.to.have.property('primary');

        rawbranchData = [ {'name': 'foo'}, {'name': 'bar'} ];
        branchData = ProjectCommitListState.custom.createRepositoryBranchData(rawBranchData);
        expect(branchData).not.to.have.property('primary');
      })
    );

    it('should add primary property',
      inject(function() {
        // Try master without default
        var rawBranchData = [ {'name': 'FOO'}, {'name': 'master'}, {'name': 'b/a:z'} ];
        branchData = ProjectCommitListState.custom.createRepositoryBranchData(rawBranchData);
        expect(branchData.primary).to.equal('master');

        // Try default without master
        rawBranchData = [ {'name': 'FOO'}, {'name': 'default'} ];
        branchData = ProjectCommitListState.custom.createRepositoryBranchData(rawBranchData);
        expect(branchData.primary).to.equal('default');

        // master overrides default
        rawBranchData = [ {'name': 'default'}, {'name': 'master'} ];
        branchData = ProjectCommitListState.custom.createRepositoryBranchData(rawBranchData);
        expect(branchData.primary).to.equal('master');
      })
    );

    it('should create names for each branch',
      inject(function() {
        var rawbranchData = [ ];
        branchData = ProjectCommitListState.custom.createRepositoryBranchData(rawbranchData);
        expect(branchData.names).to.have.length(0);

        rawbranchData = [ {'name': ''} ];
        branchData = ProjectCommitListState.custom.createRepositoryBranchData(rawbranchData);
        expect(branchData.names).to.have.length(0);

        rawbranchData = [ {'name': 'BAZ'}, {'name': '12345'}, {'name': '%:/'}];
        branchData = ProjectCommitListState.custom.createRepositoryBranchData(rawbranchData);
        expect(branchData.names).to.have.members(['BAZ', '12345', '%:/']);
      })
    );
  });

  describe('Test Project Commit List ensureDefaults', function() {
    it('should not add primary branch parameter',
      inject(function($filter) {
        // Don't add branch if the repository doesn't have any branches
        var params = {};
        ProjectCommitListState.custom.ensureDefaults($filter('lowercase'), params, {});
        expect(params.branch).to.not.be.ok;

        // Don't add branch unless the repository has names
        var branch = { primary: 'imabranch' };
        ProjectCommitListState.custom.ensureDefaults($filter('lowercase'), params, branch);
        expect(params.branch).to.not.be.ok;
      })
    );

    it('should add primary branch',
      inject(function($filter) {
        // Add the branch if the repository doesn't have any branches
        var params = {};
        var branch = { primary: 'imabranch', names: ['imabranch'] };
        ProjectCommitListState.custom.ensureDefaults($filter('lowercase'), params, branch);
        expect(params.branch).to.equal('imabranch');

        // Keep the existing branch if it's already specified
        branch = { primary: 'ignore_branch', names: ['imabranch', 'ignore_branch'] };
        ProjectCommitListState.custom.ensureDefaults($filter('lowercase'), params, branch);
        expect(params.branch).to.equal('imabranch');

        // Remove the branch if we move to a repository without names
        ProjectCommitListState.custom.ensureDefaults($filter('lowercase'), params, {});
        expect(params.branch).to.not.be.ok;
      })
    );

    it('should lower branch name',
      inject(function($filter) {
        var params = {};
        var branch = { primary: 'MASTER', names: ['MASTER'] };
        ProjectCommitListState.custom.ensureDefaults($filter('lowercase'), params, branch);
        expect(params.branch).to.equal('master');

        params = { branch: 'MASTER' };
        branch.primary = 'foo';
        ProjectCommitListState.custom.ensureDefaults($filter('lowercase'), params, branch);
        expect(params.branch).to.equal('master');
      })
    );
  });
});
