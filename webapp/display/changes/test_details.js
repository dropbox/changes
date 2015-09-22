import React, { PropTypes } from 'react';

import APINotLoaded from 'es6!display/not_loaded';

import * as api from 'es6!server/api';

/*
 * Shows captured output and artifacts for a test
 */
export var TestDetails = React.createClass({
  propTypes: {
    testID: PropTypes.number,
  },

  getInitialState: function() {
    return {};
  },

  componentDidMount: function() {
    api.fetch(this, {
      test: `/api/0/tests/${this.props.testID}/`
    });
  },

  render: function() {
    var { testID, className, ...props} = this.props;

    if (!api.isLoaded(this.state.test)) {
      return <APINotLoaded calls={this.state.test} />;
    }
    var test = this.state.test.getReturnedData();

    className = (className || "") + " testDetails";

    return <div {...props} className={className}>
      <div className="marginTopS">
        <b>Captured Output</b>
        <pre className="defaultPre">
        {test.message}
        </pre>
      </div>
      {this.renderArtifacts(test)}
    </div>;
  },

  renderArtifacts(test) {
    var artifactsOfType = type => {
      return _.filter(test.artifacts, a => a.type.id === type);
    }

    var textArtifacts = artifactsOfType('text'),
      htmlArtifacts = artifactsOfType('html'),
      imageArtifacts = artifactsOfType('image');

    var markup = [];
    if (textArtifacts.length > 0) {
      markup.push(<div className="lb marginTopM">Other Logs</div>);
      _.each(textArtifacts, a => {
        markup.push(
          <div> <a className="external" target="_blank" href={a.url}>
            {a.name}
          </a> </div>
        );
      });
    }

    if (htmlArtifacts.length > 0) {
      markup.push(<div className="lb marginTopM">HTML Files</div>);
      _.each(htmlArtifacts, a => {
        markup.push(
          <div> <a className="external" target="_blank" href={a.url}>
            {a.name}
          </a> </div>
        );
      });
    }

    if (imageArtifacts.length > 0) {
      markup.push(<div className="lb marginTopM">Images</div>);
      _.each(imageArtifacts, a => {
        markup.push(
          <div> <a target="_blank" href={a.url}>
            <img className="artifactImage" src={a.url} />
          </a> </div>
        );
      });
    }

    return markup;
  }
});
