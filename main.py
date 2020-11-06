#!/usr/bin/python
# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod
import os
import requests
import json

from fabric.api import *
from fabric.exceptions import NetworkError


class AbstractActionClass:
    __metaclass__ = ABCMeta

    version = '0.1'

    @abstractmethod
    def __init__(self, name, description):
        self.name = name
        self.description = description

    @abstractmethod
    def save(self):
        # maybe api to db
        pass

    @abstractmethod
    def execute(self):
        # executor of specific action type
        # will have implementation
        pass


class RawAction(AbstractActionClass):

    version = '0.1'

    def __init__(self, name, description, command):
        super(RawAction, self).__init__(name, description)
        self.command = command

    def save(self):
        pass

    def execute(self):

        print "{}".format(self.description)
        result = os.popen(self.command).read()
        return result


class RemoteAction(AbstractActionClass):

    version = '0.1'

    def __init__(self, name, description, ip, user, password, command):
        super(RemoteAction, self).__init__(name, description)

        self.ip = ip
        self.user = user
        self.password = password
        self.command = command

    def save(self):
        pass

    def execute(self):
        env['uts'] = []
        env.use_ssh_config = False
        env.host_string = self.ip
        env.user = self.user
        env.password = self.password
        result = None
        try:
            result = run(self.command)
        except NetworkError:
            print "wrong host specified"
        return result


class ApiAction(AbstractActionClass):

    version = '0.1'

    def __init__(self, name, description, type, url_path, certificate=None, user=None, password=None, input=None):
        super(ApiAction, self).__init__(name, description)

        self.type = type
        self.url_path = url_path
        self.certificate = certificate
        self.user = user
        self.password = password
        self.input = input

    def save(self):
        pass

    def execute(self):
        # prepare for request
        # let's start with urllib with user/password
        headers = {'Accept': 'application/json'}
        r = None
        if self.type == 'GET':
            r = requests.get(self.url_path, auth=(self.user, self.password), headers=headers)
        elif self.type == 'PUT':
            pass
        elif self.type == 'POST':
            payload = self.input
            r = requests.post(self.url_path, auth=(self.user, self.password), data=json.dumps(payload))
        elif self.type == 'DELETE':
            pass
        elif self.type == 'OPTIONS':
            # for options we shall not call Accept json
            r = requests.options(self.url_path, auth=(self.user, self.password))
        else:
            print "unsupported request type"
            return None

        return r.text


def raw_test():
    cmd1 = RawAction('ps', 'getting processes list', 'ps')
    cmd2 = RawAction('hostname', 'getting current machine hostname', 'hostname')
    cmd3 = RawAction('ip', 'getting current machine ips', 'ip r l')
    cmd4 = RawAction('df', 'getting how many space i have', 'df -h')

    cmds = [cmd1, cmd2, cmd3, cmd4]
    for cmd in cmds:
        r = cmd.execute()
    print r


def fab_test():
    cmd = RemoteAction('my host disk space', 'get disk space of my remote PCS', 'xxx', 'root', 'xxx', 'df -h')
    r = cmd.execute()
    print r


def api_test():
    cmd = ApiAction('customers from paci', 'get customers', 'OPTIONS', 'http://10.26.205.169:4465/paci/v1.0/customer', user='admin', password='xxxx')
    r = cmd.execute()
    print r

api_test()
