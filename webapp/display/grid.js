import React from 'react';

import { Error, ProgrammingError } from 'es6!display/errors';

import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;
var proptype = React.PropTypes;

export var Grid = React.createClass({

  propTypes: {
    // how many columns should this grid have?
    colnum: proptype.number.isRequired,
    // matrix (array of arrays) of data. You can use GridRow in place of an array
    data: proptype.array.isRequired,
    // a row (same length as other rows) used for blue header cells
    headers: proptype.array,
    // same length as row, we add each css class to the row cells
    cellClasses: proptype.arrayOf(proptype.string)

    // ...
    // transfers other properties to rendered <table /> or <div /> (right now table)
  },

  getDefaultProps: function() {
    return {
      data: [],
      headers : [],
      cellClasses: []
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
    if (row instanceof GridRow) {
      if (row.isUsingColspan) {
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

        return <td className={className}>
          {cell}
        </td>;
      });
    }

    var row_classes = cx({
      gridRow: true,
      gridHeader: row_index === -1,
      // we may sometimes/somday want different bg colors for even/odd rows
      gridEven: (row_index+1) % 2 === 0,
      gridFirstRow: row_index === 0,
      gridRowOneItem: is_using_colspan,
    });

    return <tr className={row_classes}>
      {cells}
    </tr>;
  },

  // verify that we were passed in good data
  verifyData: function() {
    var data = this.props.data, headers = this.props.headers, 
      cellClasses = this.props.cellClasses, colnum = this.props.colnum;

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
 * - TODO: more bullet points
 * 
 * GridRow can be used in place of the row array above
 */
export class GridRow {
  constructor(data) {
    if (!_.isArray(data)) {
      throw 'GridRow expects an array of data!';
    }
    this.data = data;
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

  // see oneItem constructor
  isUsingColspan() { return this.useColspan; }
}

