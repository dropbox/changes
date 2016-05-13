import React, { PropTypes } from 'react';
import { Button } from 'es6!display/button';

export const SUCCESS = 'success';
export const FAILURE = 'failure';
export const WARNING = 'warning';
export const INFO = 'info';

export var FlashMessage = React.createClass({
  propTypes: {
    message: PropTypes.node.isRequired,
    type: PropTypes.oneOf([SUCCESS, FAILURE, WARNING, INFO]).isRequired
  },

  getInitialState: function() {
    return {
      visible: true
    };
  },

  render: function() {
    if (this.state.visible) {
      var className = 'flash ' + this.props.type;

      let hide = () => this.setState({visible: false});

      return <div className="flashWrapper">
        <div className={className}>
          {this.props.message}
          <Button type="flash" onClick={hide}>X</Button>
        </div>
      </div>;
    }
    return null;
  }
});
