import React, { PropTypes } from 'react';

import { Error, ProgrammingError } from 'es6!display/errors';
import SimpleTooltip from 'es6!display/simple_tooltip';

/*
 * Basically a list with properties/keys on the left and values on the right.
 * The values might be arbitrarily complex markup.
 */
export var InfoList = React.createClass({

  propTypes: {
    className: PropTypes.string,
    children: PropTypes.node,
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
      var label;
      if (c.props.tooltip) {
          label = (<SimpleTooltip label={c.props.tooltip} placement="right">
              <div>{c.props.label}</div>
          </SimpleTooltip>);
      } else {
        label = c.props.label;
      }
      rows.push(
          <tr>
              <td className="infoLabel">{label}</td>
              <td className={c.props.valueClassName}>{c.props.children}</td>
          </tr>
      );
    });

    className = (className || "") + " invisibleTable infoList";
    return <table className={className} {...others}>{rows}</table>;
  },
});

export var InfoItem = React.createClass({

  propTypes: {
    // the label to use for the item
    label: PropTypes.string,

    // optional tooltip
    tooltip: PropTypes.node,

    // a className string to be applied to the <td> containing the InfoItem
    // value (vs. the InfoItem label in the other <td>)
    valueClassName: PropTypes.string,

    // the child of this item is the rhs content
  },

  render: function() {
    throw Error("cannot call me!");
  }
});
