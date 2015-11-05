import React, { PropTypes } from 'react';
import { Button } from 'es6!display/button';

export var create = function(form, saveButtonText, _this) {
  let markup = _.map(form, section => {

    let sectionMarkup = _.map(section.fields, field => {

      if (field.type === 'text' || field.type === 'textarea' || field.type === 'select') {
        let placeholder = field.placeholder || '';

        let commentMarkup = null;
        if (field.comment) {
          commentMarkup = <div> {field.comment} </div>;
        }

        let tag = '';
        if (field.type === 'text') {
          tag = <input size="50" type="text" valueLink={_this.linkState(field.link)} placeholder={placeholder}/>;
        } else if (field.type === 'textarea') {
          tag = <textarea rows="10" cols="100" valueLink={_this.linkState(field.link)} placeholder={placeholder}/>;
        } else if (field.type === 'select') {
          let options = _.map(field.options, (option, name) => <option value={option}>{name}</option>);
          tag = <select valueLink={_this.linkState(field.link)} >{options}</select>;
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
            <div><input type='checkbox' checkedLink={_this.linkState(field.link)} /></div>
            {field.comment}
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

  let onSaveClicked = _ => _this.saveSettings();
  let saveButton = <Button onClick={onSaveClicked}>{saveButtonText}</Button>;
  return <div>{saveButton}{markup}</div>;
};
