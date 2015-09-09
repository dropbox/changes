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
 *   return <APINotLoaded calls={this.state.myData} />;
 * }
 * ... (render the data from the api)
 *
 */
var APINotLoaded = React.createClass({

  propTypes: {
    // you can pass multiple API calls as a list (making sure they've all loaded
    // before proceeding.)
    calls: PropTypes.oneOfType([PropTypes.object, PropTypes.list]),

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
    var { calls, isInline, ...props} = this.props;
    var manyCalls = _.isArray(calls);

    var responseForError = null; // ignored unless condition is error
    if (manyCalls) {
      var condition = 'loading';
      if (api.anyErrors(calls)) {
        condition = 'error';
        // TODO: show multiple calls
        responseForError = _.first(api.allErrorResponses(calls));
      } else if (api.allLoaded(calls)) {
        var condition = 'loaded';
      }
    } else {
      var condition = (calls && calls.condition) || 'loading';
      responseForError = calls && calls.response;
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
