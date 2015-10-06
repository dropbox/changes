import React, { PropTypes } from 'react';

import Examples from 'es6!display/examples';
import { ProgrammingError } from 'es6!display/errors';

var cx = React.addons.classSet;

export var Grid = React.createClass({

  propTypes: {
    // how many columns should this grid have?
    colnum: PropTypes.number.isRequired,
    // matrix (array of arrays) of data. You can use GridRow in place of an array
    data: PropTypes.array.isRequired,
    // a row (same length as other rows) used for blue header cells
    headers: PropTypes.array,
    // same length as row, we add each css class to the row cells
    // we have some magic classes (descriptions in css file): cellOverflow
    cellClasses: PropTypes.arrayOf(PropTypes.string),
    // whether to render dividers between rows
    border: PropTypes.bool,

    // ...
    // transfers other properties to rendered <table />
  },

  getDefaultProps: function() {
    return {
      data: [],
      headers : [],
      cellClasses: [],
      border: true
    }
  },

  render: function() {
    var { data, headers, cellClasses, className, ...props} = this.props;

    // we only have something to render if we have >= 1 row or headers
    if (data.length === 0 && _.isEmpty(headers)) {
      return <div />;
    }

    var error_markup = this.verifyData();
    if (error_markup) {
      return error_markup;
    }

    var header_row = null;
    if (headers && headers.length) {
      header_row = this.renderRow(headers, -1);
    }

    var rows = _.map(data, this.renderRow);

    className = "grid " + (className || "");
    if (!this.props.border) {
      className += " noborder";
    }

    return <table {...props} className={className}>
      {header_row}
      <tbody>
        {rows}
      </tbody>
    </table>;
  },

  // row_index = -1 means header, otherwise its just which row
  renderRow: function(row, row_index) {
    var classes = this.props.cellClasses;

    var cells = null;
    var is_using_colspan = false;
    var hasBorder = true;
    var fadedOut = false;
    if (row instanceof GridRow) {
      hasBorder = row.hasBorder();
      fadedOut = row.isFadedOut();
      if (row.isUsingColspan()) {
        is_using_colspan = true;
        cells = <td className="gridCell" colSpan={this.props.colnum}>
          {row.getData()[0]}
        </td>;
      } else {
        row = row.getData();
      }
    }

    if (!cells) {
      var cells = _.map(row, (cell, index) => {
        if (row_index === -1) { // header cells
          className = 'nowrap gridCell';
        } else {
          var className = (classes && classes[index]) || "";
          className += ' gridCell';
        }

        // cellOverflow magic class: we wrap the contents in a span and expand
        // it on click
        if (className.indexOf('cellOverflow') >= 0) {
          var onClick = evt => {
            var newClass = evt.target.className
              .replace("cellOverflowPointer", "") +
              " cellOverflowExpanded";

            evt.target.className = newClass;
          };

          var cell = <td className={className} onClick={onClick}>
            {cell}
          </td>;

          return cell;
        }

        return <td className={className}>
          {cell}
        </td>;
      });
    }

    var row_classes = cx({
      gridRow: true,
      gridHeader: row_index === -1,
      // we may sometimes/somday want different bg colors for even/odd rows
      gridEven: row_index !== 0 && (row_index+1) % 2 === 0,
      gridFirstRow: row_index === 0,
      gridRowOneItem: is_using_colspan,
      gridFadedOut: fadedOut,
      noborder: !hasBorder,
    });

    return <tr className={row_classes}>
      {cells}
    </tr>;
  },

  componentDidMount: function() {
    // hack: we add the cellOverflowPointer class to any cell with overflowing
    // content. Note that this won't update if we scroll (but its a minor ui
    // issue and let's us avoid adding a scroll handler.)

    // React might not properly dispose of this class if something weird
    // happens, but that should be ok. The css rule only triggers when both
    // a react-supplied class and our custom class are present.

    var overflowNodes = React.findDOMNode(this).getElementsByClassName('cellOverflow');
    _.each(overflowNodes, cell => {
      if (cell.scrollWidth > cell.clientWidth) {
        cell.className += " cellOverflowPointer";
      }
    });
  },

  // verify that we were passed in good data
  verifyData: function() {
    var data = this.props.data, headers = this.props.headers,
      cellClasses = this.props.cellClasses, colnum = this.props.colnum;

    if (!colnum) {
      return <ProgrammingError>
        {"`"}colnum{"`"} is 0 or unspecified!
      </ProgrammingError>;
    }

    // make sure headers/cellClasses have the right length

    if (!_.isEmpty(headers) && headers.length !== colnum) {
      return <ProgrammingError>
        {"`"}headers{"`"} has wrong length. Expected {colnum}, got {headers.length}.
      </ProgrammingError>;
    }

    if (!_.isEmpty(cellClasses) && cellClasses.length !== colnum) {
      return <ProgrammingError>
        {"`"}cellClasses{"`"} has wrong length. Expected {colnum}, got {cellClasses.length}.
      </ProgrammingError>;
    }

    // verify everything in data is a row and same number of columns in all rows

    var bad_rows_counter = 0; // keep track of how many broken rows we see
    var sample_bad_row = null; // if we encounter something that isn't a row
    var sample_bad_row_length = null; // if we encounter a row w/ wrong # of cols

    _.each(data, row => {
      if (row instanceof GridRow) {
        if (row.isUsingColspan) { return; }
        row = row.getData();
      }

      if (row && _.isArray(row)) {
        if (row.length !== colnum) {
          bad_rows_counter++;
          sample_bad_row_length = row.length;
        }
      } else {
        bad_rows_counter++;
        sample_bad_row = row;
      }
    });

    if (sample_bad_row) {
      console.log(sample_bad_row);
      return <ProgrammingError>
        Ran into something that wasn{"'"}t a valid row (also in console):
        {sample_bad_row}.
        {bad_rows_counter} of {data.length} row(s) seem broken.
      </ProgrammingError>;
    } else if (sample_bad_row_length) {
      return <ProgrammingError>
        Expected all rows to have length {colnum}, ran into a bad
        row with length {sample_bad_row_length}.
        {bad_rows_counter} of {data.length} row(s) seem broken.
      </ProgrammingError>;
    }

    return null;
  },
});

/*
 * Sometimes we want more interesting rows in our table:
 * - A row that spans all columns
 * - TODO: more capabilities
 *
 * GridRow can be used in place of the row array above
 */
export class GridRow {
  constructor(data, border=true, fadedOut=false) {
    if (!_.isArray(data)) {
      throw 'GridRow expects an array of data!';
    }
    this.data = data;
    this.border = border;
    this.fadedOut = fadedOut;
  }

  // use this if you want your row to just be a single item that spans all
  // columns. By default, there's no border between this row and the one above
  // it
  static oneItem(item) {
    var g = new GridRow([item]);
    g.useColspan = true;
    return g;
  }

  getData() { return this.data; }
  getLength() { return this.data.length; }
  hasBorder() { return this.border; }
  isFadedOut() { return this.fadedOut; }

  // see oneItem constructor
  isUsingColspan() { return this.useColspan; }
}

Examples.add('Grid', __ => {
  var data = [['A', 1], ['Z', 26]];
  return [
    <Grid
      colnum={2}
      headers={['Letter', 'Position']}
      data={data}
    />
  ];
});
