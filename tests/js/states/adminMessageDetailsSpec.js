define(['app', 'states/adminHome', 'states/adminLayout', 'states/adminMessageDetails'], function() {

  describe('Test Admin Details Page With Message', function() {

    // Mock out the message data (to mock API data returned)
    var mockMessageData = {id: 12, message: 'foo', dateCreated: '2015-04-24'};
    beforeEach(module('app', function($provide) {
        // For this test, we simulate there's a message defined
        $provide.value('adminMessageData', mockMessageData);
    }));

    // Mock out the HTTP service (to not hang on HTTP requests)
    var $http, $httpBackend;
    beforeEach(inject(function($injector) {
      // Set up the mock http service responses for common requests
      $httpBackend = $injector.get('$httpBackend');
      $httpBackend.whenGET('/api/0/projects/').respond(200, 'not_used');
      $httpBackend.whenGET('/api/0/auth/').respond(200, 'not_used');

      // Expose $http to use when making calls
      $http = $injector.get('$http');
    }));

    afterEach(function() {
      $httpBackend.verifyNoOutstandingExpectation();
      $httpBackend.verifyNoOutstandingRequest();
    });

    it('should update message without errors',
      inject(function(_$rootScope_, _$state_, $controller, $templateCache) {

        var scope = _$rootScope_.$new();
        var flash = sinon.spy();
        $controller('AdminMessageDetailsCtrl', {$http:$http, $scope:scope, flash:flash});
        $httpBackend.whenGET('/api/0/messages/').respond(200, mockMessageData);
        $httpBackend.flush();

        // Validate form input data is correctly set based on mockMessageData
        expect(scope.formData.message).to.equal(mockMessageData.message);
        expect(scope.messageData.message).to.equal(mockMessageData.message);

        // Try saving form with new message data
        scope.messageDetailsForm = { $setPristine: sinon.spy() };
        scope.formData.message = 'new+msg';
        scope.saveForm();

        // Validate saving form posts new data to the API and clears save bit
        $httpBackend.expectPOST('/api/0/messages/', scope.formData)
            .respond(200, mockMessageData);
        $httpBackend.flush();
        expect(scope.formData.message).to.equal(mockMessageData.message);
        expect(scope.messageDetailsForm.$setPristine.calledOnce).to.be.true;

        // Validate we also flashed a success message
        expect(flash.calledOnce).to.be.true;
        expect(flash.alwaysCalledWith('success')).to.be.true;

        // Try clearing the message
        scope.formData.message = '';
        scope.saveForm();
        $httpBackend.expectPOST('/api/0/messages/', scope.formData).respond(200, scope.formData);
        $httpBackend.flush();
        expect(scope.formData.message).to.equal('');

        // Validate we also flashed a success message
        expect(flash.calledTwice).to.be.true;
        expect(flash.alwaysCalledWith('success')).to.be.true;
      })
  )});

  describe('Test Admin Details Page With Null Message', function() {
    // Mock out the message data (to mock API data returned)
    beforeEach(module('app', function($provide) {
        // For this test, we simulate there's a message defined
        $provide.value('adminMessageData', null);
    }));

    // Mock out the HTTP service (to not hang on HTTP requests)
    var $http, $httpBackend;
    beforeEach(inject(function($injector) {
      // Set up the mock http service responses for common requests
      $httpBackend = $injector.get('$httpBackend');
      $httpBackend.whenGET('/api/0/projects/').respond(200, 'not_used');
      $httpBackend.whenGET('/api/0/auth/').respond(200, 'not_used');

      // Expose $http to use when making calls
      $http = $injector.get('$http');
    }));

    afterEach(function() {
      $httpBackend.verifyNoOutstandingExpectation();
      $httpBackend.verifyNoOutstandingRequest();
    });

    it('should update message without errors',
        inject(function(_$rootScope_, _$state_, $controller, $templateCache) {
          var scope = _$rootScope_.$new();
          var flash = sinon.spy();
          $httpBackend.whenGET('/api/0/messages/').respond(200, 'not_used');
          $controller('AdminMessageDetailsCtrl', {$http:$http, $scope:scope, flash:flash});
          $httpBackend.flush();

          // Validate we can load the page without an error
          expect(flash.callCount).to.equal(0);
          expect(scope.messageData).to.be.null;

          // Validate saving a message sends an empty string to the API
          scope.messageDetailsForm = { $setPristine: sinon.spy() };
          scope.saveForm();

          var expectedPost = { message: '' };
          var mockReply = {id: 1, message: '', dateCreated: '2015-04-24'};
          $httpBackend.expectPOST('/api/0/messages/', expectedPost).respond(200, mockReply);
          $httpBackend.flush();

          expect(scope.messageDetailsForm.$setPristine.calledOnce).to.be.true;
          expect(flash.calledOnce).to.be.true;
          expect(scope.messageData.message).to.equal(mockReply.message);
      }));
  });

  describe('Test Admin Details Page With Empty Message', function() {
    // Mock out the message data (to mock API data returned)
    var mockMessageData = {id: 12, message: '', dateCreated: '2015-04-24'};
    beforeEach(module('app', function($provide) {
        // For this test, we simulate there's a message defined
        $provide.value('adminMessageData', mockMessageData);
    }));

    // Mock out the HTTP service (to not hang on HTTP requests)
    var $http, $httpBackend;
    beforeEach(inject(function($injector) {
      // Set up the mock http service responses for common requests
      $httpBackend = $injector.get('$httpBackend');
      $httpBackend.whenGET('/api/0/projects/').respond(200, 'not_used');
      $httpBackend.whenGET('/api/0/auth/').respond(200, 'not_used');

      // Expose $http to use when making calls
      $http = $injector.get('$http');
    }));

    afterEach(function() {
      $httpBackend.verifyNoOutstandingExpectation();
      $httpBackend.verifyNoOutstandingRequest();
    });

    it('should set message without errors',
        inject(function(_$rootScope_, _$state_, $controller, $templateCache) {
          var scope = _$rootScope_.$new();
          var flash = sinon.spy();
          $httpBackend.whenGET('/api/0/messages/').respond(200, 'not_used');
          $controller('AdminMessageDetailsCtrl', {$http:$http, $scope:scope, flash:flash});
          $httpBackend.flush();

          // Validate we can load the page without an error
          expect(flash.callCount).to.equal(0);
          expect(scope.messageData.message).to.equal(mockMessageData.message);
          expect(scope.messageData.dateCreated).to.equal(mockMessageData.dateCreated);

          // Validate saving a message sends an empty string to the API
          scope.messageDetailsForm = { $setPristine: sinon.spy() };
          scope.saveForm();

          var expectedPost = { message: '' };
          var mockReply = {id: 1, message: '', dateCreated: '2015-04-24'};
          $httpBackend.expectPOST('/api/0/messages/', expectedPost).respond(200, mockReply);
          $httpBackend.flush();
        }));
  });
});
