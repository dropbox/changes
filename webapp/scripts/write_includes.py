#!/usr/bin/env python

# this is a super hacky script that rewrites all of the import statements at
# the top of every javascript file. I didn't want to read through an entire
# parse tree and handle all of the corner cases, so the way this works is the
# script generates a list of every single export in the codebase, then goes
# file by file, greps for all of the exported identifiers, and uses that to
# replace every import statement. It also manually adds import react, bootstrap
# imports, and some other special cases (search for "special cases")

REACT_BOOTSTRAP_COMPONENTS_USED = [
  'Popover',
  'OverlayTrigger',
  'Tooltip',
  'Modal',
  'Dropdown'
]

import os, re, sys

# for debugging
import pprint
pp = pprint.PrettyPrinter(indent=4)
slog = pp.pprint

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

class Exports:
  """
  give it a bunch of javascript files and it'll figure out what each file
  exports. It can then take an arbitrary javascript file and figure out
  what import statements that file should have from its library of exports.
  It can't detect that a file might be trying to import something that's
  not in its export library
  """

  def __init__(self):
    self.items = {}

  def add(self, path, text):
    """adds a javascript file to the export library"""
    include_path = path.replace(ROOT_DIR, '').replace('.js', '').strip("/")
    item = {
      "path": path,
      "include_path": include_path,
      "mode": "unknown",
      "text": text,
      "exports": []
    }

    for line in text.splitlines():
      if line.startswith("export"):
        words = line.split(" ")
        if words[1] == "var" or words[1] == 'class':
          item['mode'] = "multi"
        elif words[1] == "default":
          item['mode'] = "default"
        else:
          raise ValueError("unknown export type %s" % (words[1], ))
        item['exports'].append(words[2].strip(";"))

    if len(item['exports']) > 1 and item['mode'] == "default":
      raise ValueError("can only export one default! path = %s" % path)

    self.items[path] = item

  def replace_imports(self, path, text):
    # trash all of the import lines
    start = -1
    for index, line in enumerate(text.splitlines()):
      if line.startswith("import"):
        start = index

    remaining_lines = text.splitlines()[start+1:]
    program = "\n".join(remaining_lines).strip()
    without_most_comments = self.trash_comments(program)

    # find exports that are being used
    imports_to_add = [] # contains pairs of import statements/include paths
    for key, item in self.items.items():
      if item['path'] == path:
        continue

      exports_in_file = []
      export_prefixes = []
      for exp in item['exports']:
        if re.search("[^\w]%s[^\w]" % (exp, ), without_most_comments):
          exports_in_file.append(exp)
        # we also want to find things like api.fetch
        prefix_search = re.search("(\w*)\."+exp, without_most_comments)
        if prefix_search:
          export_prefixes.append(prefix_search.group(1))

      if not exports_in_file:
        continue

      if len(set(export_prefixes)) > 1:
        raise ValueError("I don't know how to include the file %s for the file %s" %
          (item["path"], path))

      export_prefix = None
      if len(export_prefixes) > 0:
        export_prefix = export_prefixes[0]

      if (item["mode"] == "default"):
        imports_to_add.append((
          "import %s from 'es6!%s';" % (exports_in_file[0], item['include_path']),
          item['include_path']
        ))
      else:
        if export_prefix:
          imports_to_add.append((
            "import * as %s from 'es6!%s';" % (export_prefix, item['include_path']),
            item['include_path']
          ))
        else:
          imports_to_add.append((
            "import { %s } from 'es6!%s';" % (", ".join(exports_in_file), item['include_path']),
            item['include_path']
          ))
    # end of for block

    # special cases

    # if we have a closing/self-closing html tag, we should probably import 
    # react.
    # todo: strip out comments from this search string
    other_imports = ""
    if (re.search("<\/\w", without_most_comments) or 
      re.search("\/>", without_most_comments)):
      other_imports += "import React, { PropTypes } from 'react';\n"

    if "moment(" in without_most_comments or "moment." in without_most_comments:
      other_imports += "import moment from 'moment';\n"

    react_bootstrap_components = [c for c in REACT_BOOTSTRAP_COMPONENTS_USED
      if re.search("[^\w]%s[^\w]" % (c, ), without_most_comments)]
    if react_bootstrap_components:
      other_imports += "import { %s } from 'react_bootstrap';\n" % (", ".join(react_bootstrap_components), );

    if other_imports: other_imports += "\n"

    # the way I want to render imports is in directory order, with an extra
    # newline between directories
    import_lines = ""
    directories = set([pair[1][:pair[1].find("/")] for pair in imports_to_add])
    for dir in sorted(directories):
      import_lines += "\n".join(sorted([pair[0] for pair in imports_to_add
        if pair[1].startswith(dir)]))
      import_lines += "\n\n"
    return other_imports + import_lines + program

  def trash_comments(self, program):
    # right now, this only deletes multiline comments
    return re.sub(r'/\*([\s\S]*?)\*/', '', program);

exports = Exports()
js_files = {}

for dirpath, dirs, files in os.walk(ROOT_DIR):
  for name in files:
    if not name.endswith(".js"):
      continue
    if "entry.js" in name:
      continue # not es6
    if "built.js" in name and "dist" in dirpath:
      continue # ignore prod build

    full_path = os.path.join(dirpath, name)
    text = open(full_path, 'r').read().strip()
    exports.add(full_path, text)

    js_files[full_path] = text

for full_path, text in js_files.items():
    new_text = exports.replace_imports(full_path, text)
    open(full_path, 'w').write(new_text + "\n")

print "done"
