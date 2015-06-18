import React from 'react';

var cx = React.addons.classSet;
var proptype = React.PropTypes;

// Two classes: RandomLoadingMessage, InlineLoading

// Some playful loading messages
var loading_messages = [
  'Waiting for them bits',
  'Rolling, rolling, rolling',
  'Slow and steady wins the race',
  'Confucius say...wait',
  'Important things are worth waiting for',
  "I'm a happy loading message! \\(^o^)/",
  "I'm givin' her all she's got, captain!"
//  'W3C Working Draft: XMLHttpRequest Level 1'
];

/*
 * Shows a random string from the above list of loading messages. Since its
 * random, it will change every time the state of the parent component changes!
 * Which I actually like, since its a natural way to show progress.
 */
export var RandomLoadingMessage = React.createClass({
  proptypes: {
    display: proptype.oneOf(['inline', 'block', 'inlineBlock'])

    // ...
    // transfers other properties to rendered <div />
  },

  getDefaultProps: function() {
    return { display: "block" };
  },

  render: function() {
    var { className, ...props} = this.props;

    if (this.props.display === 'inline' || 
        this.props.display === 'inlineBlock') {
      className = (className || "") + " " + this.props.display;
    }

    return <div {...this.props} className={className}>
      {_.sample(loading_messages)}
    </div>;
  }
});

/*
 * When you have a part of the page that hasn't yet loaded, show a loading box.
 * Doesn't use the random loading messages above.
 */
export var InlineLoading = React.createClass({

  propTypes: {
    // ...
    // transfers all properties to rendered <div />
  },

  render: function() {
    var { className, ...props} = this.props;
    className = (className || "") + " inlineLoading";

    return <div {...this.props} className={className}>
      <i className="fa fa-spinner fa-spin marginRightS" />
      Still loading content
    </div>;
  },
});
