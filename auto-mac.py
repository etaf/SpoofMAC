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
COLOR_INFO = Fore.WHITE
COLOR_ERROR = Fore.RED
COLOR_SUCCESS = Fore.BLUE

from spoofmac.util import random_mac_address, MAC_ADDRESS_R
from spoofmac.interface import (
    wireless_port_names,
    find_interfaces,
    find_interface,
    set_interface_mac,
    get_os_spoofer,
    reconnect_wifi
)




# Return Codes
SUCCESS = 0
INVALID_ARGS = 1001
UNSUPPORTED_PLATFORM = 1002
INVALID_TARGET = 1003
INVALID_MAC_ADDR = 1004
NON_ROOT_USER = 1005


def internet_on():
    try:
        _ = requests.get("https://google.com", timeout=3)
        return True
    except requests.ConnectionError:
        print(COLOR_ERROR + "No internet access")
    return False

def list_interfaces():
    try:
        spoofer = get_os_spoofer()
    except NotImplementedError:
        return UNSUPPORTED_PLATFORM

    print '{0:^80}'.format(COLOR_INFO +'****** list of your network interfaces ******')
    for port, device, address, current_address in spoofer.find_interfaces():
        line = []
        line.append('- "{port}"'.format(port=port))
        line.append('on device "{device}"'.format(device=device))
        if address:
            line.append('with MAC address {mac}'.format(mac=address))
        if current_address and address != current_address:
            line.append('currently set to {mac}'.format(mac=current_address))
        print('{0:80}'.format( ' '.join(line)))

    print '{0:^80}'.format(COLOR_INFO + '***************** end list *****************')

def check_root_or_admin():
    try:
        root_or_admin = os.geteuid() == 0
    except AttributeError:
        root_or_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    if not root_or_admin:
        if sys.platform == 'win32':
            print('{0:80}'.format(COLOR_ERROR + 'Error: Must run this with administrative privileges to set MAC addresses'))
            return False
        else:
            print('{0:80}'.format(COLOR_ERROR + 'Error: Must run this as root (or with sudo) to set MAC addresses'))

            return False
    return True

def try_once(target, wifi_name):

    result = find_interface(target)
    if result is None:
        print(COLOR_ERROR + '- couldn\'t find the device for {target}'.format(target=target))
        sys.exit(INVALID_TARGET)

    port, device, address, current_address = result

    # generate new mac address
    target_mac = random_mac_address()
    while not MAC_ADDRESS_R.match(target_mac):
        print(COLOR_ERROR + '- {mac} is not a valid MAC address'.format(
            mac=target_mac
        ))
        target_mac = random_mac_address()

    # set mac address
    print '{0:80}'.format(COLOR_INFO + 'Seting MAC address for device ' + device + '...' )
    set_interface_mac(device, target_mac, port)
    time.sleep(3)
    print '{0:80}'.format(COLOR_INFO + "Done.")

    # reconnect wifi
    print '{0:80}'.format(Fore.WHITE + 'Reconnecting wifi..')
    wait_second = 3
    while not reconnect_wifi(device, wifi_name):
        print '{0:80}'.format(COLOR_ERROR + 'Faild, Auto reconnect after {} ...'.format(wait_second) )
        time.sleep(wait_second)
        wait_second += wait_second
    time.sleep(5)
    print '{0:80}'.format(COLOR_INFO + "Done.")

    # test network
    print '{0:80}'.format(Fore.WHITE + "Testing network access...")
    wait_second = 3
    while not internet_on():
        time.sleep(wait_second)
        wait_second += wait_second
    print '{0:80}'.format(COLOR_INFO + 'Done.')

    #print Fore.CYAN + 'Previous MAC address:\t', address
    #print Fore.GREEN +'Current MAC address:\t', target_mac
    # raw_input(Fore.CYAN + 'Manually reconnect the wifi and press any key to continue.\t')
    print '{0:80}'.format(Fore.WHITE + "Try login in .....")
    try_times = 3
    for i in xrange(try_times):
        if try_network(target_mac):
            return True
        print '{0:80}'.format(COLOR_ERROR + "Failed, Auto try again...")
    return False

# href="https://xfinity.nnu.com/xfinitywifi/?client-mac=48:d7:05:c1:8d:8b"
def try_network(mac_addr):
    # get cookies
    get_url = 'https://xfinity.nnu.com/xfinitywifi/?client-mac=' + mac_addr
    try:
        r = requests.get(get_url)
    except requests.ConnectionError, e:
        print COLOR_ERROR,e
        #print(Style.RESET_ALL)
        return False

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
        print COLOR_ERROR,e
        print(Style.RESET_ALL)
        return False

    #print "validate response:\n", r.text

    #sign up
    # https://xfinity.nnu.com/xfinitywifi/signup?loginid=1452042007
    time.sleep(1)
    login_id = int(time.time())
    login_url = 'https://xfinity.nnu.com/xfinitywifi/signup?loginid='+str(login_id)
    try:
        r = requests.get(login_url,
                    cookies = cookies
                     )
    except requests.ConnectionError, e:
        print COLOR_ERROR,e
        print(Style.RESET_ALL)
        return False

    json_data = json.loads(r.text)
    while not json_data['status'] == "done":
        print '{0:80}'.format(COLOR_ERROR + "Pending ...")
        #print(Style.RESET_ALL)
        try:
            r = requests.get(login_url, cookies = cookies)
        except requests.ConnectionError, e:
            print COLOR_ERROR ,e
            #print(Style.RESET_ALL)
            return False
        json_data = json.loads(r.text)

    if json_data["response"] and json_data["response"]["success"] and json_data["response"]["success"] == 1:
        print '{0:80}'.format(COLOR_INFO+"Login successfully!")
        print '{0:80}'.format(COLOR_INFO+"The MAC address will automaticlly changed in next hour.")
        print(Style.RESET_ALL)
        return True
    return False

def main():

    print Back.GREEN
    # list all interface
    list_interfaces()

    # get target device
    target = raw_input(Fore.WHITE + "Please input the device name which you want to modify the MAC address :\t")

    wifi_name = "xfinity"

    # login every hour.
    while True:
        try:
            while not try_once(target, wifi_name):
                print '{0:80}'.format(COLOR_ERROR + "Retrying after 3 seconds....")
                #print(Style.RESET_ALL)
                time.sleep(3)
            time.sleep(60*60-10)
        except KeyboardInterrupt:
            print '{0:80}'.format(Back.BLUE + Fore.WHITE + "------------Bye-------------")
            print(Style.RESET_ALL)
            sys.exit(0)

    print(Style.RESET_ALL)
    sys.exit(0)

if __name__ == '__main__':
    if not check_root_or_admin():
        sys.exit(0)

    sys.exit(main())
