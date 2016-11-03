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


if sys.version_info[:3] < (3, 4):
    print('Error) 파이썬3로 실행해주세요.', file=sys.stderr)
    sys.exit(1)


def speak(message):
    os.system('say -v Yuna "{0}" || say "{0}"'.format(message))


def red(message, **kwargs):
    kwargs.setdefault('file', sys.stderr)
    print(Fore.RED, end='', **kwargs)
    print(message, **kwargs)
    print(Style.RESET_ALL, end='', **kwargs)


def green(message, **kwargs):
    print(Fore.GREEN, end='', **kwargs)
    print(message, **kwargs)
    print(Style.RESET_ALL, end='', **kwargs)


def blue(message, **kwargs):
    print(Fore.BLUE, end='', **kwargs)
    print(message, **kwargs)
    print(Style.RESET_ALL, end='', **kwargs)


def write_fn(self, data):
    write_timeout = 3000
    self.write_dev.write(data, write_timeout)

USB = backend_factory('pyusb')['backend_class']
setattr(USB, '_write', write_fn)


class NameTag(object):
    PRINTER_ID = 'usb://0x04f9:0x2042'

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
            if 'message' in response_data:
                print(response_data['message'])
            else:
                print('.', end='')
            sys.stdout.flush()

    def test(self):
        try:
            usb = USB(self.PRINTER_ID)
        except ValueError as e:
            red('프린터 연결 및 전원을 확인해주세요.')
            speak('프린터 연결 및 전원을 확인해주세요.')
            sys.exit(1)

    def print(self, data):
        try:
            usb = USB(self.PRINTER_ID)
        except ValueError as e:
            red('프린터 연결 및 전원을 확인해주세요.')
            speak('프린터 연결 및 전원을 확인해주세요.')

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
@click.option('--single/--infinite', default=False, prompt='1회 실행여부')
def main(code, single):
    name_tag = NameTag(code)
    green('Your Mac Address is "{}"'.format(name_tag.mac_address))

    try:
        name_tag.test()

        while True:
            name_tag()
            if single:
                break
            sleep(1.0)
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == '__main__':
    init()
    main()

