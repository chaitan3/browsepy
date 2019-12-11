#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import os.path
import argparse
import flask

from . import app, compat
from .compat import PY_LEGACY


class ArgParse(argparse.ArgumentParser):
    default_directory = os.path.abspath(compat.getcwd())
    default_host = os.getenv('BROWSEPY_HOST', '127.0.0.1')
    default_port = os.getenv('BROWSEPY_PORT', '8080')

    description = 'extendable web file browser'

    def __init__(self):
        super(ArgParse, self).__init__(description=self.description)

        self.add_argument(
            'host', nargs='?',
            default=self.default_host,
            help='address to listen (default: %(default)s)')
        self.add_argument(
            'port', nargs='?', type=int,
            default=self.default_port,
            help='port to listen (default: %(default)s)')
        self.add_argument(
            '--directory', metavar='PATH', type=self._directory,
            default=self.default_directory,
            help='base serving directory (default: current path)')
        self.add_argument(
            '--initial', metavar='PATH', type=self._directory,
            help='initial directory (default: same as --directory)')
        self.add_argument(
            '--removable', metavar='PATH', type=self._directory,
            default=None,
            help='base directory for remove (default: none)')
        self.add_argument(
            '--upload', metavar='PATH', type=self._directory,
            default=None,
            help='base directory for upload (default: none)')
        self.add_argument(
            '--plugin', metavar='PLUGIN_LIST', type=self._plugin,
            default=[],
            help='comma-separated list of plugins')
        self.add_argument('--debug', action='store_true', help='debug mode')
        self.add_argument('--certfile', type=str, default='')
        self.add_argument('--keyfile', type=str, default='')
        self.add_argument('--passwd', type=str, default='')

    def _plugin(self, arg):
        return arg.split(',') if arg else []

    def _directory(self, arg):
        if not arg:
            return None
        if PY_LEGACY and hasattr(sys.stdin, 'encoding'):
            encoding = sys.stdin.encoding or sys.getdefaultencoding()
            arg = arg.decode(encoding)
        if os.path.isdir(arg):
            return os.path.abspath(arg)
        self.error('%s is not a valid directory' % arg)

class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the 
    front-end server to add these headers, to let you quietly bind 
    this to a URL other than / and to an HTTP scheme that is 
    different than what is used locally.

    In nginx:
    location /myprefix {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    :param app: the WSGI application
    '''
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)

def main(argv=sys.argv[1:], app=app, parser=ArgParse, run_fnc=flask.Flask.run):
    plugin_manager = app.extensions['plugin_manager']
    args = plugin_manager.load_arguments(argv, parser())
    os.environ['DEBUG'] = 'true' if args.debug else ''
    if len(passwd) > 0:
        passwd = args.passwd.split(':')
    else:
        passwd = ''
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.config.update(
        directory_base=args.directory,
        directory_start=args.initial or args.directory,
        directory_remove=args.removable,
        directory_upload=args.upload,
        plugin_modules=args.plugin,
        passwd=passwd
        )
    plugin_manager.reload()
    context=(args.certfile, args.keyfile)
    run_fnc(
        app,
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=False,
        #ssl_context=context,
        threaded=True
        )


if __name__ == '__main__':
    main()
