define(['app'], function(app) {
  'use strict';

  beforeEach(module('app'));

  describe('escape', function() {
    it('should escape tags',
      inject(function(escapeFilter) {
        expect(escapeFilter('<script>')).to.equal('&lt;script&gt;');
      })
    );
  });
});
