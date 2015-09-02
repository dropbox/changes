import React from 'react';

import { Error, ProgrammingError } from 'es6!display/errors';

var cx = React.addons.classSet;

/*
 * Basically a list with properties/keys on the left and values on the right.
 * The values might be arbitrarily complex markup.
 */

export var InfoList = React.createClass({

  propTypes: {
    // ...
    // transfers other properties to rendered <div />
  },

  render: function() {
    var { className, ...others } = this.props;

    var error = null;
    React.Children.forEach(this.props.children, c => {
      if (c.type.displayName !== 'InfoItem') {
        console.log(c);
        error = <ProgrammingError>
          InfoList got a child that wasn{"'"}t an InfoItem (see console log)
        </ProgrammingError>;
      }
    });
    if (error) {
      return error;
    }

    var rows = [];
    React.Children.forEach(this.props.children, c => {
      rows.push(
        <tr> <td className="infoLabel">
          {c.props.label}
        </td> <td>
          {c.props.children}
        </td> </tr>
      );
    });

    className = (className || "") + " invisibleTable infoList";
    return <table className={className} {...others}>{rows}</table>;
  },
});

export var InfoItem = React.createClass({

  propTypes: {
    // the label to use for the item
    label: React.PropTypes.string

    // TODO: we could add tooltip support

    // the child of this item is the rhs content
  },

  render: function() {
    throw Error("cannot call me!");
  }
});
