import logging
import sys
import yaml
from os import path
import defconf

here = path.abspath(path.dirname(__file__))
logger = logging.getLogger( 'babel2' )

# Check if topology file is correct
# All entry have 2 sides with "device interface" for each
def check_topology_file( topology, hosts, parsingError ):

    logger.debug('Checking internal Links')

    definition = yaml.load( open(path.join(here, 'topology.def.yml')) )
    defconf.validate_config( topology, definition, 'topology.def.yml' )

    for link in topology['internal_links']:
        # Check if link size is 2
        if not len(link) == 2:
            parsingError.add("Internal Link: A link has not 2 sides as expected" + str(len(link)) + " instead")
            next

        side1 = link[0].split()
        side2 = link[1].split()

        if not hosts.has_key( side1[0] ):
            parsingError.add("Internal Link: Device " + side1[0]  + " is not part of the inventory file")

        if not hosts.has_key( side2[0] ):
            parsingError.add("Internal Link: Device " + side2[0] + " is not part of the inventory file")

    logger.debug('Checking External Links')
    for name, links in topology['external_links'].iteritems():
        for link in links:
            dev_int = link.split()#
            if not hosts.has_key( dev_int[0] ):
                parsingError.add("External Link: Device " + dev_int[0]  + " is not part of the inventory file")

def check_hosts_file( hosts, groups, parsingError ):

    ## Check if groups access and aggregation exists
    if not groups.has_key('aggregation'):
        parsingError.add("Group aggregation have not been found in file 'hosts'")
        return 0
    if not groups.has_key('access'):
        parsingError.add("Group access have not been found in file 'hosts'")
        return 0

    ## Check if aggregations has 2 hosts, no more no less
    aggregations = groups['aggregation'].get_hosts()

    if len(aggregations) < 2:
        parsingError.add("Less than 2 aggregation device have been found, only 2 allow")
    elif len(aggregations) > 2:
        parsingError.add("More than 2 aggregation device have been found, only 2 allow")

    ## Check if all child access group have 2 hosts, no more, no less
    access_groups = groups['access'].child_groups
    for access_group in access_groups:
        access_devices = access_group.get_hosts()
        if len(access_devices) < 2:
            parsingError.add("Less than 2 access devices have been found in group " + access_group.name + ", only 2 allow")
        elif len(access_devices) > 2:
            parsingError.add("More than 2 access devices have been found in group " + access_group.name + ", only 2 allow")

def check_config_file( config, topology, parsingError ):

    definition = yaml.load( open(path.join(here, 'configuration.def.yml')) )
    defconf.validate_config( config, definition, 'configuration.def.yml' )

    ## Check if all links names provided exist and replace name with proper info
    for name, vlan in config['vlans'].iteritems():
        for i in range(len(vlan['links'])):
            link = vlan['links'][i]
            if not topology['external_links'].has_key(link):
                parsingError.add("Vlan {0}: Link '{1}' not found in topology file".format(name, link))
            else:
                vlan['links'][i] = { link: topology['external_links'][link] }

def assign_interfaces_to_devices( topology, devices ):

    for link in topology['internal_links']:
        side1 = link[0].split()
        side2 = link[1].split()
        dev1 = side1[0]
        dev2 = side2[0]

        ## if Devices are Peer
        if devices[dev1].get_peer_name() == dev2:
            logger.debug('Device {0} and {1} are peer'.format(dev1, dev2))
            devices[dev1].add_link_to_peer(side1[1])
            devices[dev2].add_link_to_peer(side2[1])
        ## if Dev1 is aggregation, then dev2 is access
        elif devices[dev1].is_aggregation() and devices[dev2].is_access():
            access_grp = devices[dev2].get_access_grp()
            logger.debug('Device {0} is Aggregation and {1} is Access ({2})'.format(dev1, dev2, access_grp))
            devices[dev1].add_link_to_access( access_grp, dev2, side1[1] )
            devices[dev2].add_link_to_aggregation(side2[1])
        elif devices[dev1].is_access() and devices[dev2].is_aggregation():
            access_grp = devices[dev1].get_access_grp()
            logger.debug('Device {0} is Access ({1}) and {2} is Aggregation'.format(dev1, access_grp, dev2))
            devices[dev1].add_link_to_aggregation(side1[1])
            devices[dev2].add_link_to_access( access_grp, dev1, side2[1] )

    for name, links in topology['external_links'].iteritems():
        for link in links:
            dev_int = link.split()
            devices[dev_int[0]].add_link_to_server(name, dev_int[0], dev_int[1])

def expland_vlans( config ):

    for name, value in config['vlans'].iteritems():
        #  add name at the same level
        value['name'] = name

        # Parse network info and generate IP for VIP and all routers
        network_info = value['network'].split('/')
        net = network_info[0].split('.')

        value['network'] = network_info[0]
        value['mask'] = network_info[1]
        value['vip'] = "{0}.{1}.{2}.{3}".format( net[0], net[1], net[2], config['global']['default_gw_ip'] )
        value['router_ips'] = []
        for i in config['global']['router_ips']:
            value['router_ips'].append( "{0}.{1}.{2}.{3}".format( net[0], net[1], net[2], i ) )


def generate_mac_address( qty, base_mac ):

    mac_addresses = []

    for i in range(qty):
        mac = "{0}:{1:02}".format( base_mac, i )
        mac_addresses.append(mac)

    return mac_addresses
