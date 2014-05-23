define(['angular'], function(angular) {
  'use strict';

  angular.module('collection', [])
    .factory('Collection', function(){
      var defaults = {
        sortFunc: null,
        limit: null,
        equals: function(item, other) {
          return item.id == other.id;
        }
      };

      function Collection(collection, options) {
        var i;

        Array.call(this);

        if (options === undefined) {
          options = {};
        }

        for (i in defaults) {
          if (options[i] === undefined) {
            options[i] = defaults[i];
          }
        }

        this.options = options;

        if (collection !== undefined) {
          for (i=0; i<collection.length; i++) {
            this.push(collection[i]);
          }
        }

        return this;
      }

      Collection.prototype = [];

      Collection.prototype.constructor = Collection;

      // TODO(dcramer): we should probably make the behavior in update actually
      // be part of push/unshift
      Collection.prototype.push = function push() {
        Array.prototype.push.apply(this, arguments);
        if (this.options.sortFunc) {
          this.options.sortFunc(this);
        }
        if (this.options.limit && this.length > this.options.limit) {
          this.splice(this.options.limit, this.length - this.options.limit);
        }
      };

      Collection.prototype.unshift = function unshift() {
        Array.prototype.unshift.apply(this, arguments);
        if (this.options.sortFunc) {
          this.options.sortFunc(this);
        }
        if (this.options.limit && this.length > this.options.limit) {
          this.splice(this.options.limit, this.length - this.options.limit);
        }
      };

      Collection.prototype.popItem = function remove(data) {
        var idx = this.indexOf(data);
        if (idx !== -1) {
          this.splice(idx, idx + 1);
          return;
        }
      };

      Collection.prototype.indexOf = function indexOf(data) {
        for (var i = 0; i < this.length; i++) {
          if (this.options.equals(this[i], data)) {
            return i;
          }
        }
        return -1;
      };

      Collection.prototype.extend = function extend(data) {
        for (var i = 0; i < data.length; i++) {
          this.update(data[i]);
        }
      };

      Collection.prototype.update = function update(data, create_missing) {
        if (create_missing === undefined) {
          create_missing = true;
        }
        var existing = this.indexOf(data);

        if (existing !== -1) {
          $.extend(true, this[existing], data);
          return;
        }
        if (create_missing) {
          this.unshift(data);
        }
      };

      return Collection;
    });
});
