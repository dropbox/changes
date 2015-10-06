import React, { PropTypes } from 'react';

import { AjaxError } from 'es6!display/errors';

import * as api from 'es6!server/api';

/*
 * Eas(ier) way to make post requests. 
 */
var PostRequest = React.createClass({

  propTypes: {
    parentElem: PropTypes.object.isRequired,
    name: PropTypes.string.isRequired,
    endpoint: PropTypes.string.isRequired
  },

  render: function() {
    var parentElem = this.props.parentElem,
      name = this.props.name,
      endpoint = this.props.endpoint,
      child = React.Children.only(this.props.children);

    var stateKey = "_postRequest_" + name;
    var currentState = parentElem.state[stateKey];
      
    if (currentState && currentState.condition === 'loading') {
      return <div>
        <i className="fa fa-spinner fa-spin" />
      </div>;
    } else if (api.isError(currentState)) {
      return <AjaxError response={currentState.response} />;
    } else if (api.isLoaded(currentState)) {
      // reload to pick up the updates from the post request
      window.location.reload();
    }

    var onClick = evt => {
      api.post(parentElem, {
        [ stateKey ]: endpoint
      });
    };

    child.props.onClick = onClick;
    return child;
  },
});

export default PostRequest;
