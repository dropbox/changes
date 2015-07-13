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
  getReturnedData() { 
    return JSON.parse(this.response.responseText); 
  }
}

/*
 * Sends a bunch of API requests, and calls setState on `elem` with the
 * resulting APIResponse objects. endpoint_map is a map from the state key
 * to the endpoint to send the get request to.
 */
export var fetch = function(elem, endpoint_map) {
  return fetchMap(elem, null, endpoint_map);
}

/*
 * Like fetch, but all of the results are in a map inside state with key `map_key`
 * You cannot directly call this from render! use asyncFetchMap instead
 */
export var fetchMap = function(elem, map_key, endpoint_map) {
  // add a bunch of "loading" APIResponse objects to the element state
  var state_to_set = _.mapObject(endpoint_map, (endpoint, map_key) => {
    return APIResponse(endpoint);
  });
  if (map_key) { 
    state_to_set = {};
    state_to_set[map_key] = _.mapObject(endpoint_map, e => APIResponse(e));
  }
  elem.setState(state_to_set);

  _.each(endpoint_map, (endpoint, state_key) => {
    var ajax_response = function(response, was_success) {
      if (!elem.isMounted()) {
        return false;
      }

      var api_response = APIResponse(endpoint);
      api_response.condition = was_success ? 'loaded' : 'error';
      api_response.response = response;

      if (!map_key) {
        var state_to_set = {};
        state_to_set[state_key] = api_response;
        elem.setState(state_to_set);
      } else {
        elem.setState((previous_state, current_props) => {
          // we have to set the entire map, not just the single key that changed
          var fetch_map = _.clone(elem.state[map_key]);
          fetch_map[state_key] = api_response;

          var state_to_set = {};
          state_to_set[map_key] = fetch_map;
          return state_to_set;
        });
      }
    }
    make_api_ajax_call(endpoint, ajax_response, ajax_response);
  });
}

/*
 * Wraps fetchMap in window.setTimeout. This allows you to call it from 
 * render() (yes, there's a legitimate reason we do this...)
 */
export var asyncFetchMap = function(elem, map_key, endpoint_map) {
  window.setTimeout(_ => {
    fetchMap(elem, map_key, endpoint_map);
  }, 0);
}

export var isLoaded = function(possible) {
  return _.isObject(possible) && possible.condition === 'loaded'
}

export var mapIsLoaded = function(map, keys) {
  if (!keys) {
    throw "You must provide a list of keys to check!";
  }
  return _.every(_.map(keys, k => isLoaded(map[k])));
}

export var mapAnyErrors = function(map, keys) {
  if (!keys) {
    throw "You must provide a list of keys!";
  }
  return _.any(_.map(keys, k => map[k] && map[k].condition === 'error'));
}

export var mapGetErrorResponses = function(map, keys) {
  if (!keys) {
    throw "You must provide a list of keys!";
  }
  var responses = [];
  _.each(keys, k => {
    if (map[k] && map[k].condition === 'error') {
      responses.push(map[k].response);
    }
  });
  return responses;
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
    endpoint, response_callback, error_callback) {

  response_callback = response_callback || function() { };
  error_callback = response_callback || function() { };

  var url = endpoint;

  // useful during development, to redirect API calls to a prod frontend
  if (window.changesGlobals['USE_ANOTHER_HOST']) {
    url = window.changesGlobals['USE_ANOTHER_HOST'] + url;
  }

  var req = new XMLHttpRequest();
  req.open('get', url, true);
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
  req.send();
}
