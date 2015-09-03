import React, { PropTypes } from 'react';

var cx = React.addons.classSet;

/*
 * Menu 1. Simple, items separated with |.
 * Commits | Every Build | Tests | More Information
 */
export var Menu1 = React.createClass({

  propTypes: {
    // Names of the menu items
    items: PropTypes.arrayOf(PropTypes.string).isRequired,
    // which one is selected
    selectedItem: PropTypes.string,
    // callback when an item is clicked. params are selectedItem, clickEvent
    onClick: PropTypes.func
  },

  getDefaultProps: function() {
    return {
      items: [],
      selectedItem: '',
      onClick: item => console.log('no onclick handler for menu')
    }
  },

  render: function() {
    var { items, selectedItem, onClick, ...others} = this.props;

    var item_onclick = (item, clickEvent) => onClick(item, clickEvent);

    var item_markup = _.map(items, (text, index) => {
      var classes = cx({
        menuItem: true,
        firstMenuItem: index === 0,
        selectedMenuItem: selectedItem === text
      });

      return <div
        className={classes}
        onClick={_.partial(item_onclick, text)}>
        {text}
      </div>;
    });

    return <div {...others}>{item_markup}</div>;
  }
});

/*
 * Lightweight tabs menu
 */
export var Tabs = React.createClass({

  propTypes: {
    // Names of the menu items
    items: PropTypes.arrayOf(PropTypes.string).isRequired,
    // which one is selected
    selectedItem: PropTypes.string,
    // callback when an item is clicked. params are selectedItem, clickEvent
    onClick: PropTypes.func
  },

  getDefaultProps: function() {
    return {
      items: [],
      selectedItem: '',
      onClick: item => console.log('no onclick handler for menu')
    }
  },

  render: function() {
    var { items, selectedItem, onClick, className, ...others} = this.props;

    var item_onclick = (item, clickEvent) => this.props.onClick(item, clickEvent);

    var item_markup = _.map(items, (text, index) => {
      var classes = cx({
        tabsItem: true,
        leftmostTab: index === 0,
        rightmostTab: index === items.length - 1,
        selectedTabsItem: this.props.selectedItem === text
      });

      return <div
        className={classes}
        onClick={_.partial(onClick, text)}>
        <div className="tabsItemText">{text}</div>
      </div>;
    });

    className = (className || "") + " tabs";
    return <div>
      <div className={className} {...others}>{item_markup}</div>
      <div className="tabsBottomBorder" />
    </div>;
  }
});

export var MenuUtils = {
  // call this from componentWillMount: it looks at the window hash parameter and
  // tells you whether you should use a different selectedTab
  selectItemFromHash: function(window_hash, items) {
    // change the initial selected item if there's a hash in the url
    if (!window_hash) {
      return;
    }
    var hash_to_menu_item = {};
    _.each(items, i => {
      // let's accept a bunch of hash variants
      hash_to_menu_item[i] = i;
      hash_to_menu_item[i.toLowerCase()] = i;
      hash_to_menu_item[i.replace(/ /g, "")] = i;
      hash_to_menu_item[i.toLowerCase().replace(/ /g, "")] = i;
    });

    var hash = window_hash.substring(1);
    if (hash_to_menu_item[hash]) {
      return hash_to_menu_item[hash];
    }
    return null;
  },

  // default onclick handler for menu items
  // TODO: add a param to enable/disable the hash (some menus are small and
  // unimportant)
  onClick: function(elem, selected_item) {
    return item => {
      if (item === selected_item) {
        // one reason we'd want to be able to click on the same tab again is to
        // refresh the data. functions like componentDidMount won't be called
        // again, though, so this wouldn't work out of the box. Disabling for
        // now, might revisit later (e.g. using key attribute to force remount)
        return;
      }

      window.location.hash = item.replace(/ /g, "");
      elem.setState({selectedItem: item});
    };
  }
}
