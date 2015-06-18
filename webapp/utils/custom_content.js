/*
 * Your deployment of changes may want to include custom content, e.g. links to
 * internal tools, contextual help on what to do if a build fails, etc. Add
 * custom_content_hook at places in the ui where you might want to do this
 * (we've added a bunch for ourselves already), and follow the instructions at
 * the bottom to create your own custom content.
 */

// default_content: what to return if no custom content was provided for name
// extra_data: if the custom content is a function, it will be called with
//             extra_data as its first parameter
function custom_content_hook(name, default_content, extra_data) {
  default_content = default_content || null;

  var custom_content = window.changesCustomContent && 
    window.changesCustomContent[name];

  // empty string is a valid return value
  if (!custom_content && custom_content !== '') {
    return default_content;
  }

  if (_.isFunction(custom_content)) {
    custom_content = custom_content.call(this, extra_data);
  }

  return custom_content;
}

export default custom_content_hook;

/* Creating a custom content file.
 * - Use ES6 syntax and modules. You can import libraries like react
 * - You should export a dictionary that maps hook names to strings,
 *   functions, or react components. extra_data is only used funcs.
 *
 * Example:
 * 
 * import React from 'react';
 *
 * var content = {
 *   errorLink: <a href='https://internal.bigcompany.com/error_dashboard/changes'>
 *     Errors
 *   </a>
 * };
 *
 * export default content;
 */
