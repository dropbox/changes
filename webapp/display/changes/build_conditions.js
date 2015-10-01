import React, { PropTypes } from 'react';

import Examples from 'es6!display/examples';

/*
 * Basic code to deal with the fact that our builds (and similar objects like
 * jobs and tests (!) can be in many different conditions: still running,
 * failed, passed, etc. Some things we handle in this file:
 * - Given a build (/job/jobstep/test), what condition is it in?
 * - What color should I render text for a particular condition
 * - Rendering a colored dot that represents a condition
 *
 * Generally, we can assign conditions to objects with a status and result
 */

var all_build_conditions = [
  'passed', 
  'failed', 
  'failed_infra', 
  'failed_aborted', 
  'unknown', 
  
  'waiting'
];

/*
 * Looks at a build/job/jobstep's status and result fields to figure out what
 * condition the build is in. There are a bunch of failure conditions with a
 * common prefix, so you can just check failure with indexOf('failed') === 0.
 */
export var get_runnable_condition = function(runnable) {
  var status = runnable.status.id, result = runnable.result.id;

  if (status === 'in_progress' || status === "queued") {
    return 'waiting';
  }

  if (result === 'passed' || result === 'failed') {
    return result;
  } else if (result === 'aborted') {
    return 'failed_aborted';
  } else if (result === 'infra_failed') {
    return 'failed_infra';
  }
  return 'unknown';
}

/*
 * Combines the conditions of a bunch of runnables into a single summary
 * condition: if any failed or haven't finished, returns failed/waiting, etc.
 */
export var get_runnables_summary_condition = function(runnables) {
  var any_condition = condition => _.any(runnables,
    r => get_runnable_condition(r) === condition);

  // I picked what I thought was a reasonable order here
  var any_aborted = any_condition('failed_aborted');
  var any_failed_infra = any_condition('failed_infra');
  var any_failed = any_condition('failed');
  var any_waiting = any_condition('waiting');
  var any_unknown = any_condition('unknown');

  return (any_aborted && 'failed_aborted') ||
    (any_failed_infra && 'failed_infra') ||
    (any_failed && 'failed') ||
    (any_waiting && 'waiting') ||
    (any_unknown && 'unknown') ||
    'passed';
}

// short, readable text for runnable conditions
export var get_runnable_condition_short_text = function(condition) {
  var names = {
    passed: 'passed',
    failed: 'failed',
    'failed_aborted': 'aborted',
    'failed_infra': 'infrastructure failure',
    waiting: 'in progress',
  };
  return names[condition] || 'unknown';
}

export var get_runnable_condition_color_cls = function(condition, background = false) {
  switch (condition) {
    case 'passed':
      return background ? 'greenBg' : 'green';
    case 'failed':
    case 'failed_aborted':
      return background ? 'redBg' : 'red';
    case 'failed_infra':
      return background ? 'blackBg' : 'black';
    case 'waiting':
      return background ? 'bluishGrayBg' : 'bluishGray';
    case 'unknown':
      return background ? 'mediumGrayBg' : 'mediumGray';
  }
}

/*
 * Renders a rounded square with a color that indicates the condition of the
 * runnable (passed/failed/unknown/not yet run.) Shows icons instead of
 * dots for builds that haven't finished yet or were cancelled
 */
export var ConditionDot = React.createClass({

  propTypes: {
    // the runnable condition to render (see get_runnable_condition)
    condition: PropTypes.oneOf(all_build_conditions).isRequired,
    // renders a number inside the dot
    // only if dot >= small and we aren't rendering an icon
    // TODO: this
    num: PropTypes.oneOfType(PropTypes.number, PropTypes.string),
    // smaller = 12px, small = 16px
    size: PropTypes.oneOf(["smaller", "small", "medium", "large"]),
    // we have a special UI indicator to represent multiple builds
    multiIndicator: PropTypes.bool
  },

  getDefaultProps: function() {
    return {
      num: null,
      size: 'small',
      multiIndicator: false
    }
  },

  render: function() {
    var condition = this.props.condition;

    var dot = null;
    if (condition === 'waiting' || condition === 'failed_aborted') {
      var font_sizes = {
        smaller: 12,
        small: 16,
        medium: 26,
        large: 45
      };

      var style = {
        fontSize: font_sizes[this.props.size], 
      };
      if (this.props.size === 'medium') {
        style = _.extend(style, {marginLeft: 2, marginRight: 6});
      }

      var classes = {
        common: 'fa conditionDotIcon ',
        waiting: "fa-clock-o blue",  // blue instead of blue-gray
        'failed_aborted': 'red fa-ban'
      }
      var className = classes['common'] + classes[condition];

      dot = <i
        className={className}
        style={style}
      />;
    } else {
      var classes = [
        'conditionDot',
        this.props.size,
        get_runnable_condition_color_cls(condition, true),
        this.props.multiIndicator ? 'ring' : ''
      ];

      // cap num at 99 unless rendering the large widget
      var num = this.props.num;
      if (this.props.size !== 'large' && this.props.num > 99) {
        num = '99+';
      }

      var text = num && this.props.size !== "smaller" ?
        <span className="dotText">{num}</span> :
        null;

      dot = <span className={classes.join(" ")}>{text}</span>;
    }

    return <span>
      {dot}
    </span>;
  }
});

Examples.add('ConditionDot', __ => {
  return [
    <ConditionDot condition="passed" />,
    <ConditionDot condition="waiting" />,
    <ConditionDot condition="failed" />,
    <ConditionDot condition="failed_infra" />,
    <ConditionDot condition="failed_aborted" />,
    <ConditionDot condition="unknown" />,
    <div>
      <ConditionDot className="marginRightS" condition="passed" size="small" num={222} />
      <ConditionDot className="marginRightS" condition="passed" size="smaller" num={222} />
      <ConditionDot className="marginRightS" condition="passed" size="medium" num={222} />
      <ConditionDot className="marginRightS" condition="passed" size="large" num={222} />
    </div>,
    <div>
      <ConditionDot 
        className="marginRightS" 
        condition="passed" 
        size="small" 
        multiIndicator={true} 
      />
      <ConditionDot 
        className="marginRightS" 
        condition="passed" 
        size="smaller" 
        multiIndicator={true} 
      />
      <ConditionDot 
        className="marginRightS" 
        condition="passed" 
        size="medium" 
        multiIndicator={true} 
      />
      <ConditionDot 
        className="marginRightS" 
        condition="passed" 
        size="large" 
        multiIndicator={true} 
      />
    </div>,
    <div>
      <ConditionDot className="marginRightS" condition="failed" size="small" />
      <ConditionDot className="marginRightS" condition="failed" size="smaller" />
      <ConditionDot className="marginRightS" condition="failed" size="medium" />
      <ConditionDot className="marginRightS" condition="failed" size="large" />
    </div>
  ];
});
