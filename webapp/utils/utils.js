/*
 * Collection of useful utils, e.g. string manipulation/parsing, some
 * utils to make interacting with setState easier, etc.
 *
 * Some more changes-specific stuff is in display/changes/utils.py
 */

//
// Generic stuff
//

// jondoe@company.com -> jondoe. leaves non-emails untouched
export var email_head = function(email) {
  return email.indexOf('@') >= 0 ?
    email.substring(0, email.indexOf('@')) :
    email;
}

// truncates a string to length-3 chars and adds ...
export var truncate = function(str, length = 80) {
  if (str.length > length) {
    str = str.substr(0, length - 3) + "...";
  }
  return str;
}

// splits a string into an array of lines
export var split_lines = function(text) {
  if (text === "") {
    return [text];
  }
  return text.match(/[^\r\n]+/g);
}

// gets the first line of a string
export var first_line = function(text) {
  return _.first(split_lines(text));
}

// pads a number with leading zeroes up to size digits
export var pad = function(num, size) {
  var ret = num + "";
  while (ret.length < size) {
    ret = "0" + ret;
  }
  return ret;
}

// if item is not an array, make it a one-element array
export var ensureArray = function(item) {
  if (!_.isArray(item)) {
    item = [item];
  }
  return item;
}

// takes a list of strings and splits each of them into a three-tuple of common
// prefix (across all strings), unique middle, and common suffix. Some parts
// may be ''.
export var split_start_and_end = function(strings) {
  var prefix = get_common_prefix(strings);
  var suffix = get_common_suffix(strings);
  var dict = {};
  _.each(strings, s => {
    dict[s] = [prefix,
      s.substring(prefix.length, s.length - suffix.length),
      suffix];
  });
  return dict;
}

// given a list of strings, finds their longest common prefix
export var get_common_prefix = function(strings) {
  if (strings.length === 0) {
    return '';
  }

  var common_prefix = '';
  for (var i = 0; i < strings[0].length; i++) {
    var char_to_check = strings[0].charAt(i);
    var matches = true;
    _.each(strings, s => {
      if (s.length < i + 1 || s.charAt(i) !== char_to_check) {
        matches = false;
        return;
      }
    });
    if (matches) {
      common_prefix += char_to_check;
    } else {
      break;
    }
  }
  return common_prefix;
}

// plural(1, "test(s) passed") -> "1 test passed"
// plural(2, "test(s) passed") -> "2 tests passed"
// if use_no is set, No will be used in place of 0 (or no if not capitalize)
export var plural = function(num, text, use_no = false, capitalize = false) {
  if (num === 1) {
    return num + " " + text.replace("(s)", "");
  }
  text = text.replace("(s)", "s");

  if (num === 0 && use_no) {
    return (capitalize ? 'No ' : 'no ') + text;
  }
  return num + " " + text;
}

// as get_common_prefix, but for suffixes
export var get_common_suffix = function(strings) {
  var reversed_strings = _.map(strings, s => s.split('').reverse().join(''));
  var rcommon_prefix = get_common_prefix(reversed_strings);
  return rcommon_prefix.split('').reverse().join('');
}

// Wraps func in window.setTimeout. This allows you to call functions
// like setState from render() (yes, there's a legitimate reason we do this...)
// Make sure to call bind on func!
export var async = function(func) {
  window.setTimeout(func, 0);
}

// allows you to update a single key in a dict stored in a react elem's state.
// Preserves prototype, but doesn't play well with es6 classes
// TODO: this may accidentally promote properties from the prototype to the
// object
// Usage: this.setState(utils.update_key_in_state_dict(...))
export var update_key_in_state_dict = function(map_key, key, value) {
  return update_state_dict(map_key, {[ key ]: value});
}

// as above, but updates multiple keys
export var update_state_dict = function(map_key, updates) {
  return (prev_state, current_props) => {
    var prev_obj = prev_state[map_key] || {};
    var old_map = _.create(Object.getPrototypeOf(prev_obj), {});
    old_map = _.extendOwn(old_map, prev_obj, updates);
    return {
      [ map_key ]: old_map
    };
  }
}

export var to_underscore = function(camelcase) {
  return this.replace(/([A-Z])/g, function($1){return "_"+$1.toLowerCase();});
}

export var setPageTitle = function(title) {
  if (window.changesGlobals.IS_DEBUG) {
    title = "\u2699 " + title;
  }
  window.document.title = title;
}

export var randomID = function() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
    return v.toString(16);
  });
}
