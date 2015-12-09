import React, { PropTypes } from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesUI from 'es6!display/changes/ui';

import * as api from 'es6!server/api';

import custom_content_hook from 'es6!utils/custom_content';

/*
 * Shows captured output and artifacts for a test
 */
export var TestDetails = React.createClass({
  propTypes: {
    testID: PropTypes.string,
    buildID: PropTypes.string
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

    var testDetailsHelpText = custom_content_hook('testDetailsHelpText', null, test.project.id)
    if (testDetailsHelpText) {
      testDetailsHelpText = ChangesUI.linkifyURLs(testDetailsHelpText);
      testDetailsHelpText = <div className="green" style={{marginBottom: 15}}>
        <i className="fa fa-info-circle marginRightS"></i>
        {testDetailsHelpText}
      </div>;
    }

    var permalink = <div>
        <a href={"/build_test/" + this.props.buildID + "/" + test.id}>
        Link
        </a>
        </div>;

    return <div {...props} className={className}>
      {testDetailsHelpText}
      <b>Captured Output</b>
      <pre className="defaultPre">
      {test.message}
      </pre>
      {this.renderArtifacts(test)}
      <p/>
      {permalink}
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
    markup.push(<div className="lb marginTopM">Logs</div>);

    var log_url = `/job_log/${this.props.buildID}/${test.logSource.job.id}/${test.logSource.id}/`;
    markup.push(<a className="marginRightM" href={log_url} target="_blank">Console log</a>);

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
      markup.push(<div className="lb marginTopM marginBottomS">Images</div>);
      _.each(imageArtifacts, a => {
        markup.push(
          <div> <a target="_blank" href={a.url}>
            <div className="artifactImageName">{a.name}</div>
            <img className="artifactImage" src={a.url} />
          </a> </div>
        );
      });
    }

    return markup;
  }
});
