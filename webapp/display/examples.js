import React, { PropTypes } from 'react';

/*
 * When creating a display component, add some example usages using
 * Examples.add. Its an easy way to test your component in isolation and
 * to document various ways to use the component.
 *
 * Examples are added automatically on import, so if your component doesn't
 * show up its probably because nothing imports it
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

Examples.add('CSS Classes', __ => {
  return [
    <span className="blink">Blinking Text</span>,
    <span>
      Normal,{" "}
      <span className="lb">Bold-ish</span>,{" "}
      <b>Bold</b>,{" "}
      <span className="bb">Very Bold</span>
    </span>,
    <pre className="defaultPre">
    {"#include <stdio.h>"}<br />
    <br />
    {"int main() {\n"}<br />
    {"  printf(\"Hello World!\\n\");\n"}<br />
    {"}"}
    </pre>,
    <span>Text. <span className="subText">Subtext</span></span>
  ];
});

export default Examples;
