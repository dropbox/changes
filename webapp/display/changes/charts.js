import React, { PropTypes } from 'react';

import ChangesLinks from 'es6!display/changes/links';
import SimpleTooltip from 'es6!display/simple_tooltip';
import { ProgrammingError } from 'es6!display/errors';
import {
  get_runnable_condition,
  get_runnable_condition_color_cls,
  get_runnable_condition_short_text
} from 'es6!display/changes/build_conditions';

/*
 * Renders a small bar chart of a series of builds/tests/maybe others
 */
export var ChangesChart = React.createClass({

  MAX_CHART_HEIGHT: 40,  // pixels
  
  propTypes: {
    type: PropTypes.oneOf(['build', 'test']).isRequired,
    runnables: PropTypes.array.isRequired,
    // if enabled, we'll show a 'latest' label
    enableLatest: PropTypes.bool
  },

  getDefaultProps() {
    return { enableLatest: true };
  },

  render() {
    var { runnables, className, } = this.props;

    // we'll render bar heights relative to this
    // We sortBy(identity) because using sort() sorts by string representation, which is wrong.
    var longestDuration = _.chain(runnables).compact().pluck('duration').sortBy(_.identity).last().value();

    var content = _.map(this.props.runnables, (runnable, idx) => {
      var no_duration = runnable && !runnable.duration && runnable.duration === 0;
      if (_.isEmpty(runnable) || no_duration) {
        // would be nice to still show a tooltip here...
        return <div key={(runnable && runnable.id) || ("empty:" + idx)}
          className="chartBarColumn"
          style={{ paddingTop: this.MAX_CHART_HEIGHT - 2 }}>
          <div
            className="emptyChartBar"
            style={{height: 2}}
          />
        </div>;
      }

      var heightPercentage = runnable.duration / longestDuration;
      var barHeight = Math.floor(heightPercentage * this.MAX_CHART_HEIGHT) || 1;

      var columnPadding = this.MAX_CHART_HEIGHT - barHeight;

      var condition = get_runnable_condition(runnable);
      var bgColor = get_runnable_condition_color_cls(condition, true);
      var label = get_runnable_condition_short_text(condition, true);

      var tooltipText = null, href = null;
      if (this.props.type === 'build') {
        // TODO: show more details about the build
        tooltipText = runnable.name;
        href = ChangesLinks.buildHref(runnable);
      } else if (this.props.type === 'test') {
        // TODO: show more details about the test
        tooltipText = runnable.result.name;
        href = ChangesLinks.buildTestHref(runnable.job.build.id, runnable);
      } else {
        return <ProgrammingError>
          Unknown type {this.props.type}
        </ProgrammingError>;
      }

      return <SimpleTooltip label={tooltipText} placement="top" key={runnable.id}>
        <a 
          className="chartBarColumn" 
          href={href}
          style={{ paddingTop: columnPadding }}>
          <div 
            className={"chartBar " + bgColor}
            alt={label}
            title={label}
            style={{ height: barHeight }}
          />
        </a>
      </SimpleTooltip>;
    });

    if (this.props.enableLatest) {
      content.unshift(<LatestWidget key="latest" />);
    }

    var className = " changesChart " + (className || "");
    return <div className={className}>{content}</div>;
  }
});

var LatestWidget = React.createClass({
  render() {
    var divStyle = {
      position: 'absolute',
      marginLeft: -12,
      marginTop: -18,
      fontSize: 'xx-small',
    };

    var spanStyle = {
      backgroundColor: '#000000',
      color: 'white',
      padding: '1px 4px',
      borderRadius: 3
    };

    var caretStyle = {
      display: 'block',
      fontSize: 13,
      marginLeft: 13,
      marginTop: -4
    };

    return <div style={divStyle}>
      <span style={spanStyle}>Latest</span>
      <i style={caretStyle} className="fa fa-caret-down" />
    </div>;
  }
});
