# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import click
import json
import os
import sys
import requests
from time import sleep
from uuid import getnode
from brother_ql.backends import backend_factory
from brother_ql.reader import interpret_response
from colorama import init, Fore, Back, Style
from usb.core import USBError


def speak(message):
    os.system('say -v Yuna "{0}" || say "{0}"'.format(message))


def red(message, **kwargs):
    kwargs.setdefault('file', sys.stderr)
    print(Fore.RED, end='')
    print(message, **kwargs)
    print(Style.RESET_ALL, end='')
    sys.stdout.flush()


def green(message, **kwargs):
    print(Fore.GREEN, end='')
    print(message, **kwargs)
    print(Style.RESET_ALL, end='')
    sys.stdout.flush()


def blue(message, **kwargs):
    print(Fore.BLUE, end='')
    print(message, **kwargs)
    print(Style.RESET_ALL, end='')
    sys.stdout.flush()


def write_fn(self, data):
    write_timeout = 3000
    self.write_dev.write(data, write_timeout)

USB = backend_factory('pyusb')['backend_class']
setattr(USB, '_write', write_fn)


class NameTag(object):
    def __init__(self, code):
        self.mac_address = '%02X' % getnode()
        self.code = code

    def status_404(self, response):
        red('잘못된 이벤트 코드 ({}) 입니다.'.format(self.code))
        sys.exit(1)

    def status_401(self, response):
        red('허용되지 않은 접근입니다. Festi 관리자에게 {}를 알려주세요.'.format(self.mac_address))
        sys.exit(1)

    def status_500(self, response):
        red('서버오류가 발생했습니다.')

    def status_200(self, response):
        data = response.content

        try:
            response_data = json.loads(data.decode('utf8'))
        except (UnicodeDecodeError, ValueError):
            self.print(data)
        else:
            # response_data
            print('.', end='')
            sys.stdout.flush()

    def print(self, data):
        try:
            usb = USB('usb://0x04f9:0x2042')
        except ValueError:
            red('프린터 연결을 확인해주세요.')
            speak('프린터 연결을 확인해주세요.')
            sys.exit(1)

        try:
            try:
                usb.write(data)
            except USBError as e:
                red(e)

            readed = usb.read()
            try:
                result = interpret_response(readed)
            except Exception as e:
                red(e)
                speak(e)
            else:
                errors = result['errors']
                if errors:
                    error_message = '\n'.join(errors)
                    red(error_message)  # TODO: 에러 메세지 노출
                    speak('오류 메세지를 확인해주세요.')
                else:
                    green('.')
        finally:
            usb.dispose()
            del usb

    def status_not_defined(self, response):
        red('정의되지 않은 응답코드 {}입니다.'.format(response.status_code))

    def __call__(self):
        headers = {'X-Mac-Address': self.mac_address}
        url = 'https://festi.kr/festi/{}/print/'.format(self.code)
        r = requests.get(url, headers=headers)

        fn_name = 'status_{}'.format(r.status_code)
        fn = getattr(self, fn_name, None)
        if callable(fn):
            fn(r)
        else:
            self.status_not_defined(r)


@click.command()
@click.option('--code', prompt='이벤트 코드', help='이벤트 코드를 지정')
def main(code):
    name_tag = NameTag(code)
    green('Your Mac Address is "{}"'.format(name_tag.mac_address))

    try:
        while True:
            name_tag()
            sleep(0.5)
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == '__main__':
    init()
    main()

