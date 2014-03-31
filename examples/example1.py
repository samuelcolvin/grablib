target =  "static_libs"
libs = {
  "https://raw.github.com/twbs/bootstrap/v3.1.1/dist/css/bootstrap.min.css": "{{ filename }}",
  "https://raw.github.com/twbs/bootstrap/v3.1.1/dist/css/bootstrap-theme.min.css": "{{ filename }}",
  "https://raw.github.com/twbs/bootstrap/v3.1.1/dist/js/bootstrap.min.js": "{{ filename }}",
  "http://code.jquery.com/jquery-1.11.0.min.js": "jquery.min.js",
  "https://github.com/makeusabrew/bootbox/releases/download/v4.2.0/bootbox.min.js": "{{ filename }}",
  "http://malsup.github.io/min/jquery.form.min.js": "{{ filename }}",
  "https://raw.github.com/ccampbell/mousetrap/1.4.6/mousetrap.min.js": "{{ filename }}",
  "https://github.com/ajaxorg/ace-builds/archive/v1.1.3.zip":
  {
    ".*/src-min/(?!snippets/)(?P<filename>.+\\.js)": "ace/{{ filename }}"
  }
}