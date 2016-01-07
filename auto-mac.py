#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import time
import requests
from random import choice
from string import digits, ascii_lowercase
from datetime import datetime
import json
if sys.platform == 'win32': import ctypes

#colorful output
from colorama import init
init()
from colorama import Fore, Back, Style

from spoofmac.util import random_mac_address, MAC_ADDRESS_R, normalize_mac_address

from spoofmac.interface import (
    wireless_port_names,
    find_interfaces,
    find_interface,
    set_interface_mac,
    get_os_spoofer
)



# Return Codes
SUCCESS = 0
INVALID_ARGS = 1001
UNSUPPORTED_PLATFORM = 1002
INVALID_TARGET = 1003
INVALID_MAC_ADDR = 1004
NON_ROOT_USER = 1005


import urllib2
def internet_on():
    try:
        _ = requests.get("https://baidu.com", timeout=3)
        return True
    except requests.ConnectionError:
        print("No internet connection available.")
    return False

def list_interfaces():
    try:
        spoofer = get_os_spoofer()
    except NotImplementedError:
        return UNSUPPORTED_PLATFORM

    print (Fore.GREEN +'\n*********************\n')
    for port, device, address, current_address in spoofer.find_interfaces():
        line = []
        line.append('- "{port}"'.format(port=port))
        line.append('on device "{device}"'.format(device=device))
        if address:
            line.append('with MAC address {mac}'.format(mac=address))
        if current_address and address != current_address:
            line.append('currently set to {mac}'.format(mac=current_address))
        print( ' '.join(line))

    print '\n*********************\n'
    print(Style.RESET_ALL)
def check_root_or_admin():
    try:
        root_or_admin = os.geteuid() == 0
    except AttributeError:
        root_or_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    if not root_or_admin:
        if sys.platform == 'win32':
            print(Fore.RED + 'Error: Must run this with administrative privileges to set MAC addresses')
            return False
        else:
            print(Fore.RED + 'Error: Must run this as root (or with sudo) to set MAC addresses')
            return False
    return True

def try_once(target):
    result = find_interface(target)
    if result is None:
        print('- couldn\'t find the device for {target}'.format(
            target=target
        ))
        sys.exit(INVALID_TARGET)

    port, device, address, current_address = result

    target_mac = random_mac_address()
    while not MAC_ADDRESS_R.match(target_mac):
        print('- {mac} is not a valid MAC address'.format(
            mac=target_mac
        ))
        target_mac = random_mac_address()

    set_interface_mac(device, target_mac, port)
    print Fore.BLUE + 'Seting MAC address for device ' + device + '...'
    time.sleep(10)
#    while not internet_on():
        #time.sleep(2)
    print Fore.GREEN + 'Done'
    print Fore.CYAN + 'Previous MAC address:\t', address
    print Fore.GREEN +'Current MAC address:\t', target_mac
    raw_input(Fore.CYAN + 'Manually reconnect the wifi and press any key to continue.\t')
    print(Style.RESET_ALL)
    return try_network(target_mac)

# href="https://xfinity.nnu.com/xfinitywifi/?client-mac=48:d7:05:c1:8d:8b"
def try_network(mac_addr):
    # get cookies
    get_url = 'https://xfinity.nnu.com/xfinitywifi/?client-mac=' + mac_addr
    r = requests.get(get_url)
    cookies = r.cookies.get_dict()
    cookies['planid'] = "spn"

    #post data
    #https://xfinity.nnu.com/xfinitywifi/signup/validate
    spn_postal = ''.join(choice(digits) for i in range(5))
    expmm = '%02d' % datetime.now().month
    expyy = str(datetime.now().year % 100 )
    spn_email = ''.join(choice(ascii_lowercase) for i in range(5)) + "%40" + \
                ''.join(choice(ascii_lowercase) for i in range(3)) + \
                '.' + \
                ''.join(choice(ascii_lowercase) for i in range(3))
    post_data = "rateplanid=spn&spn_postal="+spn_postal+"&spn_email="+spn_email+"&spn_terms=1&username=&password1=&password2=&firstname=&lastname=&email=&cardnumber=&ccv=&expmm="+expmm+"&expyy="+expyy+"&billcountry=&billstate=&billpostal="
    post_url = 'https://xfinity.nnu.com/xfinitywifi/signup/validate'
    try:
        r = requests.post(post_url, data = post_data, cookies = cookies)
    except requests.ConnectionError, e:
        print Fore.RED,e
        print(Style.RESET_ALL)
        return False

    #print "validate response:\n", r.text

    #sign up
    # https://xfinity.nnu.com/xfinitywifi/signup?loginid=1452042007
    login_id = int(time.time())
    login_url = 'https://xfinity.nnu.com/xfinitywifi/signup?loginid='+str(login_id)
    try:
        r = requests.get(login_url,
                    cookies = cookies
                     )
    except requests.ConnectionError, e:
        print Fore.RED,e
        print(Style.RESET_ALL)
        return False

    json_data = json.loads(r.text)
    while not json_data['status'] == "done":
        try:
            r = requests.get(login_url, cookies = cookies)
        except requests.ConnectionError, e:
            print Fore.RED,e
            print(Style.RESET_ALL)
            return False
        json_data = json.loads(r.text)

    if json_data["response"] and json_data["response"]["success"] and json_data["response"]["success"] == 1:
        print Fore.GREEN+"Login successfully!\nThe MAC address will automaticlly changed in next hour."
        print(Style.RESET_ALL)
        return True
    return False

def main():
    # list all interface
    list_interfaces()
    target = raw_input("Please input the device name which you want to modify the MAC address :\t")
    print '\n'

    while True:
        try:
            while not try_once(target):
                print Fore.RED+"retrying"
                print(Style.RESET_ALL)
                time.sleep(1)
            #time.sleep(60*60-10)
            time.sleep(30)
        except KeyboardInterrupt:
            print Back.CYAN + Fore.WHITE + "\n------------Bye~."
            print(Style.RESET_ALL)
            sys.exit(0)


if __name__ == '__main__':
    if not check_root_or_admin():
        sys.exit(0)

    sys.exit(main())
