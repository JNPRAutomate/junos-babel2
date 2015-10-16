#! /usr/bin/env python

import ansible.inventory
import ansible.inventory.ini
import argparse
from jinja2 import Template
from babel2 import device
from babel2 import parsingerror
import babel2.lib
import pprint
import yaml
import logging
from subprocess import call
from os import path
import os

'''
Usage:

python babel2.py  --push <conf_type> --log LEVEL

TODO: Complete description
'''

parser = argparse.ArgumentParser(description='Process user input')
parser.add_argument("--push", dest="push_conf", metavar="CONF_TYPE",
                    choices=['mclag', 'jfd'],
                    help="Indicate if you want to push the configuration to all devices")
parser.add_argument("--log", dest="log", metavar="LEVEL", default='info',
                    choices=['info', 'warn', 'debug', 'error'],
                    help="Specify the log level ")
args = parser.parse_args()

here = path.abspath(path.dirname(__file__))
parsingError = parsingerror.ParsingError()
pp = pprint.PrettyPrinter(indent=4)

############################################
### Variables initialization
#############################################
devices = {}
group_vars = {}
host_vars = {}
groups_name = []
nbr_access_grp = 0
fpc_id = 100

HOSTS_FILE = 'input/hosts'
CONFIG_FILE = 'input/configuration.yaml'
TOPO_FILE = 'input/topology.yaml'

PB_MCLAG_GEN = 'mclag.all.p.yaml'
PB_MCLAG_PUSH = 'mclag.all.commit.p.yaml'
PB_JFD_GEN = 'jfd.all.p.yaml'
PB_JFD_PUSH = 'jfd.all.commit.p.yaml'

############################################
### Log level configuration
#############################################
logger = logging.getLogger( 'babel2' )

if args.log == 'debug':
    logger.setLevel(logging.DEBUG)
elif args.log == 'warn':
    logger.setLevel(logging.WARN)
elif args.log == 'error':
    logger.setLevel(logging.ERROR)
else:
    logger.setLevel(logging.INFO)

logging.basicConfig(format=' %(name)s - %(levelname)s - %(message)s')

############################################
### Open main input files
#############################################
## Access the hosts file from Ansible and check its conformity
inventory = ansible.inventory.ini.InventoryParser(HOSTS_FILE)
hosts = inventory.hosts
groups = inventory.groups

logger.info('Checking Inventory file')
babel2.lib.check_hosts_file(hosts, groups, parsingError)

parsingError.exit_on_error()

## Find devices and classify them
aggregations = groups['aggregation'].get_hosts()
groups_name.append('aggregation')

## Create both Aggregation devices
agg1 = aggregations[0].name
agg2 = aggregations[1].name
agg1dev = device.Device(agg1)
agg2dev = device.Device(agg2)
agg1dev.set_as_aggregation()
agg2dev.set_as_aggregation()
agg2dev.set_peer(agg1dev)
agg1dev.set_peer(agg2dev)

## Add devices to the dict for storage
devices[agg1] = agg1dev
devices[agg2] = agg2dev

## Create access devices
access_groups = groups['access'].child_groups

for access_group in access_groups:
    nbr_access_grp += 1
    groups_name.append(access_group.name)

    access_devices = access_group.get_hosts()
    acc1 = access_devices[0].name
    acc2 = access_devices[1].name
    acc1dev = device.Device(acc1)
    acc2dev = device.Device(acc2)
    acc1dev.set_as_access(access_group.name)
    acc2dev.set_as_access(access_group.name)
    acc1dev.set_fpc_id(fpc_id)
    acc2dev.set_fpc_id(fpc_id + 1)
    acc2dev.set_peer(acc1dev)
    acc1dev.set_peer(acc2dev)
    devices[acc1] = acc1dev
    devices[acc2] = acc2dev

    fpc_id += 2

## Access the topology file
## Parse it and chech that all devices are present in the inventory
topology_file = open(TOPO_FILE)

# Render the file as a jinja2 template
topo_tpl = Template(topology_file.read())
topo_tpl_rdr = topo_tpl.render()

topology = yaml.load(topo_tpl_rdr)
logger.info('Checking Topology file')
babel2.lib.check_topology_file(topology, hosts, parsingError)
babel2.lib.assign_interfaces_to_devices(topology, devices)

## Access the configuration definition file
conf_file = open(CONFIG_FILE)

