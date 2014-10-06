define(['app', 'utils/createBuild'], function(app, createBuild) {
  'use strict';

  beforeEach(module('app'));

  describe('createBuild', function() {

    var $http, $httpBackend;

    beforeEach(inject(function($injector) {
      // Set up the mock http service responses
      $httpBackend = $injector.get('$httpBackend');

      // Expose $http to use when making calls
      $http = $injector.get('$http');
     }));

    afterEach(function() {
      $httpBackend.verifyNoOutstandingExpectation();
      $httpBackend.verifyNoOutstandingRequest();
    });

    it('should flash error for failed post', function() {
      $httpBackend.whenPOST('/api/0/builds/').respond(400, '');

      var flash = sinon.spy();
      createBuild($http, {}, flash, {});
      $httpBackend.flush();

      expect(flash.calledOnce).to.be.true;
      expect(flash.alwaysCalledWith('error')).to.be.true;
    });

    it('should flash correct message for failed post', function() {
      $httpBackend.whenPOST('/api/0/builds/').respond(400, {error: 'foo_bar'});

      var flash = sinon.spy();
      createBuild($http, {}, flash, {});
      $httpBackend.flush();

      expect(flash.calledOnce).to.be.true;
      expect(flash.alwaysCalledWith('error')).to.be.true;
      expect(flash.getCall(0).args[1]).to.equal('foo_bar')
    });

    it('should flash error for no data returned', function() {
      $httpBackend.whenPOST('/api/0/builds/').respond(200, '');

      var flash = sinon.spy();
      createBuild($http, {}, flash, {});
      $httpBackend.flush();

      expect(flash.calledOnce).to.be.true;
      expect(flash.alwaysCalledWith('error')).to.be.true;
    });

    it('should redirect for one build created', function() {
      var buildInfo = { id: 12 };
      $httpBackend.whenPOST('/api/0/builds/').respond(200, [ buildInfo ]);

      var flash = sinon.spy();
      var state = {
        go: sinon.spy(),
      };
      createBuild($http, state, flash, {});
      $httpBackend.flush();

      expect(flash.callCount).to.equal(0);
      expect(state.go.callCount).to.equal(1);
      var stateGo = state.go.getCall(0);
      expect(stateGo.args[0]).to.equal('build_details');
      expect(stateGo.args[1].build_id).to.equal(buildInfo.id);
    });

    it('should flash and redirect for multiple builds created', function() {
      $httpBackend.whenPOST('/api/0/builds/').respond(200, [ {}, {} ]);

      var flash = sinon.spy();
      var state = {
        go: sinon.spy(),
      };
      createBuild($http, state, flash, {});
      $httpBackend.flush();

      expect(flash.calledOnce).to.be.true;
      expect(flash.getCall(0).args[0]).to.equal('success');

      expect(state.go.calledOnce).to.be.true;
      expect(state.go.getCall(0).args[0]).to.equal('project_details');
    });
  });
});
