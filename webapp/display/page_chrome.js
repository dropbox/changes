import React from 'react';
import _ from 'underscore';

var cx = React.addons.classSet;
var proptype = React.PropTypes;

// Exports ChangesPage. Helper class: ChangesPageHeader

var ChangesPage = React.createClass({

  propTypes: {
    // should we automatically add padding to the page content?
    bodyPadding: proptype.bool,
  },

  getDefaultProps: function() {
    return { bodyPadding: true };
  },

  render: function() {
    var style = this.props.bodyPadding ? {padding: '10px'} : {};

    return <div>
      <ChangesPageHeader />
      <div style={style}>
        {this.props.children}
      </div>
    </div>;
  }
});

/*
 * The header that shows up at the the top of every page. Decided against 
 * using fixed positioning: its not important enough (if it were the primary
 * means of navigation on the page, I'd have used it.)
 */
var ChangesPageHeader = React.createClass({
  
  // no properties

  render: function() {
    // Log In not implemented yet, graying it out
    return <div>
      <div className="pageHeader">
        <div className="headerBlock"><b>Changes</b></div>
        <a className="headerLinkBlock" href="/v2/">
          My Changes
        </a>
        <a className="headerLinkBlock" href="/v2/projects/">
          All Projects
        </a>
        <div className="headerBlock" style={{float: 'right', color: '#959ca1'}}>
          Log in
        </div>
      </div>
    </div>;
  }
});

export default ChangesPage;