# Render the file as a jinja2 template
config_tpl = Template(conf_file.read())
config_tpl_rdr = config_tpl.render()

config = yaml.load(config_tpl_rdr)
logger.info('Checking Configuration file')
babel2.lib.check_config_file(config, topology, parsingError)

## If some error, exit and print
parsingError.exit_on_error()

#########################################
## Clean Up existing file in group_vars and host_vars
########################################
logger.info('Cleaning Up Old generated file')
for name, device in devices.iteritems():
    mydir = path.join(here, 'host_vars', name)
    myfile = path.join(mydir, config['global']['gen_file_name'])

    if not path.exists(mydir):
        os.mkdir(mydir)
    elif not path.isdir(mydir):
        raise RuntimeError("{0} is not a directory, please fix")

    if path.exists(myfile):
        logger.debug('File {0} found and deleted'.format(myfile))
        os.remove(myfile)

for group in groups_name:
    mydir = path.join(here, 'group_vars', group)
    myfile = path.join(mydir, config['global']['gen_file_name'])
    if not path.exists(mydir):
        os.mkdir(mydir)
    elif not path.isdir(mydir):
        raise RuntimeError("{0} is not a directory, please fix".format(mydir))

    if path.exists(myfile):
        logger.debug('File {0} found and deleted'.format(myfile))
        os.remove(myfile)

##########################################
## Expand Vlans
##########################################
# Go over vlans
# assign Ip addresses for gateway and for all aggs devices
babel2.lib.expland_vlans(config)

##########################################
## Generate variables file for MC-LAG
##########################################

## Create this array with values for both peers, will be use later to generate config for a pair of devices
mclag_cluster_param = []
mclag_cluster_param.append({'chassis_id': 0, 'status_control': 'active', 'local_ip': '1.1.1.1', 'peer_ip': '1.1.1.2'})
mclag_cluster_param.append({'chassis_id': 1, 'status_control': 'standby', 'local_ip': '1.1.1.2', 'peer_ip': '1.1.1.1'})

# Need to generate mac address for all groups
mymac = babel2.lib.generate_mac_address(nbr_access_grp + 1, '00:11:22:33:33')

### Generate variable for aggregation devices
# - first group_vars
# - then host

group_vars['aggregation'] = {}
group_vars['aggregation']['mclag_shared'] = {}
group_vars['aggregation']['mclag_shared']['iccp'] = {}
group_vars['aggregation']['mclag_shared']['mac'] = mymac.pop(0)
group_vars['aggregation']['mclag_shared']['mode'] = config['global']['mc_lag_mode']
group_vars['aggregation']['mclag_shared']['iccp']['vlan_name'] = config['global']['iccp_vlan_name']
group_vars['aggregation']['mclag_shared']['iccp']['vlan_id'] = config['global']['iccp_vlan_id']

## Generate Variables for Aggregation devices ##
for i in range(0, 2):
    dev_name = aggregations[i].name

    host_vars[dev_name] = {}
    host_vars[dev_name]['vlans'] = []
    host_vars[dev_name]['mclag'] = {}
    host_vars[dev_name]['mclag']['links'] = {}
    host_vars[dev_name]['mclag']['links']['to_access'] = []
    host_vars[dev_name]['mclag']['iccp'] = {}
    host_vars[dev_name]['mclag']['chassis_id'] = mclag_cluster_param[i]['chassis_id']
    host_vars[dev_name]['mclag']['status_control'] = mclag_cluster_param[i]['status_control']
    host_vars[dev_name]['mclag']['iccp']['local_ip'] = mclag_cluster_param[i]['local_ip']
    host_vars[dev_name]['mclag']['iccp']['peer_ip'] = mclag_cluster_param[i]['peer_ip']
    host_vars[dev_name]['mclag']['icl_interface'] = config['global']['icl_interface']

    ## Create vlans for aggre and assigne VIP and addr
    for name, vlan in config['vlans'].iteritems():
        tmp_vlan = {}
        tmp_vlan['name'] = name
        tmp_vlan['id'] = vlan['id']
        tmp_vlan['ip'] = vlan['router_ips'][i]
        tmp_vlan['mask'] = vlan['mask']
        tmp_vlan['vip'] = vlan['vip']

        # Get peer links info
        host_vars[dev_name]['vlans'].append(tmp_vlan)
        host_vars[dev_name]['mclag']['links']['to_peer'] = devices[dev_name].get_peer_links()

