/*
 * Collection of useful utils, e.g. string manipulation/parsing, some
 * utils to make interacting with setState easier, etc.
 *
 * More display-specific utils are in changes_utils.py in display
 */

// TODO: rename this generic.js

// jondoe@company.com -> jondoe
export var email_head = function(email) {
  return email.substring(0, email.indexOf('@'));
}

export var truncate = function(str, length = 80) {
  if (str.length > length) {
    str = str.substr(0, length - 3) + "...";
  }
  return str;
}

export var split_lines = function(text) {
  if (text === "") {
    return [text];
  }
  return text.match(/[^\r\n]+/g);
}

export var first_line = function(text) {
  return _.first(split_lines(text));
}

export var pad = function(num, size) {
  var ret = num + "";
  while (ret.length < size) {
    ret = "0" + ret;
  }
  return ret;
}

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

export var get_common_suffix = function(strings) {
  var reversed_strings = _.map(strings, s => s.split('').reverse().join(''));
  var rcommon_prefix = get_common_prefix(reversed_strings);
  return rcommon_prefix.split('').reverse().join('');
}

/*
 * Wraps func in window.setTimeout. This allows you to call functions
 * like setState from render() (yes, there's a legitimate reason we do this...)
 * Make sure to call bind on func!
 */
export var async = function(func) {
  window.setTimeout(func, 0);
}

// allows you to update a single key in a dict stored in a react elem's state.
// Preserves prototype
export var update_key_in_state_dict = function(map_key, key, value) {
  return update_state_dict(map_key, {[ key ]: value});
}

// as above, but updates multiple keys
export var update_state_dict = function(map_key, updates) {
  return (prev_state, current_props) => {
    var old_map = _.create(
      Object.getPrototypeOf(prev_state[map_key]),
      prev_state[map_key]);
    old_map = _.extend(old_map, updates);
    return {
      [ map_key ]: old_map
    };
  }
}

// TODO: move out of this file
export var get_short_repo_name = function(repo_url) {
  return _.last(_.compact(repo_url.split(/:|\//)));
}
