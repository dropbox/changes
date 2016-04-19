import React from 'react';

/*
 * Very simple text component designed to be the title above grid elements
 */
var SectionHeader = React.createClass({

  propTypes: {
    // ...
    // transfers all properties to rendered <div />
  },

  render: function() {
    var { className, ...others } = this.props;
    className = (className || "") + " sectionHeader nonFixedClass";
    return <div {...others} className={className}>
      {this.props.children}
    </div>;
  }
});

export default SectionHeader;