### Generate Variables for Access devices ##
# - first group_vars
# - then host

grp_id = 1
for access_group in access_groups:
    name = access_group.name
    access_devices = access_group.get_hosts()
    group_vars[name] = {}
    group_vars[name]['mclag_shared'] = {}
    group_vars[name]['mclag_shared']['iccp'] = {}
    group_vars[name]['mclag_shared']['mac'] = mymac.pop(0)
    group_vars[name]['mclag_shared']['mode'] = config['global']['mc_lag_mode']
    group_vars[name]['mclag_shared']['iccp']['vlan_name'] = config['global']['iccp_vlan_name']
    group_vars[name]['mclag_shared']['iccp']['vlan_id'] = config['global']['iccp_vlan_id']

    ## Populate to_access info for aggregation devices
    for i in range(0, 2):
        agg_name = aggregations[i].name
        links = devices[agg_name].get_access_links(name)
        tmp = {'key': grp_id, 'links': links, 'description': "to_{0}".format(name) }
        logger.debug('Agg device {0} will add link for access'.format(agg_name))
        host_vars[agg_name]['mclag']['links']['to_access'].append(tmp)

    ## For both devices in the group
    for i in range(0, 2):
        dev_name = access_devices[i].name

        host_vars[dev_name] = {}
        host_vars[dev_name]['vlans'] = []
        host_vars[dev_name]['mclag'] = {}
        host_vars[dev_name]['mclag']['links'] = {}
        host_vars[dev_name]['mclag']['iccp'] = {}
        host_vars[dev_name]['mclag']['chassis_id'] = mclag_cluster_param[i]['chassis_id']
        host_vars[dev_name]['mclag']['status_control'] = mclag_cluster_param[i]['status_control']
        host_vars[dev_name]['mclag']['iccp']['local_ip'] = mclag_cluster_param[i]['local_ip']
        host_vars[dev_name]['mclag']['iccp']['peer_ip'] = mclag_cluster_param[i]['peer_ip']
        host_vars[dev_name]['mclag']['icl_interface'] = config['global']['icl_interface']

        for name, vlan in config['vlans'].iteritems():
            tmp_vlan = {}
            tmp_vlan['name'] = name
            tmp_vlan['id'] = vlan['id']
            host_vars[dev_name]['vlans'].append(tmp_vlan)

        # Get peer & Aggregation links info
        host_vars[dev_name]['mclag']['links']['to_servers'] = []
        host_vars[dev_name]['mclag']['links']['to_peer'] = devices[dev_name].get_peer_links()
        host_vars[dev_name]['mclag']['links']['to_aggregation'] = devices[dev_name].get_aggregation_links()

    seg_key = 2
    for seg, srv_links in topology['external_links'].iteritems():
        do_have = 0
        for i in range(0, 2):
            dev_name = access_devices[i].name
            links = devices[dev_name].get_servers_links(seg)
            if not len(links) == 0:
                do_have = 1
                tmp = {'key': seg_key, 'links': links, 'description': seg, 'vlans':[]}

                for vlan_name, vlan in config['vlans'].iteritems():
                    for link in vlan['links']:
                        for key, value in link.iteritems():
                            if key == seg:
                                tmp['vlans'].append(vlan['id'])

                host_vars[dev_name]['mclag']['links']['to_servers'].append(tmp)

        if do_have == 1:
            seg_key += 1

    grp_id += 1

    ## Count the number of AE per Access device
    for i in range(0, 2):
        dev_name = access_devices[i].name
        nbr_ae = len(host_vars[dev_name]['mclag']['links']['to_servers']) + 2
        host_vars[dev_name]['mclag']['nbr_ae'] = nbr_ae

## Count the number of AE per aggregation device
for i in range(0, 2):
    agg_name = aggregations[i].name
    nbr_ae = len(host_vars[agg_name]['mclag']['links']['to_access']) + 2
    host_vars[agg_name]['mclag']['nbr_ae'] = nbr_ae

##########################################
## Generate variables file for JFD    ####
##########################################

jfd_cluster_param = []
jfd_cluster_param.append({'chassis_id': 1, 'peer_chassis_id': 2, 'peer_ip': '1.1.1.2', 'peer_name': aggregations[1].name})
jfd_cluster_param.append({'chassis_id': 2, 'peer_chassis_id': 1, 'peer_ip': '1.1.1.1', 'peer_name': aggregations[0].name})

