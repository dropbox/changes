var fetchText, _buildMap = {};

//>>excludeStart('excludeBabel', pragmas.excludeBabel)
if (typeof window !== "undefined" && window.navigator && window.document) {
    fetchText = function (url, callback) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.onreadystatechange = function (evt) {
            //Do not explicitly handle errors, those should be
            //visible via console output in the browser.
            if (xhr.readyState === 4) {
                callback(xhr.responseText);
            }
        };
        xhr.send(null);
    };
} else if (typeof process !== "undefined" &&
           process.versions &&
           !!process.versions.node) {
    //Using special require.nodeRequire, something added by r.js.
    fs = require.nodeRequire('fs');
    fetchText = function (path, callback) {
        callback(fs.readFileSync(path, 'utf8'));
    };
}
//>>excludeEnd('excludeBabel')

define([
    //>>excludeStart('excludeBabel', pragmas.excludeBabel)
    'babel',
    //>>excludeEnd('excludeBabel')
    'module'
], function(
    //>>excludeStart('excludeBabel', pragmas.excludeBabel)
    babel,
    //>>excludeEnd('excludeBabel')
    _module
    ) {
    return {
        load: function (name, req, onload, config) {
            //>>excludeStart('excludeBabel', pragmas.excludeBabel)
            function applyOptions(options) {
                var defaults = {
                    modules: 'amd',
                    sourceMap: config.isBuild ? false :'inline',
                    sourceFileName: name
                };
                for(var key in options) {
                    if(options.hasOwnProperty(key)) {
                        defaults[key] = options[key];
                    }
                }
                return defaults;
            }
            var url = req.toUrl(name + '.js');

            fetchText(url, function (text) {
                var code = babel.transform(text, applyOptions(_module.config())).code;

                if (config.isBuild) {
                    _buildMap[name] = code;
                }

                onload.fromText(code); 
            });
            //>>excludeEnd('excludeBabel')
        },

        write: function (pluginName, moduleName, write) {
            if (moduleName in _buildMap) {
                write.asModule(pluginName + '!' + moduleName, _buildMap[moduleName]);
            }
        }
    }
});
