import React, { PropTypes } from 'react';

import ChangesLinks from 'es6!display/changes/links';
import SimpleTooltip from 'es6!display/simple_tooltip';
import { get_runnable_condition, get_runnable_condition_color_cls } from 'es6!display/changes/builds';

/*
 * Renders a small bar chart of a series of builds.
 */
export var BuildsChart = React.createClass({

  MAX_CHART_HEIGHT: 40,  // pixels
  
  propTypes: {
    builds: PropTypes.array.isRequired,
    leftEllipsis: PropTypes.bool,
    rightEllipsis: PropTypes.bool,
  },

  getDefaultProps() {
    return { leftEllipsis: false, rightEllipsis: false };
  },
  
  render() {
    var builds = this.props.builds;
    
    // we'll render bar heights relative to this
    var longestBuildDuration = _.max(builds, b => b.duration).duration;

    var content = _.map(this.props.builds, build => {
      if (_.isEmpty(build)) {
        // would be nice to still show a tooltip here...
        return <div 
          className="chartBarColumn"
          style={{ paddingTop: this.MAX_CHART_HEIGHT - 2 }}>
          <div
            className="emptyChartBar"
            style={{height: 2}}
          />
        </div>;
      }

      var heightPercentage = build.duration / longestBuildDuration;
      var barHeight = Math.floor(heightPercentage * this.MAX_CHART_HEIGHT) || 1;

      var columnPadding = this.MAX_CHART_HEIGHT - barHeight;

      var bgColor = get_runnable_condition_color_cls(
        get_runnable_condition(build),
        true);

      // TODO: show more details about the build
      return <SimpleTooltip label={build.name} placement="bottom">
        <a 
          className="chartBarColumn" 
          href={ChangesLinks.buildHref(build)}
          style={{ paddingTop: columnPadding }}>
          <div 
            className={"chartBar " + bgColor} 
            style={{ height: barHeight }}
          />
        </a>
      </SimpleTooltip>;
    });

    // add ellipses
    if (this.props.leftEllipsis) {
      content.unshift(<div className="inlineBlock marginRightXS">...</div>);
    }
    if (this.props.rightEllipsis) {
      content.push(<div className="inlineBlock">...</div>);
    }

    return <div className="buildsChart">{content}</div>;
  }
});
