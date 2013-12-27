(function(console) {
  'use strict';

  angular.module('collection', [])
    .factory('collection', function(){
      function Collection($scope, collection) {
        if (collection !== undefined) {
          for (var i=0; i<collection.length; i++) {
            this.push(collection[i]);
          }
        }

        this.updateItem = function(data) {
          $scope.$apply(function() {
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
          });
        };
      }
      Collection.prototype = Array.prototype;

      return Collection;
    });
})(console);
