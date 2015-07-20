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

export var update_state_key = function(map_key, key, value) {
  return (prev_state, current_props) => {
    var old_map = _.clone(prev_state[map_key]);
    old_map[key] = value;
    return {
      [ map_key ]: old_map
    };
  }
}

/*
 * Wraps func in window.setTimeout. This allows you to call functions 
 * like setState from render() (yes, there's a legitimate reason we do this...)
 * Make sure to call bind on func!
 */
export var async = function(func) {
  window.setTimeout(func, 0);
}

// TODO: use this regex to write a function that wraps urls in anchor tags
// var urlRegex =/(\b(https?|ftp|file):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]* \
// [-A-Z0-9+&@#\/%=~_|])/ig;
