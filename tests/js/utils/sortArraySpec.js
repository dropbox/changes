define(['app', 'utils/sortArray'], function(app, sortArray) {
  'use strict';

  beforeEach(module('app'));

  describe('sortArray', function() {
    it('should sort ascending', function() {
      var input = [{name: 'foo'}, {name: 'bar'}];
      var result = sortArray(input, function(object){
        return [object.name];
      });

      expect(result).to.equal(input);

      expect(result.length).to.equal(2);
      expect(result[0].name).to.equal('bar');
      expect(result[1].name).to.equal('foo');
    });

    it('should sort ascending with multiple values', function() {
      var input = [{name: 'foo', t: 1}, {name: 'bar', t: 1}];
      var result = sortArray(input, function(object){
        return [object.t, object.name];
      });

      expect(result).to.equal(input);

      expect(result.length).to.equal(2);
      expect(result[0].name).to.equal('bar');
      expect(result[1].name).to.equal('foo');
    });

    it('should sort descending', function() {
      var input = [{name: 'bar'}, {name: 'foo'}];
      var result = sortArray(input, function(object){
        return [object.name];
      }, true);

      expect(result).to.equal(input);

      expect(result.length).to.equal(2);
      expect(result[0].name).to.equal('foo');
      expect(result[1].name).to.equal('bar');
    });
  });
});
