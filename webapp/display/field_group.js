import React, { PropTypes } from 'react';
import { Button } from 'es6!display/button';
import SimpleTooltip from 'es6!display/simple_tooltip';

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

// A Mixin to track changes in form fields. Components that use this mixin
// can enable/disable save/submit buttons based on whether or not the form
// fields are dirty.
//
// DiffFormMixin monitors the values of state keys that are whitelisted by
// getFieldKeys() on the host object.
//
// The mixin stores last-saved-state data on the component as
// diffFormSavedState. This is simply a copy of the component's .state from
// the last time it was saved.
export var DiffFormMixin = {

  // Use onFormSubmit as a callback to any api.js post/get/delete call.
  onFormSubmit: function(api_response, all_successes) {
    if (!all_successes || api_response.condition !== 'loaded') {
      return false;
    }

    // POST was successful. Update the known saved state.
    this.updateSavedFormState();
    return true;
  },

  // Returns true if any component state values have changed since the last time
  // the form was submitted (onFormSubmit was called).
  hasFormChanges: function(currentState) {
    let savedState = this.state.diffFormSavedState;
    for (let key in savedState) {
      let savedValue = savedState[key];
      let currentValue = currentState[key];

      // Text fields are often initialized to undefined values instead of empty values.
      // Normalize these values to empty strings.
      if (savedValue === undefined) {
          savedValue = '';
      }
      if (currentValue === undefined) {
          currentValue = '';
      }

      if (savedValue != currentValue) {
        return true;
      }
    }
    return false;
  },

  // This is called automatically whenever onFormSubmit is triggered. It should
  // also be specified as a setState callback at mount time when
  // forms/components are loaded in order to specify the form's initial state.
  updateSavedFormState: function() {
    if (this.getFieldNames === undefined) {
        throw Error('getFieldNames() must be defined on the DiffFormMixin ' +
                    'host object. It returns a list of names of state fields ' +
                    'that should be monitored to enable/disable the ' +
                    'Submit/Save button on forms.');
    }
    let fieldNames = this.getFieldNames();
    let savedState = {};
    for (let i = 0; i < fieldNames.length; ++i) {
      let key = fieldNames[i];
      savedState[key] = this.state[key];
    }

    for (let key in this.state) {
        if (!(key in savedState)) {
            console.log(
                `DiffFormMixin is ignoring state field '${key}'. If this is ` +
                'not an input field on the form on this page, everything is ' +
                'fine. However, if this IS a form input field, you should ' +
                'add it to getFieldNames() on the form page/object to ' +
                'support form diffing.');
        }
    }

    this.setState({ diffFormSavedState: savedState });
  }
}

export var create = function(form, saveButtonText, _this, messages=[], extraButtons=[]) {
  // If the form doesn't track its changed state, always enable the save button.
  let hasChanges = true;
  if (_this.hasFormChanges !== undefined) {
    hasChanges = _this.hasFormChanges(_this.state);
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
        valueLink.requestChange = makeChangeFunc(_this, field.link);

        let tag = '';
        if (field.type === 'text') {
          tag = <input size="50" type="text" valueLink={valueLink} placeholder={placeholder}/>;
        } else if (field.type === 'textarea') {
          tag = <textarea rows="10" cols="80" valueLink={valueLink} placeholder={placeholder}/>;
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
        let checkedLink = _this.linkState(field.link);
        checkedLink.requestChange = makeChangeFunc(_this, field.link);
        return <div className="marginBottomS">
          <label>
            <div><input type='checkbox' checkedLink={checkedLink} /> {field.comment} </div>
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

  // If changes are pending, show the button as enabled with an active onclick.
  // If no changes are pending, show the button as disabled and clicking does nothing.
  let saveDisabled = '';
  let onSaveClicked = null;
  if (!hasChanges) {
    saveDisabled = 'disabled';
    onSaveClicked = null;
  } else {
    onSaveClicked = _ => {
      _this.saveSettings();
    }
  }
  let saveButton =
      <Button onClick={onSaveClicked} className={saveDisabled}>{saveButtonText}</Button>
  if (!hasChanges) {
    saveButton =
        <SimpleTooltip label="There are no pending changes to save.">{saveButton}</SimpleTooltip>;
  }

  // Clone extraButtons to avoid mutating the function param with the subsequent unshift.
  let allButtons = _.clone(extraButtons);
  allButtons.unshift(saveButton);

  return <div>
    {markup}
    <div>{allButtons}</div>
    {messageDivs}
  </div>;
};

var makeChangeFunc = function(_this, fieldLink) {
  return function(newValue) {
    let newState = {};
    newState[fieldLink] = newValue;
    _this.setState(newState);
  }
};
