# -*- coding:utf-8 -*-

# Copyright 2015 Cisco Systems, Inc.
# All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
import sys
import urllib2
import json
import random
import time

URL = 'http://{bind_host}:{bind_port}/v1/peer/{peer_ip}/send/update'

class YabgpAgent():
    def __init__(self, server_ip='127.0.0.1', server_port=8801, \
                        user='admin', passwd='admin'):
        self.server_ip = server_ip
        self.server_port = server_port
        self.user = user
        self.passwd = passwd


    def send_update(self, peer_ip, update):
        url = URL.format(bind_host = self.server_ip,
                         bind_port = self.server_port,
                         peer_ip = peer_ip)

        self.__get_data_from_agent(url, self.user, self.passwd, 'POST', update)

    def announce(self, peer_ip, origin=0, prefixes=[],
                                        as_path=[], next_hop=''):
        attr = {}
        attr['1'] = origin # Origin attribute
        attr['2'] = [ [2, as_path] ] # ASPath attribute
        attr['3'] = next_hop

        nlri = prefixes
        withdraw = []

        update = { 'attr': attr, 'nlri': nlri, 'withdraw' : withdraw }
        self.send_update(peer_ip, update)

    def withdraw(self, peer_ip, prefixes=[]):
        attr = {}
        nlri = []
        withdraw = prefixes

        update = { 'attr': attr, 'nlri': nlri, 'withdraw' : withdraw }
        self.send_update(peer_ip, update)

    def __get_api_opener_v1(self, url, username, password):
        """
        get the http api opener with base url and username,password

        :param url: http url
        :param username: username for api auth
        :param password: password for api auth
        """
        # create a password manager
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()

        # Add the username and password.
        password_mgr.add_password(None, url, username, password)

        handler = urllib2.HTTPBasicAuthHandler(password_mgr)
        opener = urllib2.build_opener(handler)
        return opener

    def __get_data_from_agent(self, url, username, password, method='GET', data=None):
        """
        HTTP interaction with yabgp rest api
        :param url:
        :param username:
        :param password:
        :param method:
        :param data:
        :return:
        :return:
        """
        # build request
        if data:
            data = json.dumps(data)
        request = urllib2.Request(url, data)
        request.add_header("Content-Type", 'application/json')
        request.get_method = lambda: method
        opener_v1 = self.__get_api_opener_v1(url, username, password)
        try:
            res = json.loads(opener_v1.open(request).read())
            return res
        except Exception as e:
            print(e)
        return None
