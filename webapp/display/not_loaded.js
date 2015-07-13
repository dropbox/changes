import React from 'react';

import { AjaxError, ProgrammingError } from 'es6!display/errors';
import { InlineLoading, RandomLoadingMessage } from 'es6!display/loading';
import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;
var proptype = React.PropTypes;

/*
 * Convenience wrapper that takes the contents of the state variable used for 
 * an api fetch and renders either <AjaxError /> or <RandomLoadingMessage />.
 */
var APINotLoaded = React.createClass({

  propTypes: {
    state: proptype.object,
    stateMap: proptype.objectOf.object,
    stateMapKeys: proptype.array,
    // if true, show InlineLoading instead of RandomLoading
    isInline: proptype.bool,
  },

  getDefaultProps: function() {
    return {
      isInline: false 
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
