define(['app', 'utils/time'], function(app, time) {
  'use strict';

  describe('duration', function() {
    it('should support milliseconds', function() {
      var result = time.duration(320);
      expect(result).to.equal('320 ms');

      var result = time.duration(1);
      expect(result).to.equal('1 ms');
    });

    it('should support seconds', function() {
      var result = time.duration(3200);
      expect(result).to.equal('3.2 sec');

      var result = time.duration(120000);
      expect(result).to.equal('120 sec');
    });

    it('should support minutes', function() {
      var result = time.duration(180000);
      expect(result).to.equal('3 min');

      var result = time.duration(360000);
      expect(result).to.equal('6 min');

      var result = time.duration(3600000);
      expect(result).to.equal('60 min');

      var result = time.duration(7200000);
      expect(result).to.equal('120 min');
    });

    it('should support hours', function() {
      var result = time.duration(14400000);
      expect(result).to.equal('4 hr');
    });
  });
});
