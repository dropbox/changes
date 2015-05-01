define(['modules/flash'], function() {

  describe('flash', function() {

    it('should set message text, type and default dismissible state',
      inject(function(_$rootScope_, $controller, flash) {
        var testScope = _$rootScope_.$new();
        $controller('FlashCtrl', {$scope:testScope});

        flash('warning', 'msg');
        expect(testScope.messages[0].type).to.equal('warning');
        expect(testScope.messages[0].text).to.equal('msg');
        expect(testScope.dismissible).to.be.true;
      })
    );

    it('should set message dismissible to be false',
      inject(function(_$rootScope_, $controller, flash) {

        var testScope = _$rootScope_.$new();
        $controller('FlashCtrl', {$scope:testScope});

        flash('error', 'some mess', false);
        expect(testScope.dismissible).to.be.false;
      })
    );

    it('should set message dismissible to be true',
      inject(function(_$rootScope_, $controller, flash) {

        var testScope = _$rootScope_.$new();
        $controller('FlashCtrl', {$scope:testScope});

        flash('error', 'some mess', true);
        expect(testScope.dismissible).to.be.true;
      })
    );

  });
});
