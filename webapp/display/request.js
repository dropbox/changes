import React, { PropTypes } from 'react';

import { AjaxError } from 'es6!display/errors';

import * as api from 'es6!server/api';

/*
 * Eas(ier) way to make post requests.
 */
var Request = React.createClass({

  propTypes: {
    parentElem: PropTypes.object.isRequired,
    name: PropTypes.string.isRequired,
    endpoint: PropTypes.string.isRequired,
    params: PropTypes.object,
    method: function(props, propName) {
      if (!_.contains(['delete', 'post', 'get'], props[propName])) {
        return new Error('Unknown request method');
      }
    },
  },

  render: function() {
    var parentElem = this.props.parentElem,
      name = this.props.name,
      endpoint = this.props.endpoint,
      child = React.Children.only(this.props.children);

    var stateKey = `_${this.props.method}Request_${name}`;
    var currentState = parentElem.state[stateKey];

    if (currentState && currentState.condition === 'loading') {
      return <div>
        <i className="fa fa-spinner fa-spin" />
      </div>;
    } else if (api.isError(currentState)) {
      return <AjaxError response={currentState.response} />;
    } else if (api.isLoaded(currentState) && this.props.method !== 'get') {
      // reload to pick up the updates from the request
      window.location.reload();
    }

    var method = api.post;
    if (this.props.method === 'delete') {
      method = api.delete_;
    } else if (this.props.method === 'get') {
      method = api.get;
    }

    var onClick = evt => {
      method(parentElem, {
        [ stateKey ]: endpoint,
      }, {
        [ stateKey ]: this.props.params,
      });
    };

    return React.cloneElement(child, {'onClick': onClick});
  },
});

export default Request;
