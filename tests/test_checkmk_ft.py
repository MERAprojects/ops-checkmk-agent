#
# !/usr/bin/python
#
# Copyright (C) 2015 Hewlett Packard Enterprise Development LP
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import sys
import time
import pytest
import subprocess
import time
import re
from halonvsi.docker import *
from halonvsi.halon import *
from halonutils.halonutil import *
from omd import *

NUM_OF_SWITCHES = 2
NUM_HOSTS_PER_SWITCH = 0

SWITCH = "s1"
OMD_SERVER = "s2"
OMD_IP = "9.0.0.1"
SWITCH_IP = "9.0.0.2"
NETMASK = "24"

class myTopo(Topo):
    def build (self, hsts=0, sws=NUM_OF_SWITCHES, **_opts):

        self.hsts = hsts
        self.sws = sws

        self.addSwitch(SWITCH)
        self.addSwitch(name = OMD_SERVER, cls = OmdSwitch, **self.sopts)
        #self.addLink(SWITCH, OMD_SERVER)

class checkmkTest (HalonTest):
    def setupNet (self):
        self.net = Mininet(topo=myTopo(hsts = NUM_HOSTS_PER_SWITCH,
                                       sws = NUM_OF_SWITCHES,
                                       hopts = self.getHostOpts(),
                                       sopts = self.getSwitchOpts()),
                                       switch = HalonSwitch,
                                       host = HalonHost,
                                       link = HalonLink,
                                       controller = None,
                                       build = True)

    def configure (self):
        for switch in self.net.switches:
            if isinstance(switch, HalonSwitch):
                switch.cmd("systemctl enable checkmk-agent.socket")
                switch.cmd("systemctl restart sockets.target")
                switch.cmdCLI("configure terminal")
                switch.cmdCLI("interface 1")
                switch.cmdCLI("no shutdown")
                switch.cmdCLI("ip address %s/%s" % (SWITCH_IP, NETMASK)),
                switch.cmdCLI("exit")

    def checkmk_getIPs (self):
        for switch in self.net.switches:
            result = switch.cmd("ifconfig eth0")
            ipAddrs = re.findall(r'[0-9]+(?:\.[0-9]+){3}', result)
            for ipAddr in ipAddrs:
                if ipAddr != '0.0.0.0' and not re.match("255", ipAddr):
                    break
            if isinstance(switch, HalonSwitch):
                self.switchIpAddr = ipAddr
            elif isinstance(switch, OmdSwitch):
                self.omdIpAddr = ipAddr

        print "Switch Mgmt IP is %s, OMD Server IP is %s" % (self.switchIpAddr, self.omdIpAddr)

    def checkmk_addHost(self):
        for switch in self.net.switches:
            if isinstance(switch, OmdSwitch):
                args = ['curl', """-d 'request={"hostname": "%s", "folder": "os/linux"}'""" % self.switchIpAddr, """\"http://127.0.0.1/default/check_mk/webapi.py?action=add_host&_username=auto&_secret=secretpassword\""""]
                result = switch.cmd(args)
                print result

    def checkmk_discoverHost(self):
        for switch in self.net.switches:
            if isinstance(switch, OmdSwitch):
                args = ['curl', """-d 'request={"hostname": "%s"}'""" % self.switchIpAddr, """\"http://127.0.0.1/default/check_mk/webapi.py?action=discover_services&_username=auto&_secret=secretpassword&mode=refresh\""""]
                result = switch.cmd(args)
                print result

    def checkmk_activateHost(self):
        for switch in self.net.switches:
            if isinstance(switch, OmdSwitch):
                args = ['curl', """\"http://127.0.0.1/default/check_mk/webapi.py?action=activate_changes&_username=auto&_secret=secretpassword&mode=all\""""]
                result = switch.cmd(args)

class Test_checkmk_basic_setup:
    def setup (self):
        pass

    def teardown (self):
        pass

    def setup_class (cls):
        Test_checkmk_basic_setup.test_var = checkmkTest()

    def teardown_class (cls):
        Test_checkmk_basic_setup.test_var.net.stop()

    def setup_method (self, method):
        pass

    def teardown_method (self, method):
        pass

    def __del__ (self):
        del self.test_var

    def test_run (self):
        self.test_var.configure()
        self.test_var.checkmk_getIPs()
        self.test_var.checkmk_addHost()
        CLI(self.test_var.net)
        self.test_var.checkmk_discoverHost()
        CLI(self.test_var.net)
        self.test_var.checkmk_activateHost()
        CLI(self.test_var.net)
