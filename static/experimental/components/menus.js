import React from 'react';

var cx = React.addons.classSet;
var proptype = React.PropTypes;

/*
 * Menu 1. Simple, items separated with |.
 * Commits | Every Build | Tests | More Information
 * TODO: not used currently
 */
export var Menu1 = React.createClass({
  // TODO: proptypes, if I ever use this
  getDefaultProps: function() {
    return {
      'items': [],
      'selectedItem': ''
    }
  },

  render: function() {
    var item_markup = _.map(this.props.items, (text, index) => {
      var classes = cx({
        menuItem: true,
        firstMenuItem: index === 0,
        selectedMenuItem: this.props.selectedItem === text
      });
      return <div className={classes}>{text}</div>;
    });

    return <div>{item_markup}</div>;
  }
});

/*
 * Lightweight tabs menu. Most search engines have a similar menu style
 */
export var Menu2 = React.createClass({

  propTypes: {
    // Names of the menu items
    items: proptype.arrayOf(proptype.string).isRequired,
    // which one is selected
    selectedItem: proptype.string,
    // callback when an item is clicked. params are selectedItem, clickEvent
    onClick: proptype.func
  },

  getDefaultProps: function() {
    return {
      items: [],
      selectedItem: '',
      onClick: null
    }
  },

  render: function() {
    var onClick = (item, clickEvent) => this.props.onClick(item, clickEvent);

    var item_markup = _.map(this.props.items, (text, index) => {
      var classes = cx({
        menu2Item: true,
        firstMenu2Item: index === 0,
        selectedMenu2Item: this.props.selectedItem === text
      });
      
      return <div 
        className={classes}
        onClick={_.partial(onClick, text)}>
        {text}
      </div>;
    });

    return <div>{item_markup}</div>;
  }
});
