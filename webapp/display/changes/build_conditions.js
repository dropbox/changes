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

const COND_PASSED = 'passed';
const COND_FAILED = 'failed';
const COND_FAILED_INFRA = 'failed_infra';
const COND_FAILED_ABORTED = 'failed_aborted';
const COND_UNKNOWN = 'unknown';
const COND_WAITING = 'waiting';
const COND_WAITING_WITH_ERRORS = 'waiting_with_errors';
const COND_WAITING_WITH_FAILURES = 'waiting_with_failures';

var all_build_conditions = [
  COND_PASSED,
  COND_FAILED,
  COND_FAILED_INFRA,
  COND_FAILED_ABORTED,
  COND_UNKNOWN,
  COND_WAITING,
  COND_WAITING_WITH_ERRORS,
  COND_WAITING_WITH_FAILURES,
];

export var is_waiting = function(condition) {
    return condition === COND_WAITING ||
           condition === COND_WAITING_WITH_ERRORS ||
           condition === COND_WAITING_WITH_FAILURES;
}

/*
 * Looks at a build/job/jobstep's status and result fields to figure out what
 * condition the build is in. There are a bunch of failure conditions with a
 * common prefix, so you can just check failure with indexOf(COND_FAILED) === 0.
 */
export var get_runnable_condition = function(runnable) {
  var status = runnable.status.id, result = runnable.result.id;

  if (status === 'in_progress' || status === "queued") {
    if (runnable.stats['test_failures']) {
      return COND_WAITING_WITH_ERRORS;
    }
    if (runnable.result.id === COND_FAILED) {
      return COND_WAITING_WITH_FAILURES;
    }
    return COND_WAITING;
  }

  if (result === COND_PASSED || result === COND_FAILED) {
    return result;
  } else if (result === 'aborted') {
    return COND_FAILED_ABORTED;
  } else if (result === 'infra_failed') {
    return COND_FAILED_INFRA;
  }
  return COND_UNKNOWN;
}

/*
 * Combines the conditions of a bunch of runnables into a single summary
 * condition: if any failed or haven't finished, returns failed/waiting, etc.
 */
export var get_runnables_summary_condition = function(runnables) {
  var any_condition = condition => _.any(runnables,
    r => get_runnable_condition(r) === condition);

  // I picked what I thought was a reasonable order here
  var any_aborted = any_condition(COND_FAILED_ABORTED);
  var any_failed_infra = any_condition(COND_FAILED_INFRA);
  var any_failed = any_condition(COND_FAILED);
  var any_waiting = any_condition(COND_WAITING);
  var any_waiting_with_errors = any_condition(COND_WAITING_WITH_ERRORS);
  var any_waiting_with_failures = any_condition(COND_WAITING_WITH_FAILURES);
  var any_unknown = any_condition(COND_UNKNOWN);

  return (any_aborted && COND_FAILED_ABORTED) ||
    (any_failed_infra && COND_FAILED_INFRA) ||
    (any_failed && COND_FAILED) ||
    (any_waiting_with_errors && COND_WAITING_WITH_ERRORS) ||
    (any_waiting_with_failures && COND_WAITING_WITH_FAILURES) ||
    (any_waiting && COND_WAITING) ||
    (any_unknown && COND_UNKNOWN) ||
    COND_PASSED;
}

// short, readable text for runnable conditions
export var get_runnable_condition_short_text = function(condition) {
  var names = {};
  names[COND_PASSED] = 'passed';
  names[COND_FAILED] = 'failed';
  names[COND_FAILED_ABORTED] = 'aborted';
  names[COND_FAILED_INFRA] = 'infrastructure failure';
  names[COND_WAITING_WITH_ERRORS] = 'in progress (errors occurred)';
  names[COND_WAITING_WITH_FAILURES] = 'in progress (test failures occurred)';
  names[COND_WAITING] ='in progress';
  return names[condition] || 'unknown';
}

export var get_runnable_condition_color_cls = function(condition, background = false) {
  switch (condition) {
    case COND_PASSED:
      return background ? 'greenBg' : 'green';
    case COND_FAILED:
    case COND_FAILED_ABORTED:
    case COND_WAITING_WITH_FAILURES:
      return background ? 'redBg' : 'red';
    case COND_FAILED_INFRA:
    case COND_WAITING_WITH_ERRORS:
      return background ? 'blackBg' : 'black';
    case COND_WAITING:
      return background ? 'bluishGrayBg' : 'bluishGray';
    case COND_UNKNOWN:
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
    // renders a number inside the dot. Despite the name, you can render a
    // letter too (e.g. "!")
    // (only if dot >= small and we aren't rendering an icon)
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
    if (condition === COND_WAITING ||
        condition === COND_WAITING_WITH_FAILURES ||
        condition === COND_WAITING_WITH_ERRORS ||
        condition === COND_FAILED_ABORTED) {
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
      };
      classes[COND_WAITING] = 'fa-clock-o blue'; // blue instead of blue-gray
      classes[COND_WAITING_WITH_FAILURES] = 'fa-clock-o red';
      classes[COND_WAITING_WITH_ERRORS] = 'fa-clock-o black';
      classes[COND_FAILED_ABORTED] = 'red fa-ban';
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
      if (this.props.size !== 'large' && 
          (_.isFinite(num) && num > 99)) {
        num = '99+';
      }

      if ((_.isString(num) && num.length === 1) || 
          (_.isFinite(num) && num > 0 && num < 9)) {
        classes.push('singleDigit');
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
    <ConditionDot condition="waiting_with_errors" />,
    <ConditionDot condition="waiting_with_failures" />,
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
