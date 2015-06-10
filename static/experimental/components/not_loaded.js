import React from 'react';

import { AjaxError } from 'es6!components/errors';
import { RandomLoadingMessage } from 'es6!components/loading';

import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;
var proptype = React.PropTypes;

/*
 * Convenience wrapper that takes the output of fetch_data and renders either
 * <AjaxError /> or <RandomLoadingMessage />
 */
var NotLoaded = React.createClass({

  propTypes: {
    // is the status still loading or error?
    loadStatus: proptype.oneOf(['loading', 'error']).isRequired,
    // if error, use this to populate error data
    errorData: proptype.object
  },

  render: function() {
    var { loadStatus, errorData, ...props} = this.props;

    if (loadStatus === 'loading') {
      return <RandomLoadingMessage {...props} />;
    } else if (loadStatus === 'error') {
      return <AjaxError {...props} response={errorData.response} />;
    }
  },
});

export default NotLoaded;
