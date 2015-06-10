/**
 * Fetches data. elem is the caller react object, and for fetch_map:
 *
 * Simple usage: fetch_map is a map from labels to endpoints. After getting 
 * the data, we populate several state variables on elem.
 *
 * Using diffs as an example label:
 *   diffsStatus: will be set to 'loaded' or 'error'.
 *   diffsData: if 'loaded', the json parsed response from the api endpoint
 *   diffsError: if 'error', a dict with keys {status, responseText, response}
 * 
 * Advanced usage: instead of an endpoint, you can provide another map from 
 *   labels to endpoints. This is NOT recursive (you can only go one level 
 *   deep...KISS.) The top-level status variable will be set to error if any 
 *   sub-fetch has an error (even if not all endpoints have responded), and
 *   will be set to loaded if every sub-fetch succeeds. There is no top-level
 *   *Error variable, and the *Data variable has the same schema as above.
 * 
 *   We have this because we want the top-level page to fetch data for 
 *   individual sections of the page, and pass it down to them using props.
 * 
 * Example usage: fetct_data(this, {
 *   diffs: '/api/0/author/me/diffs', 
 *   info: {
 *     project: '/api/0/project/changes',
 *     project_plan: '/api/0/project/changes'
 *   }
 *  });
 */
export var fetch_data = function(elem, fetch_map) {
  _.each(fetch_map, (v, label) => {
    if (_.isString(v)) {
      // the simple case
      var simple_response = function(response, was_success) {
        if (!elem.isMounted()) {
          return false;
        }
        var state_to_set = {};
        if (was_success) {
          state_to_set[label+"Status"] = "loaded";
          state_to_set[label+"Data"] = JSON.parse(response.responseText);
        } else {
          state_to_set[label+"Status"] = "error";
          state_to_set[label+"Error"] = {
            status: response.status,
            responseText: response.responseText,
            response: response
          };
        }
        elem.setState(state_to_set)
      }
      make_api_ajax_call(v, simple_response, simple_response);
    } else {
      // the complex case: we have a dictionary of endpoints
      var schema = v;
      _.each(v, (child_endpoint, child_label) => {
        var child_response = function(response, was_success) {
          if (!elem.isMounted()) {
            return false;
          }

          // unlike the simple case where we pass in only the changed fields,
          // we have to grab the existing label+Data dict and send
          // back an updated version.
          var fetched_data = elem.state[label+"Data"] || {};
          if (was_success) {
            fetched_data[child_label+"Status"] = "loaded";
            fetched_data[child_label+"Data"] = JSON.parse(response.responseText);
          } else {
            fetched_data[child_label+"Status"] = "error";
            state_to_set[child_label+"Error"] = {
              status: response.status,
              responseText: response.responseText,
              response: response
            };
          }

          // figure out whether everything has finished loading / any errors
          var fields_to_check = _.chain(schema).keys()
            .map(s => s+"Status")
            .value();

          var every_status = _.values(_.pick(fetched_data, fields_to_check));
          var any_error = _.contains(every_status, 'error');
          var all_loaded = _.every(every_status, 
            t => { return t === 'loaded'; });

          var state_to_set = {};
          state_to_set[label+"Data"] = fetched_data;
          if (any_error) {
            state_to_set[label+"Status"] = "error";
          } else if (all_loaded) {
            state_to_set[label+"Status"] = "loaded";
          }
          elem.setState(state_to_set);
        } // end function child_response(...
        make_api_ajax_call(child_endpoint, child_response, child_response);
      }); // end _.each(v, (child_endpoint, child_label) => {
    } // end if (_.isString(v)) {
  }); // end _.each(fetch_map, (v, label) => {
}

/**
 * Makes an ajax request to the changes API and returns data. This function
 * may rewrite urls to a prod host if window.DEV_JS_SHOULD_HIT_HOST is set.
 *
 * The response_callback/error_callback functions should have the sig:
 *   function(response, was_success) { ... } 
 * (was_success makes it easy to use the same func for both)
 */
export var make_api_ajax_call = function(
    endpoint, response_callback, error_callback) {

  response_callback = response_callback || function() { };
  error_callback = response_callback || function() { };

  var url = endpoint;

  // useful during development, to redirect API calls to a prod frontend
  if (window.DEV_JS_SHOULD_HIT_HOST) {
    // hack: for auth, send an extra call to the local instance (but not /authors)
    if (endpoint.indexOf('/auth') !== -1 &&
        (endpoint.indexOf('/auth') !== endpoint.indexOf('/authors'))) {
      var req = new XMLHttpRequest();
      req.open('get', url, true);
      req.send();
    }

    // temporary hack: authors/me/diff not checked in yet, so exclude it
    if (endpoint.indexOf("/diffs") === -1) {
      url = window.DEV_JS_SHOULD_HIT_HOST + url;
    }
  }

  var req = new XMLHttpRequest();
  req.open('get', url, true);
  // TODO: maybe just use a library for ajax calls
  req.onload = function() {
    // 2xx responses and 304 responses count as success
    var failed = this.status < 200 || 
      (this.status >= 300 && this.status !== 304);

    if (!failed) {
      // TODO: any way to do this without binding this?
      response_callback.call(this, this, true);
    } else {
      error_callback.call(this, this, false);
    }
  };
  req.send();
}
