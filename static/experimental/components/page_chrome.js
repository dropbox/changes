import React from 'react';
import _ from 'underscore';

var cx = React.addons.classSet;
var proptype = React.PropTypes;

/*
 * The header that shows up at the the top of every page. Not sure whether to 
 * use fixed position; without it, we have more real estate for the content
 * TODO: revisit this. The main benefit of a fixed position header is that
 * its always easy to navigate. This means that the header has to be a primary
 * means of moving around the app.
 */
export var ChangesPageHeader = React.createClass({
  
  // no properties

  render: function() {
    return <div>
      <div className="pageHeader">
        <div className="headerBlock"><b>Changes</b></div>
        <a className="headerLinkBlock" href="/experimental/">
          My Changes
        </a>
        <div className="headerBlock" style={{float: 'right'}}>
          Log in
        </div>
      </div>
    </div>;
  }
});

export var ChangesPage = React.createClass({

  propTypes: {
    // should we automatically add padding to the page content?
    bodyPadding: proptype.bool,
  },

  getDefaultProps: function() {
    return { bodyPadding: true };
  },

  render: function() {
    var header_elem = null;
    var other_children = [];
    React.Children.forEach(this.props.children, c => {
      // c.type.displayName? there has to be a better way...
      if (c && c.type.displayName === "ChangesPageHeader") {
        header_elem = c;
      } else {
        other_children.push(c);
      }
    });

    var style = this.props.bodyPadding ? {padding: '10px'} : {};

    return <div>
      {header_elem}
      <div style={style}>
        {other_children}
      </div>
    </div>;
  }
});
