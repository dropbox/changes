define(['app'], function(app) {
  'use strict';

  beforeEach(module('app'));

  describe('truncate', function() {
    it('should trim when over length',
      inject(function(truncateFilter) {
        expect(truncateFilter('foo bar baz', 5)).to.equal('fo...');
      })
    );

    it('should do nothing at equal length',
      inject(function(truncateFilter) {
        expect(truncateFilter('foo bar', 7)).to.equal('foo bar');
      })
    );
  });

  describe('ltruncate', function() {
    it('should trim when over length',
      inject(function(ltruncateFilter) {
        expect(ltruncateFilter('foo bar baz', 5)).to.equal('...az');
      })
    );

    it('should do nothing at equal length',
      inject(function(ltruncateFilter) {
        expect(ltruncateFilter('foo bar', 7)).to.equal('foo bar');
      })
    );
  });

});
