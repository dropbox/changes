define(['app', 'states/adminHome', 'states/adminLayout'], function(app, AdminHomeState, AdminLayoutState) {
 
  beforeEach(module('app'));
  beforeEach(function() {
    module('app', function($provide) {
      // For this test, we simulate there's no user defined
      $provide.value('authData', authDataMock = {
      });
    });
  });

  describe('Test Admin Home Page', function() {
    it('should redirect to login when no user is defined',
      inject(function(_$rootScope_, _$state_, $controller, $templateCache) {
        
        // The mock window object will contain the redirected location
        var mockWindow = {
          location: {
            href: '/admin'
          }
        }

        // We don't really use these here, but we need to define them to mock the controller 
        scope = _$rootScope_.$new(); 
        stateparams = { };
        $controller('AdminLayoutCtrl', {$scope:scope, $stateParams:stateparams, $window:mockWindow})
        expect(mockWindow.location.href).to.equal('/auth/login/')
      })
    );
  });
});
