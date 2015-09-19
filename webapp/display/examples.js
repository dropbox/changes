import React, { PropTypes } from 'react';

/*
 * When creating a display component, add some example usages using
 * Examples.add. Its an easy way to test your component in isolation and
 * to document various ways to use the component.
 *
 * /display_examples allows you to see all examples.
 */
var Examples = {
  _exampleFuncs: {},

  // this should be a function that returns a list of examples. Using a function
  // means that examples are only generated on the examples page itself
  add: function(name, func) {
    this._exampleFuncs[name] = func;
  },

  // runs all the example-generating functions and returns the results
  // You probably just want render, though...
  generateAndReturn: function() {
    var result = {};
    _.each(this._exampleFuncs, (func, name) => {
      result[name] = func.call(this);
    });
    return result;
  },

  // renders a list of all examples
  render: function() {
    var examples = this.generateAndReturn();

    var names = _.keys(examples).sort();

    var markup = [];
    _.each(names, name => {
      var items = examples[name];

      markup.push(
        <div>
          <div className="exampleHeader">{name}</div>
          <ul className="exampleList">
            {_.map(items, l => <li>{l}</li>)}
          </ul>
        </div>
      );
    });
    return markup;
  }
};

export default Examples;
