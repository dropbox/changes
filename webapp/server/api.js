import { Error } from 'es6!display/errors';

import * as utils from 'es6!utils/utils';

/**
 * Data structure for the data received from the changes API.
 */
export var APIResponse = function(endpoint) {
  return _.create(APIResponsePrototype, {
    endpoint: endpoint,
    condition: 'loading',  // 'loading', 'loaded', or 'error'
    response: null         // this will be the browser's response
                           // object from the ajax call
  });
}

var APIResponsePrototype = {
  // for API calls that return json
  // TODO: this name is terrible. Change it
  getReturnedData: function() {
    return JSON.parse(this.response.responseText);
  },

  getStatusCode: function() {
    return this.response.status + "";
  },

  // api calls with paging return their links as a response header.
  getLinksFromHeader: function() {
    var header = this.response.getResponseHeader('Link');
    if (header === null) {
      return {};
    }

    var links = {};
    _.each(header.split(','), str => {
      var match = /<([^>]+)>; rel="([^"]+)"/g.exec(str);
      links[match[2]] = match[1];
    });

    return links;
  }
}

/*
 * Sends a bunch of API requests, and calls setState on `elem` with the
 * resulting APIResponse objects.
 * endpoint_map is a map from the state key to the endpoint to send the get request to.
 * param_map is a map from the state key to a params object to send.
 * callback is a function(APIResponse, bool) which is called with
 *     a) the raw result of the API call. Can be null.
 *     b) Whether or not all batched API calls have completed successfully
 *        (e.g. for fetchMapWithParams(). Note that this is false for earlier
 *        calls if not all calls have returned yet.
 */
export var fetch = function(elem, endpoint_map, param_map = {}, callback = null) {

  return fetchMapWithParams(elem, null, endpoint_map, 'GET', param_map, callback);
}

/*
 * Similar to fetch, but use this for post requests.
 */
export var post = function(elem, endpoint_map, param_map = {}, callback = null) {
  return fetchMapWithParams(elem, null, endpoint_map, 'POST', param_map, callback);
}

/*
 * Similar to fetch, but use this for delete requests.
 */
export var delete_ = function(elem, endpoint_map, param_map = {}, callback = null) {
  return fetchMapWithParams(elem, null, endpoint_map, 'DELETE', param_map, callback);
}

/*
 * Like fetch, but all of the results are in a map inside state with key `map_key`
 * You cannot directly call this from render! use asyncFetchMap instead
 */
export var fetchMap = function(elem, map_key, endpoint_map, method = 'GET', callback = null) {
  return fetchMapWithParams(elem, map_key, endpoint_map, method, {}, callback);
}

var fetchMapWithParams = function(elem, map_key, endpoint_map, method, param_map, callback) {
  method = method.toLowerCase();
  if (method !== 'get' && method !== 'post' && method !=='delete') {
    throw new Error('method must be get or post or delete!');
  }

  // add a bunch of "loading" APIResponse objects to the element state
  if (map_key) {
    // we preserve other elements in the map
    elem.setState((previous_state, props) => {
      var new_map = _.extend({},
        previous_state[map_key],
        _.mapObject(endpoint_map, endpoint => {
          return APIResponse(endpoint);
        }));
      var state_to_set = {};
      state_to_set[map_key] = new_map;
      return state_to_set;
    });
  } else {
    elem.setState(
      _.mapObject(endpoint_map, endpoint => {
        return APIResponse(endpoint);
      })
    );
  }

  let success_count = 0;
  _.each(endpoint_map, (endpoint, state_key) => {
    var params = param_map[state_key];
    var ajax_response = function(response, was_success) {
      if (!elem.isMounted()) {
        return false;
      }

      if (was_success) {
        ++success_count;
      }

      var api_response = APIResponse(endpoint);
      api_response.condition = was_success ? 'loaded' : 'error';
      api_response.response = response;

      var state_to_set = null;
      if (!map_key) {
        state_to_set = {};
        state_to_set[state_key] = api_response;
      } else {
        state_to_set = utils.update_key_in_state_dict(map_key, state_key, api_response);
      }

      // If a callback is specified, pass the response object to it to allow
      // additional conditional processing by the GET/POST/DELETE caller.
      let callbackWithResponse = null;
      if (callback) {
        let all_successes = success_count === Object.keys(endpoint_map).length;
        callbackWithResponse = function() { callback(api_response, all_successes); }
      }

      elem.setState(state_to_set, callbackWithResponse);
    }

    make_api_ajax_call(method, endpoint, params, ajax_response, ajax_response);
  });
}

/*
 * Wraps fetchMap in window.setTimeout. This allows you to call it from
 * render() (yes, there's a legitimate reason we do this...)
 *
 * TODO: deleted only use case, maybe deprecate?
 */
