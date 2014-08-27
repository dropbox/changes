define(['angular', 'jquery'], function(angular, jQuery) {
  'use strict';

  angular.module('changes.paginator', ['collection'])
    .factory('Paginator', function($http, Collection) {

      var defaults = {
        poller: null,
        collection: null,
        transform: function(data) {
          return data;
        },
        onLoadBegin: function(url){},
        onLoadSuccess: function(url, data){},
        onLoadError: function(url, data){},
        onLoadComplete: function(url, data){}
      };

      function parseLinkHeader(header) {
        if (header === null) {
          return {};
        }

        var header_vals = header.split(','),
            links = {};

        $.each(header_vals, function(_, val){
            var match = /<([^>]+)>; rel="([^"]+)"/g.exec(val);

            links[match[2]] = match[1];
        });

        return links;
      }

      function Paginator(endpoint, options) {
        var i;

        if (options === undefined) {
          options = {};
        }

        for (i in defaults) {
          if (options[i] === undefined) {
            options[i] = defaults[i];
          }
        }

        this.options = options;
        this.collection = options.collection || new Collection();
        this.pageLinks = [];
        this.nextPage = null;
        this.previousPage = null;

        if (endpoint) {
          this.deferred = this.loadResults(endpoint);
        }

        return this;
      }

      Paginator.prototype.updatePageLinks = function updateLinks(links) {
        var value = parseLinkHeader(links),
            poller = this.options.poller;

        this.pageLinks = value;
        this.nextPage = value.next || null;
        this.previousPage = value.previous || null;

        if (poller) {
          if (value.previous) {
            poller.stop();
          } else {
            poller.start();
          }
        }
      };

      Paginator.prototype.loadResults = function loadResults(url) {
        var self = this;

        self.options.onLoadBegin(url);

        return $http.get(url)
          .success(function(data, status, headers){
            self.collection.empty();
            self.collection.extend(self.options.transform(data));
            self.updatePageLinks(headers('Link'));
            self.options.onLoadSuccess(url, data);
            self.options.onLoadComplete(url);
          })
          .error(function(data){
            self.options.onLoadError(url, data);
            self.options.onLoadComplete(url);
          });
      };

      Paginator.prototype.loadPreviousPage = function loadPreviousPage() {
        jQuery(document.body).scrollTop(0);
        this.loadResults(this.pageLinks.previous);
      };

      Paginator.prototype.loadNextPage = function loadNextPage() {
        jQuery(document.body).scrollTop(0);
        this.loadResults(this.pageLinks.next);
      };

      return Paginator;
    });
});
