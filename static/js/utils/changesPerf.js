/* 
 * This is a global object stored on window.
 * No RequireJS since we directly include this on the template page.
 */

var changesPerf = {

  // Keeps track of perf data. Once the page is loaded, we flush the data 
  // to server and reset to null
  currentPage: null,

  fullPageLoadStart: function() {
    'use strict';
    // differentiate between the initial page load
    // and angular state transitions
    this._start(true);
  },

  transitionPageLoadStart: function() {
    'use strict';
    this._start(false);
  },

  _start: function(is_initial) {
    'use strict';
    this.currentPage = {
      initial: is_initial,
      startTime: (new Date()).getTime(),
      apiCalls: {}
    };
  },

  pageLoadEnd: function() {
    'use strict';
    if (this.currentPage) {
      this.currentPage.endTime = (new Date()).getTime();

      // send data to server, using built-in browser xhr
      var ajax = new XMLHttpRequest();
      ajax.open('POST', '/api/0/perf/', true);
      this.currentPage.url = window.location.href;
      ajax.send(JSON.stringify(this.currentPage));

      this.currentPage = null;
    }
  },

  ajaxStart: function(config) {
    'use strict';
    if (!this.currentPage) {
      return config;
    }

    if (config.url.indexOf("api/") != -1) {
      if (this.currentPage.apiCalls[config.url]) {
        // if we ever make multiple api calls with the same url,
        // mark a bit. We should fix whatever error causes this
        // and/or throw out those rows when analyzing data
        this.currentPage.sameApiCalledTwice = true;
      }
      this.currentPage.apiCalls[config.url] = {};
      this.currentPage.apiCalls[config.url].startTime = (
        new Date()).getTime();
    }
    return config;
  },

  ajaxEnd: function(response) {
    'use strict';
    if (!this.currentPage) {
      return response;
    }
    
    if (response.config.url.indexOf("api/") != -1) {
      if (!this.currentPage.apiCalls[response.config.url]) {
        // Silently failing. I think this is the correct behavior...what if 
        // we're in the middle of an ajax request on state transition?
        return response;
      }
      this.currentPage.apiCalls[response.config.url].endTime = (
        new Date()).getTime();
    }
    return response;
  }
};

window.changesPerf = changesPerf;