export var asyncFetchMap = function(elem, map_key, endpoint_map) {
  window.setTimeout(_ => {
    fetchMap(elem, map_key, endpoint_map);
  }, 0);
}

/*
 * Has an api call finished yet? Handles null (false)
 */
export var isLoaded = function(possible) {
  return _.isObject(possible) && possible.condition === 'loaded'
}

/*
 * Did an api call return an error?
 */
export var isError = function(possible) {
  return _.isObject(possible) && possible.condition === 'error'
}

/*
 * For keys in map, are all of the api calls finished?
 */
export var allLoaded = function(list_of_calls) {
  return _.every(list_of_calls, l => isLoaded(l));
}

/*
 * For keys in map, did any of the api calls return an error?
 */
export var anyErrors = function(list_of_calls) {
  return _.any(list_of_calls, l => l && l.condition === 'error');
}

/*
 * For keys in map, return all XMLHTTPRequest objects for api calls that
 * returned an error
 */
export var allErrorResponses = function(list_of_calls) {
  var responses = [];
  _.each(list_of_calls, l => {
    if (l && l.condition === 'error') {
      responses.push(l.response);
    }
  });
  return responses;
}

/*
 * Build success/error messages for an API call response. Handles null/false.
 * possible: the state object produced by the API call
 * success_str: a string to display if the call was successful
 * error_str_prefix: a prefix to prepend to an error message produced by the
 *                   API call.
 */
export var buildStatusMessage = function(
        possible, success_str, error_str_prefix) {
  if (isLoaded(possible)) {
    return success_str;
  } else if (isError(possible)) {
    let response_data = possible.getReturnedData();
    // Sometimes API responses are JSON-encoded objects, and sometimes they're
    // JSON-encoded JSON-encoded objects. getReturnedData() decodes one layer.
    // Keep going until we get an Object instead of a string.
    //
    // @kylec: Some other options for this janky implementation:
    // 1) The right fix is probably to remove the double JSON-encoding from
    //    the server, but that will have similar compatibility problems.
    // 2) Move the while loop into getReturnedData(). But that's called in a
    //    bunch of places, and guaranteeing compatibility will be tricky.
    // 3) The old solution was: Just display whatever string (JSON-encoded
    //    or otherwise) the server decides to send back in response to the
    //    API call. But this is ugly.
    while (typeof(response_data) === 'string' || response_data instanceof String) {
        response_data = JSON.parse(response_data);
    }
    return `${error_str_prefix}: ${response_data.error}`;
  }
}

/**
 * Wrapper to make ajax GET request
 */
export var make_api_ajax_get = function(
    endpoint, params, response_callback, error_callback) {
  return make_api_ajax_call('get', endpoint, params, response_callback, error_callback);
}

/**
 * Wrapper to make ajax POST request
 */
export var make_api_ajax_post = function(
    endpoint, params, response_callback, error_callback) {
  return make_api_ajax_call('post', endpoint, params, response_callback, error_callback);
}

/**
 * Makes an ajax request to the changes API and returns data. This function
 * may rewrite urls to a prod host if USE_ANOTHER_HOST was set from the server
 *
 * The response_callback/error_callback functions should have the sig:
 *   function(response, [was_success]) { ... }
 * (was_success is optional - makes it easy to use the same func for both)
 */
export var make_api_ajax_call = function(
    method, endpoint, params, response_callback, error_callback) {

  response_callback = response_callback || function() { };
  error_callback = response_callback || function() { };

  var url = endpoint;

  // useful during development, to redirect API calls to a prod frontend
  var url_is_absolute = url && url.indexOf('http') === 0;
  if (window.changesGlobals['USE_ANOTHER_HOST'] && !url_is_absolute) {
    url = window.changesGlobals['USE_ANOTHER_HOST'] + url;
  }

  var req = new XMLHttpRequest();
  req.open(method, url, true);
  if (params) {
    params = JSON.stringify(params);
    req.setRequestHeader('Content-type', 'application/json;charset=UTF-8');
    req.setRequestHeader('Content-length', params.length);
    req.setRequestHeader('Connection', 'close');
  } else {
    params = '';
  }
  // TODO: maybe just use a library for ajax calls
  req.onload = function() {
    // 2xx responses and 304 responses count as success
    var failed = this.status < 200 ||
      (this.status >= 300 && this.status !== 304);

    if (!failed) {
      // nit: any way to do this without binding this?
      response_callback.call(this, this, true);
    } else {
      error_callback.call(this, this, false);
    }
  };

  req.onerror = function() {
    error_callback.call(this, this, false);
  }

  req.send(params);
}
