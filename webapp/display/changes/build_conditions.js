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

export const COND_PASSED = 'passed';
export const COND_FAILED = 'failed';
export const COND_FAILED_INFRA = 'failed_infra';
export const COND_FAILED_ABORTED = 'failed_aborted';
export const COND_UNKNOWN = 'unknown';
export const COND_WAITING = 'waiting';
export const COND_WAITING_WITH_ERRORS = 'waiting_with_errors';
export const COND_WAITING_WITH_FAILURES = 'waiting_with_failures';

const ICON_CLASSES = {
  [ COND_PASSED ]: 'fa-check-circle green',
  [ COND_FAILED ]: 'fa-times-circle red',
  [ COND_FAILED_INFRA ]: 'fa-exclamation-circle black',
  [ COND_WAITING ]: 'fa-clock-o blue', // blue instead of blue-gray
  [ COND_WAITING_WITH_FAILURES ]: 'fa-clock-o red',
  [ COND_WAITING_WITH_ERRORS ]: 'fa-clock-o black',
  [ COND_FAILED_ABORTED ]: 'red fa-ban',
}

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
 * Looks at a build/job/jobstep/test's status and result fields to figure out what
 * condition the build is in.
 */
export var get_runnable_condition = function(runnable) {
  const status = runnable.status ? runnable.status.id : 'finished';
  var result = runnable.result.id;

  if (status === 'in_progress' || status === 'queued' || status === 'pending_allocation') {
    if (runnable.stats && runnable.stats['test_failures']) {
      return COND_WAITING_WITH_ERRORS;
    }
    if (runnable.result && runnable.result.id === 'failed') {
      return COND_WAITING_WITH_FAILURES;
    }
    return COND_WAITING;
  }

  const result_condition = {
      'passed':              COND_PASSED,
      'quarantined_passed':  COND_PASSED,
      'failed':              COND_FAILED,
      'quarantined_failed':  COND_FAILED,
      'skipped':             COND_UNKNOWN,
      'quarantined_skipped': COND_UNKNOWN,
      'aborted':             COND_FAILED_ABORTED,
      'infra_failed':        COND_FAILED_INFRA,
  };
  return result_condition[result] || COND_UNKNOWN;
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
  var names = {
      [ COND_PASSED ]: 'passed',
      [ COND_FAILED ]: 'failed',
      [ COND_FAILED_ABORTED ]: 'aborted',
      [ COND_FAILED_INFRA ]: 'infrastructure failure',
      [ COND_WAITING_WITH_ERRORS ]: 'in progress (errors occurred)',
      [ COND_WAITING_WITH_FAILURES ]: 'in progress (test failures occurred)',
      [ COND_WAITING ]:'in progress',
  };
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

var get_runnable_condition_icon_classname = function(condition) {
  var iconClassName = 'fa conditionDotIcon ';

  if (ICON_CLASSES[condition]) {

    return iconClassName + ICON_CLASSES[condition];
  }
  // to generate icons for projects that do not
  // have any builds (for the projects page, for example)
  return iconClassName + 'fa-circle-thin blue';
}

export var get_runnable_condition_icon = function(condition) {
  return <i className={get_runnable_condition_icon_classname(condition)} />;
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
    // letter too (e.g. "E"). Takes precedent over icons.
    // (only if dot >= small)
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
    var num = this.props.num;

    var dot = null;
    if (ICON_CLASSES[condition] && num === null) {
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

      var className = get_runnable_condition_icon_classname(condition);

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
