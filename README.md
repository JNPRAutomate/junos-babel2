
# What is Babel2 ?
Babel2 is a small tool working on top of Ansible that help to easily create and deploy configurations for different type of Datacenter L2 topologies like :
 - MC-LAG Fabric
 - Junos Fusion Datacenter

# How does it works

Babel2 takes inputs independent of the network architecture and is able to generate
configuration files for Junos Fusion Datacenter and MC-LAG Fabric:

These independent inputs are provided via 3 main files
 - [hosts] Standard Ansible Inventory File [[example](https://github.com/JNPRAutomate/junos-babel2/blob/master/input/hosts)
 - [topology.yaml] List of all physical connections [example](https://github.com/JNPRAutomate/junos-babel2/blob/master/input/topology.yaml)
 - [configuration.yaml] All information regarding L2 Networks that needs to be deploy [example](https://github.com/JNPRAutomate/junos-babel2/blob/master/input/configuration.yaml)
input files structure is explained [in the Wiki](https://github.com/JNPRAutomate/junos-babel2/wiki/input-files)

Based on these information, Babel2 will dynamically generate Ansible variables file that are matching pre-defined templates for Junos Fusion Datacenter and MC-LAG
Once these variables are generated based on customers input, the generation of all configuration and the deployment of those configuration is done entirely with Ansible in a standard way.

Ansible [templates](https://github.com/JNPRAutomate/junos-babel2/wiki/roles) and [playbooks](https://github.com/JNPRAutomate/junos-babel2/wiki/playbooks) are provided to be able to:
 - Build configurations for MC-LAG and/or Junos Fusion Datacenter
 - Build and deploy configurations for MC-LAG and/or Junos Fusion Datacenter
[See list of provided playbooks](https://github.com/JNPRAutomate/junos-babel2/wiki/playbooks)

# How to start
 1/ [Installation Instruction and dependencies list available](https://github.com/JNPRAutomate/junos-babel2/wiki/install)
 2/ [Getting start Guide](https://github.com/JNPRAutomate/junos-babel2/wiki/setup)
