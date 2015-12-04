import React, { PropTypes } from 'react';
import { Button } from 'es6!display/button';

// Convenience function for generating redirect callbacks on successful form saves.
// `redirectUrl` should be a function that takes a json-parsed response object and
// returns the url to redirect to on success.
export var redirectCallback = function(fieldGroup, redirectUrl) {
  return (response, was_success) => {
      if (was_success) {
        window.location.href = redirectUrl(JSON.parse(response.responseText));
      } else {
        fieldGroup.setState({ error: response.responseText });
      }
  };
}

export var create = function(form, saveButtonText, _this, messages=[]) {
  let hasChanges = _this.state.hasFormChanges;
  if (hasChanges === undefined) {
    // Since we can't tell if this form has changes, default to true.
    hasChanges = true;
  }

  let markup = _.map(form, section => {
    let sectionMarkup = _.map(section.fields, field => {
      if (field.type === 'text' || field.type === 'textarea' || field.type === 'select') {
        let placeholder = field.placeholder || '';

        let commentMarkup = null;
        if (field.comment) {
          commentMarkup = <div> {field.comment} </div>;
        }

        // valueLink is a ReactLink object which has a `value` field and `requestChange` field.
        // See React docs on ReactLink for details: https://facebook.github.io/react/docs/two-way-binding-helpers.html
        let valueLink = _this.linkState(field.link);
        valueLink.requestChange = function(newValue) {
          let newState = {};
          newState[field.link] = newValue;
          newState['hasFormChanges'] = true;
          _this.setState(newState);
        };

        let tag = '';
        if (field.type === 'text') {
          tag = <input size="50" type="text" valueLink={valueLink} placeholder={placeholder}/>;
        } else if (field.type === 'textarea') {
          tag = <textarea rows="10" cols="100" valueLink={valueLink} placeholder={placeholder}/>;
        } else if (field.type === 'select') {
          let options = _.map(field.options, (option, name) => <option value={option}>{name}</option>);
          tag = <select valueLink={valueLink} >{options}</select>;
        }

        return <div className="marginBottomS">
          <div> {field.display ? field.display + ':' : ''} </div>
          {tag}
          {commentMarkup}
          <hr />
        </div>;
      } else if (field.type === 'checkbox') {
        return <div className="marginBottomS">
          <label>
            <div><input type='checkbox' checkedLink={_this.linkState(field.link)} /> {field.comment} </div>
          </label>
          <hr />
        </div>;
      } else {
        throw 'unreachable';
      }
    });

    return <div>
      <h2>{section.sectionTitle}</h2>
      {sectionMarkup}
    </div>;
  });

  let messageDivs = _.map(messages, m => {
    return <div>{m}</div>;
  });

  let onSaveClicked = _ => _this.saveSettings();
  let saveButton = hasChanges ? <Button onClick={onSaveClicked}>{saveButtonText}</Button> : '';
  return <div>{saveButton}{messageDivs}{markup}</div>;
};
