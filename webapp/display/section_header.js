import React from 'react';

var cx = React.addons.classSet;
var proptype = React.PropTypes;

/*
 * Very simple text component designed to be the title above grid elements
 */
var SectionHeader = React.createClass({

  propTypes: {
    // ...
    // transfers all properties to rendered <span />
  },

  render: function() {
    var { className, ...others } = this.props;
    className = (className || "") + " sectionHeader";
    return <span {...others} className={className}>
      {this.props.children}
    </span>;
  }
});

export default SectionHeader;
