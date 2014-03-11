define(['angular'], function(angular) {
  'use strict';

  angular.module('collection', [])
    .factory('Collection', function(){
      var defaults = {
        sortFunc: null,
        limit: null
      };

      function Collection($scope, collection, options) {
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
        this.$scope = $scope;

        if (collection !== undefined) {
          for (i=0; i<collection.length; i++) {
            this.push(collection[i]);
          }
        }

        return this;
      }

      Collection.prototype = [];

      Collection.prototype.constructor = Collection;

      // TODO(dcramer): we hsould probably make the behavior in updateItem actually
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

      Collection.prototype.updateItem = function updateItem(data) {
        this.$scope.$apply(function() {
          var updated = false,
              item_id = data.id,
              attr, result, item;

          if (this.length > 0) {
            result = $.grep(this, function(e){
              return e.id == item_id;
            });

            if (result.length > 0) {
              item = result[0];
              for (attr in data) {
                // ignore dateModified as we're updating this frequently and it causes
                // the dirty checking behavior in angular to respond poorly
                if (item[attr] != data[attr] && attr != 'dateModified') {
                  updated = true;
                  item[attr] = data[attr];
                }
                if (updated) {
                  item.dateModified = data.dateModified;
                }
              }
            }
          }

          if (!updated) {
            this.unshift(data);
          }
        }.bind(this));
      };

      return Collection;
    });
});