## Generate Variables for Aggregation devices ##
for i in range(0, 2):
    agg_name = aggregations[i].name
    logger.debug('JFD - Starting {0}'.format(agg_name))

    if not host_vars[dev_name]:
        host_vars[agg_name] = {}
        host_vars[agg_name]['vlans'] = []

    ## Init host_vars dict
    host_vars[agg_name]['jfd'] = {}
    host_vars[agg_name]['jfd']['links'] = {}
    host_vars[agg_name]['jfd']['links']['to_peer'] = []
    host_vars[agg_name]['jfd']['links']['to_servers'] = []
    host_vars[agg_name]['jfd']['links']['to_satellite'] = []

    ## Populate general info
    host_vars[agg_name]['jfd']['chassis_id'] = jfd_cluster_param[i]['chassis_id']
    host_vars[agg_name]['jfd']['peer_chassis_id'] = jfd_cluster_param[i]['peer_chassis_id']
    host_vars[agg_name]['jfd']['peer_ip'] = jfd_cluster_param[i]['peer_ip']
    host_vars[agg_name]['jfd']['peer_name'] = jfd_cluster_param[i]['peer_name']
    host_vars[agg_name]['jfd']['icl_interface'] = config['global']['icl_interface']

    host_vars[agg_name]['jfd']['links']['to_peer'] = devices[dev_name].get_peer_links()

    ## To Generate Satellite and Server ports info, we go over list of access groups
    ## and device per device inside each group
    for access_group in access_groups:
        name = access_group.name
        access_devices = access_group.get_hosts()

        links_to_sd = devices[agg_name].get_access_links_with_dev(name)

        ## For Each device in access group, get list of interface
        for i in range(0, 2):
            sd_name = access_devices[i].name

            tmp = {}
            tmp['id'] = devices[sd_name].get_fpc_id()
            tmp['name'] = sd_name
            tmp['links'] = []

            for link in links_to_sd:
                if link['dev'] == sd_name:
                    tmp['links'].append(link['int'])

            host_vars[agg_name]['jfd']['links']['to_satellite'].append(tmp)

        ## Generate Server port information
        seg_key = 1
        for seg, srv_links in topology['external_links'].iteritems():
            do_have = 0

            tmp = {}
            tmp['description'] = "to {0}".format(seg)
            tmp['links'] = []
            tmp['vlans'] = []
            tmp['key'] = ''

            for i in range(0, 2):
                sd_name = access_devices[i].name
                links = devices[sd_name].get_servers_links(seg)
                fpc_id = devices[sd_name].get_fpc_id()

                ## Get list of links
                if not len(links) == 0:
                    do_have = 1
                    tmp['key'] = seg_key
                    for link in links:
                        ep_port = link.replace('-0/', "-{0}/".format(fpc_id) )
                        tmp['links'].append(ep_port)

            ## Get list of vlans
            for vlan_name, vlan in config['vlans'].iteritems():
                for link in vlan['links']:
                    for key, value in link.iteritems():
                        if key == seg:
                            tmp['vlans'].append(vlan['id'])

            if do_have == 1:
                seg_key += 1
                host_vars[agg_name]['jfd']['links']['to_servers'].append(tmp)

##############################################
## Generate Variable Files
##############################################
logger.info('Generate new variable files ... ')
for name, device in devices.iteritems():
    myfile = path.join(here, 'host_vars', name, config['global']['gen_file_name'])
    with open(myfile, 'w') as f:
        yaml.dump(host_vars[name], f, indent=4, default_flow_style=False)

for group in groups_name:
    myfile = path.join(here, 'group_vars', group, config['global']['gen_file_name'])
    with open(myfile, 'w') as f:
        yaml.dump(group_vars[group], f, indent=4, default_flow_style=False)

# ##############################################
# ## Generate Configuration Files
# ##############################################
#
# logger.info('Generate Configuration files for MCLAG ... ')
# call("ansible-playbook -i {0} {1}".format(HOSTS_FILE, PB_MCLAG_GEN), shell=True)
#
# logger.info('Generate Configuration files for JFD ... ')
# call("ansible-playbook -i {0} {1}".format(HOSTS_FILE, PB_JFD_GEN), shell=True)
