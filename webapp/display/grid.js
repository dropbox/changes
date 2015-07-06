import React from 'react';

import { Error } from 'es6!display/errors';

import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;
var proptype = React.PropTypes;

var Grid = React.createClass({

  propTypes: {
    // matrix (array of arrays) of data
    data: proptype.arrayOf(proptype.array).isRequired,
    // a row (same length as other rows) used for blue header cells
    headers: proptype.array,
    // same length as row, we add each css class to the row cells
    cellClasses: proptype.arrayOf(proptype.string)

    // ...
    // transfers other properties to rendered <div /> or <table /> (right now div)
  },

  getDefaultProps: function() {
    return {
      data: [],
      headers : [],
      cellClasses: []
    }
  },

  verifyData: function() {
    var data = this.props.data, headers = this.props.headers;

    // assumes there's some data. headers is optional
    var count = headers && headers.length;

    if (!count) {
      var firstRow = data && data[0];
      if (!firstRow) {
        return false;
      }
      count = firstRow.length;
    }

    var error_data = {
      num_rows_bad: 0,
      bad_row_length: 0,
      expected_length: count
    };

    data.forEach(row => {
      // TODO: _.isArray
      if (!row || (row.length !== count)) {
        error_data.num_rows_bad += 1;
        error_data.bad_row_length = (row && row.length) || 0;
      }
    });

    return [error_data.num_rows_bad === 0, error_data];
  },

  render: function() {
    var { data, headers, cellClasses, className, ...props} = this.props;
    className = "grid " + (className || "");

    if (data.length === 0) {
      // TODO: show headers, even without data?
      return <div />;
    }

    var [data_is_good, error_data] = this.verifyData();
    if (!data_is_good) {
      return <Error>
        {error_data.num_rows_bad} of {data.length} row(s) has/have the 
        wrong length. Expected {error_data.expected_length}, there was a bad
        row with length {error_data.bad_row_length}.
      </Error>;
    }

    var header_row = null;
    if (headers && headers.length) {
      header_row = this.renderRow(headers, 'header');
    }

    var rows = _.map(data, (row, index) =>
      this.renderRow(row, ((index+1) % 2 === 0) ? 'even' : 'odd')
    );

    // TODO: add spread attribute
    return <div {...props} className={className}>
      {header_row}
      {rows}
    </div>;
  },

  // row_type can be header, even, or odd
  renderRow: function(row, row_type) {
    if (!_.contains(["header", "even", "odd"], row_type)) {
      throw `Misused renderRow in grid: row_type is ${row_type}`;
    }

    var classes = this.props.cellClasses;

    var cells = _.map(row, (cell, index) => {
      var className = (classes && classes[index]) || "";
      className += ' gridCell';
      return <div className={className}>
        {cell}
      </div>;
    });

    var row_classes = cx({
      gridRow: true,
      gridHeader: row_type === 'header',
      gridEven: row_type === 'even'
    });

    return <div className={row_classes}>
      {cells}
    </div>;
  }
});

export default Grid;
