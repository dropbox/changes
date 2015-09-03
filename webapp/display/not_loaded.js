import React, { PropTypes } from 'react';

import { AjaxError, ProgrammingError } from 'es6!display/errors';
import { RandomLoadingMessage, InlineLoading } from 'es6!display/loading';

import * as api from 'es6!server/api';

var cx = React.addons.classSet;

/*
 * Convenience wrapper that takes the contents of the state variable used for
 * an api fetch and renders either an error message (using <AjaxError />)
 * or <RandomLoadingMessage />.
 *
 * Example:
 * if (!api.isLoaded(this.state.myData)) {
 *   return <APINotLoaded state={this.state.myData} />;
 * }
 * ... (render the data from the api)
 *
 */
var APINotLoaded = React.createClass({

  propTypes: {
    state: PropTypes.object,

    // you can use this for multiple API calls (making sure they've all loaded
    // before proceeding.)
    // TODO: just make this take a list...
    stateMap: PropTypes.objectOf.object,
    stateMapKeys: PropTypes.array,

    // if true, show InlineLoading instead of RandomLoading
    // TODO: should always be true?
    isInline: PropTypes.bool,
  },

  getDefaultProps: function() {
    return {
      isInline: true
    }
  },

  // note: we'll treat missing APIResponse objects (before api.fetch is called)
  // as "loading"
  render: function() {
    var { state, stateMap, stateMapKeys, isInline, ...props} = this.props;

    if (state && stateMapKeys) {
      return <ProgrammingError>
        APINotLoaded: passed both state and stateMapKeys/stateMap
      </ProgrammingError>;
    }

    var responseForError = null; // ignored unless condition is error

    if (stateMapKeys) {
      var condition = 'loading';
      if (api.mapAnyErrors(stateMap, stateMapKeys)) {
        condition = 'error';
        responseForError = _.first(api.mapGetErrorResponses(
          stateMap, stateMapKeys));
      } else if (api.mapIsLoaded(stateMap, stateMapKeys)) {
        var condition = 'loaded';
      }
    } else {
      var condition = (state && state.condition) || 'loading';
      responseForError = state && state.response;
    }

    if (condition === 'loading') {
      if (isInline) {
        return <InlineLoading {...props} />;
      }
      return <RandomLoadingMessage {...props} />;
    } else if (condition === 'error') {
      return <AjaxError {...props} response={responseForError} />;
    } else {
      return <ProgrammingError>
        APINotLoaded: Unknown condition {condition}
      </ProgrammingError>;
    }
  },
});

export default APINotLoaded;
