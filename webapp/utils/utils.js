// jondoe@company.com -> jondoe
export var email_localpart = function(email) {
  return email.substring(0, email.indexOf('@'));
}

export var truncate = function(str, length = 80) {
  if (str.length > 80) {
    str = str.substr(0, 77) + "...";
  }
  return str;
}

// Example: is_one_of(str, ["headers", "odd", "even"])
export var is_one_of = function(str, possibles) {
  var matches = false;
  _.each(possibles, p => {
    if (str === p) { matches = true; }
  });
  return matches;
}

export var assert_is_one_of = function(str, possibles) {
  if (!is_one_of(str, possibles)) {
    var possibles_str = JSON.stringify(possibles);
    throw(`Expected one of ${possibles_str}, got ${str}`);
  }
}

// TODO: use this regex to write a function that wraps urls in anchor tags
// var urlRegex =/(\b(https?|ftp|file):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]* \
// [-A-Z0-9+&@#\/%=~_|])/ig;

