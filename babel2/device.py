import logging
import pprint

logger = logging.getLogger( 'babel2' )
pp = pprint.PrettyPrinter(indent=4)

class Device:
         ## o unknown, 1 agg, 2 access \

    def __init__( self, name ):
        self.__name = name
        self.__links = {}
        self.__peer = ''
        self.__personnality = 0
        self.__links['to_peer'] = []
        self.__links['to_access'] = {}
        self.__links['to_aggregation'] = []
        self.__links['to_server'] = {}
        self.__group_name = ''
        self.__fpc_id = 0

    def get_name(self):
        return self.__name

    def get_peer_name(self):
        return self.__peer.get_name()

    def get_fpc_id(self):
        return self.__fpc_id

    def set_fpc_id(self, fpc_id):
        self.__fpc_id = fpc_id

    def set_as_aggregation(self):
        self.__personnality = 1

    def set_as_access(self, group_name):
        self.__personnality = 2
        self.__group_name = group_name

    def is_aggregation (self):
        if self.__personnality == 1:
            return 1
        else:
            return 0

    def is_access (self):
        if self.__personnality == 2:
            return 1
        else:
            return 0

    def get_access_grp (self):
        return self.__group_name

    def set_peer (self, peer):
        self.__peer = peer

    def get_peer (self):
        return self.__peer

    def add_link_to_peer (self, link):
        self.__links['to_peer'].append(link)
        logger.debug('{0} - add_link_to_peer: link {1} added '.format(self.__name, link))

    def add_link_to_aggregation (self, link):
        self.__links['to_aggregation'].append(link)
        logger.debug('{0} - add_link_to_aggregation: link {1} added '.format(self.__name, link))

    def add_link_to_access (self, grp_name, device, link):
        if not self.__links['to_access'].has_key(grp_name):
            self.__links['to_access'][grp_name] = []

        self.__links['to_access'][grp_name].append({'dev': device, 'int': link})
        logger.debug( '{0} - add_link_to_access: device {1} link {2} added to {3}'.format(self.__name, device, link, grp_name)  )

    def add_link_to_server (self, grp_name, device, link ):
        if not self.__links['to_server'].has_key(grp_name):
            self.__links['to_server'][grp_name] = []

        self.__links['to_server'][grp_name].append({'dev': device, 'int': link})
        logger.debug( '{0} - add_link_to_server: link {1} added to {2}'.format(self.__name, link, grp_name))

    def get_peer_links (self):
        return self.__links['to_peer']

    def get_aggregation_links (self):
        return self.__links['to_aggregation']

    def get_servers_links (self, name):
        if not  self.__links['to_server'].has_key(name):
            return []

        tmp_list = []
        for link in self.__links['to_server'][name]:
            tmp_list.append( link['int'] )
        return tmp_list

    def get_servers_links_with_dev (self, grp_name):
        if not self.__links['to_server'].has_key(grp_name):
            return []
        return self.__links['to_server'][grp_name]

    def get_access_links (self, grp_name):
        if not self.__links['to_access'].has_key(grp_name):
            return []

        tmp_list = []
        for link in self.__links['to_access'][grp_name]:
            tmp_list.append(link['int'])
        return tmp_list

    def get_access_links_with_dev (self, grp_name):
        if not self.__links['to_access'].has_key(grp_name):
            return []
        return self.__links['to_access'][grp_name]
