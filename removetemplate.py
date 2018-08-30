# NOTE: THIS SCRIPT IS UNFINISHED. CHECK BACK FOR UPDATES
#
# This is a script to convert networks configured as template-based to indivudually managed networks without templates.
#  At this stage the script is limited to MX-only networks.
#
# Usage:
#  python removetemplate.py -k <key> -o <org> [-a <admin privilege> -f <filter tag> -b <base net>]
#
# Mandatory arguments:
#  -k <key>                 Your Meraki Dashboard API key
#  -o <org>                 The name of the organization you want to modify
#
# Optional arguments:
#  -a <admin privilege>     Maximum privilege level for copied network administrators. Valid options:
#                            full           Administators copied can have up to full admin privileges
#                            read-only      Full network admins will be limited to read-only in the new net (default)
#  -f <filter tag>          Only process networks tagged <filter tag>
#  -b <base net>            Name of network that will be used as clone source to create the new  networks. The
#                            base net will contain IPS, AMP, NAT, Content filtering and Traffic shaping settings. The base
#                            net needs to be type 'appliance' and NOT bound to a template
#
# Example, process all MX networks tagged "convertme" in org "Meraki Inc", using base net named "clone_source":
#  python removetemplate.py -k 1234 -o "Meraki Inc" -b clone_source -f convertme
#
# Use double quotes ("") in Windows to pass arguments containing spaces. Names are case-sensitive.
#
# The Base must have the following configuration:
#   * VLANs enabled
#   * All VLANs should have subnets that are NOT used in the production network
#   * Although DHCP parameters can be overwritten, the DHCP run/relay/off switch cannot. If the clone source
#      has VLANs predefined, have the DHCP run state configured in them the correct way. Any VLANs not present in
#      the clone source net will be created as "DHCP: run server"
#   * Have IPS, AMP, NAT, Content filtering and Traffic shaping settings configured
#
# This script was developed using Python 3.6.4. You will need the Requests module to run it. You can install
#  the module via pip:
#  pip install requests
#
# More info on this module:
#   http://python-requests.org
#
# To make script chaining easier, all lines containing informational messages to the user
#  start with the character @
#
# This file was last modified on 2018-05-04

import sys, getopt, requests, json, time
from datetime import datetime

#Used for time.sleep(API_EXEC_DELAY). Delay added to avoid hitting dashboard API max request rate
API_EXEC_DELAY = 0.21

#connect and read timeouts for the Requests module
REQUESTS_CONNECT_TIMEOUT = 60
REQUESTS_READ_TIMEOUT    = 60

#used by merakirequestthrottler(). DO NOT MODIFY
LAST_MERAKI_REQUEST = datetime.now() 

        
def printusertext(p_message):
    #prints a line of text that is meant for the user to read
    #do not process these lines when chaining scripts
    print('@ %s' % p_message) 


def printhelp():
    #prints help text
    printusertext('This is a script to convert networks configured as template-based to indivudually managed networks without templates.')
    printusertext('At this stage the script is limited to MX-only networks.')
    printusertext('')
    printusertext('Usage:')
    printusertext(' python removetemplate.py -k <key> -o <org> [-a <admin privilege> -f <filter tag> -b <base net>]')
    printusertext('')
    printusertext('Mandatory arguments:')
    printusertext(' -k <key>                 Your Meraki Dashboard API key')
    printusertext(' -o <org>                 The name of the organization you want to modify')
    printusertext('')
    printusertext('Optional arguments:')
    printusertext(' -a <admin privilege>     Maximum privilege level for copied network administrators. Valid options:')
    printusertext('                           full           Administators copied can have up to full admin privileges')
    printusertext('                           read-only      Full network admins will be limited to read-only in the new net (default)')
    printusertext(' -f <filter tag>          Only process networks tagged <filter tag>')
    printusertext(' -b <base net>            Name of network that will be used as clone source to create the new  networks. The')
    printusertext('                           base net will contain IPS, AMP, NAT, Content filtering and Traffic shaping settings.')
    printusertext('                           The base net needs to be type "appliance" and NOT bound to a template')
    printusertext('')
    printusertext('Example, process all MX networks tagged "convertme" in org "Meraki Inc", using base net named "clone_source":')
    printusertext(' python removetemplate.py -k 1234 -o "Meraki Inc" -b clone_source -f convertme')
    printusertext('')
    printusertext('Use double quotes ("") in Windows to pass arguments containing spaces. Names are case-sensitive.')
    
    
def merakirequestthrottler():
    #makes sure there is enough time between API requests to Dashboard to avoid hitting shaper
    global LAST_MERAKI_REQUEST
    
    if (datetime.now()-LAST_MERAKI_REQUEST).total_seconds() < API_EXEC_DELAY:
        time.sleep(API_EXEC_DELAY)
    
    LAST_MERAKI_REQUEST = datetime.now()
    return   
    
    
def getorgid(p_apikey, p_orgname):
    #looks up org id for a specific org name
    #on failure returns 'null'
    
    merakirequestthrottler()
    
    r = requests.get('https://api.meraki.com/api/v0/organizations', headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if r.status_code != requests.codes.ok:
        return (None)
    
    rjson = r.json()
    
    for record in rjson:
        if record['name'] == p_orgname:
            return record['id']
    return (None) 
    
    
def getshard(p_apikey, p_orgid):
    #Looks up shard FQDN host for a specific org. Use this URL instead of 'dashboard.meraki.com'
    # when making API calls with API accounts that can access multiple orgs.
    #On failure returns 'null'
        
    merakirequestthrottler()
    
    r = requests.get('https://api.meraki.com/api/v0/organizations/%s/snmp' % p_orgid, headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if r.status_code != requests.codes.ok:
        return (None)
        
    rjson = r.json()
    
    return(rjson['hostname'])
    
 
def gettemplates(p_apikey, p_orgid, p_shardhost):
    #returns the list of configuration templates for a specified organization
    
    merakirequestthrottler()
    
    r = requests.get('https://%s/api/v0/organizations/%s/configTemplates' % (p_shardhost, p_orgid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
        
    if r.status_code != requests.codes.ok:
        return (None)
    
    rjson = r.json()
    
    return(rjson) 
    
    
def getnetworks(p_apikey, p_orgid, p_shardhost):
    #returns the list of networks for a specified organization
    
    merakirequestthrottler()
    
    r = requests.get('https://%s/api/v0/organizations/%s/networks' % (p_shardhost, p_orgid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
        
    if r.status_code != requests.codes.ok:
        return (None)
    
    rjson = r.json()
    
    return(rjson) 
    
    
def createnet(p_apikey, p_orgid, p_shardurl, p_name, p_basenetid = None, p_nettags = None):
   #creates a network into an organization, either by cloning an existing one, or by cloning
   
    merakirequestthrottler()
    
    if p_basenetid is None:
        payload = json.dumps({'name':p_name, 'type':'appliance', 'tags':'removetemplate-py'})
    else:
        if p_nettags is None:
            payload = json.dumps({'name':p_name, 'type':'appliance', 'copyFromNetworkId': p_basenetid})
        else:
            payload = json.dumps({'name':p_name, 'type':'appliance', 'tags':p_nettags, 'copyFromNetworkId': p_basenetid})
        
    r = requests.post('https://%s/api/v0/organizations/%s/networks' % (p_shardurl, p_orgid), data=payload, headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if 200 <= r.status_code < 300:
        rjson = r.json()
        return (rjson)
      
    return(None)  
    

def deletenet(p_apikey, p_netid, p_shardhost):
    #returns the list of networks for a specified organization
    
    merakirequestthrottler()
    
    r = requests.delete('https://%s/api/v0/networks/%s' % (p_shardhost, p_netid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if 200 <= r.status_code < 300:
        return ('ok')
        
    return(None)
    
    
def getvlans(p_apikey, p_netid, p_shardhost):
    #returns the list of VLANs for a network
    
    merakirequestthrottler()
    
    r = requests.get('https://%s/api/v0/networks/%s/vlans' % (p_shardhost, p_netid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if r.status_code != requests.codes.ok:
        return (None)
    
    rjson = r.json()
    
    return(rjson) 
    

def createvlan(p_apikey, p_netid, p_shardurl, p_attributes):
   #creates a MX VLAN into a network
   
    merakirequestthrottler()
            
    r = requests.post('https://%s/api/v0/networks/%s/vlans' % (p_shardurl, p_netid), data=json.dumps(p_attributes), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if 200 <= r.status_code < 300:
        rjson = r.json()
        return ('ok')
      
    return(None) 
    
    
def updatevlan(p_apikey, p_netid, p_shardurl, p_attributes):
    #update an existing MX VLAN
   
    merakirequestthrottler()
            
    r = requests.put('https://%s/api/v0/networks/%s/vlans/%s' % (p_shardurl, p_netid, p_attributes['id']), data=json.dumps(p_attributes), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if 200 <= r.status_code < 300:
        rjson = r.json()
        return ('ok')
      
    return(None) 
    
    
def deletevlan(p_apikey, p_netid, p_shardurl, p_vlanid):
   #delete an existing MX VLAN
   
    merakirequestthrottler()
            
    r = requests.delete('https://%s/api/v0/networks/%s/vlans/%s' % (p_shardurl, p_netid, p_vlanid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    return(None) 
    
    
def readmxfwruleset(p_apikey, p_shardhost, p_nwid):
    #return the MX L3 firewall ruleset for a network

    merakirequestthrottler()
    
    r = requests.get('https://%s/api/v0/networks/%s/l3FirewallRules' % (p_shardhost, p_nwid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
            
    if r.status_code != requests.codes.ok: 
        return None
    
    rjson = r.json()
    
    return(rjson)
    
    
def writemxfwruleset(p_apikey, p_shardhost, p_nwid, p_ruleset):
    #writes MX L3 ruleset for a device to cloud
    
    merakirequestthrottler()
    
    r = requests.put('https://%s/api/v0/networks/%s/l3FirewallRules/' % (p_shardhost, p_nwid), data=json.dumps({'rules': p_ruleset}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
            
    if r.status_code != requests.codes.ok:
        return None
    
    return('ok')
    
    
def getorgadmins(p_apikey, p_orgid, p_shardhost):
    #returns the list of admins for a specified organization
    
    merakirequestthrottler()
    
    r = requests.get('https://%s/api/v0/organizations/%s/admins' % (p_shardhost, p_orgid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if r.status_code != requests.codes.ok:
        return (None)
    
    rjson = r.json()
    
    return(rjson)
    
    
def updateorgadmin(p_apikey, p_orgid, p_shard, p_attributes):
    #creates admin into an organization
   
    merakirequestthrottler()
    
    r = requests.put('https://%s/api/v0/organizations/%s/admins/%s' % (p_shard, p_orgid, p_attributes['id']), data=json.dumps(p_attributes), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
            
    if r.status_code != requests.codes.ok:    
        return None
      
    return('ok') 
    
    
def stripdefaultrule(p_inputruleset):
    #strips the default allow ending rule from an MX L3 Firewall ruleset
    outputset = []
    
    if len(p_inputruleset) > 0:
        lastline = p_inputruleset[len(p_inputruleset)-1]
        if lastline == {'protocol': 'Any', 'policy': 'allow', 'comment': 'Default rule', 'srcCidr': 'Any', 'srcPort': 'Any', 'syslogEnabled': False, 'destPort': 'Any', 'destCidr': 'Any'}:
            outputset = p_inputruleset[:-1]
        else:
            outputset = p_inputruleset
            
    return(outputset)
    
    
def main(argv):

#  python removetemplate.py -k <key> -o <org> [-a <admin privilege> -f <filter tag> -b <base net>]

    #initialize variables for command line arguments
    arg_apikey      = ''
    arg_orgname     = ''
    arg_adminlvl    = ''
    arg_filter      = ''
    arg_basenet     = ''
    
    #get command line arguments
    try:
        opts, args = getopt.getopt(argv, 'hk:o:a:f:b:')
    except getopt.GetoptError:
        printhelp()
        sys.exit(2)
    
    for opt, arg in opts:
        if   opt == '-h':
            printhelp()
            sys.exit()
        elif opt == '-k':
            arg_apikey  = arg
        elif opt == '-o':
            arg_orgname = arg
        elif opt == '-a':
            arg_adminlvl = arg
        elif opt == '-f':
            arg_filter  = arg
        elif opt == '-b':
            arg_basenet = arg
            
    #check that all mandatory arguments have been given
    if arg_apikey == '' or arg_orgname == '':
        printhelp()
        sys.exit(2)
        
    if not arg_adminlvl in ['full', 'read-only', '']:
        printusertext('ERROR 01: Max admin privilege must be "full" or "read-only"')
        sys.exit(2)        
        
    #set optional parameters with no given values to defaults
    if arg_adminlvl == '':
        arg_adminlvl = 'read-only'
    #arg_basenet == '' means not specified
    #arg_filter  == '' means not specified
    
    #get orgid and shard host
    try:
        orgid = getorgid(arg_apikey, arg_orgname)
    except:
        printusertext('ERROR 02: Unable to contact Meraki cloud')
        sys.exit(2)
    if orgid is None:
        printusertext('ERROR 03: Unable to find org "%s"' % arg_orgname)
        sys.exit(2)
    try:
        shard = getshard(arg_apikey, orgid)
    except:
        printusertext('ERROR 04: Unable to contact Meraki cloud')
        sys.exit(2)
    if shard is None:
        printusertext('ERROR 05: Unable to resolve shard for org "%s"' % arg_orgname)
        sys.exit(2)
        
    #get list of networks
    #network fields: {'id', 'organizationId', 'name', 'timeZone', ('tags'), 'type', ('configTemplateId')}
    try:
        networklist = getnetworks(arg_apikey, orgid, shard)
    except:
        printusertext('ERROR 06: Unable to contact Meraki cloud')
        sys.exit(2)
    if networklist is None:
        printusertext('ERROR 07: Org "%s" contains no networks' % arg_orgname)
        sys.exit(2)
        
    cleannetlist = []
    for network in networklist:
        if 'configTemplateId' in network:
            #if user gave net tag filter, make sure tag exists in net
            flag_infilterscope = True
            if arg_filter != '':
                if network['tags'] is None:
                    flag_infilterscope = False
                elif network['tags'].find(arg_filter) == -1:
                    flag_infilterscope = False
                    
            if flag_infilterscope:     
                if network['type'] != 'combined' and network['type'].find('appliance') == -1:
                    printusertext('WARNING: Skipping net "%s": Must be type "combined" or "appliance"' % network['name'])
                else:
                    cleannetlist.append(network)
            else:
                printusertext('WARNING: Skipping net "%s": Not in filter scope' % network['name']) 
        else:
            printusertext('WARNING: Skipping net "%s": Not bound to a template' % network['name'])
            
    #check if user has given a base net name and resolve it if needed
    NEW_NET_ADDED_TAGS = 'removetemplate-py'
    basenetid   = None
    basetags    = None
    if arg_basenet != '':
        for network in networklist:
            if network['name'] == arg_basenet:
                basenetid = network['id']
                if 'configTemplateId' in network:
                    printusertext('ERROR 08: Base net "%s" must not be bound to a template' % arg_basenet)
                    sys.exit(2)
                if network['type'] != 'appliance':
                    printusertext('ERROR 09: Base net "%s" must be type "appliance", not "%s"' % (arg_basenet, network['type']))
                    sys.exit(2)
                if network['tags'] is None:
                    basetags = NEW_NET_ADDED_TAGS
                else:
                    basetags = network['tags'] + ' ' + NEW_NET_ADDED_TAGS
                break
        if basenetid is None:
            printusertext('ERROR 10: Unable to find network with name "%s"' % arg_basenet)
            sys.exit(2)
            
    #Get list of org admins. Will be used later
    orgadmins = getorgadmins(arg_apikey, orgid, shard)
        
    for network in cleannetlist:
        printusertext('INFO: Processing net "%s"' % network['name'])
        
        #create new network
        
        #find an unused network name
        MAX_NETWORK_RENAME_TRIES = 99 #needs to be 1 or more
        newname     = network['name'] + ' - new'
        newnamemod  = newname
        flag_nametaken = False
        for i in range(0, MAX_NETWORK_RENAME_TRIES):
            flag_nametaken = False
            if i != 0:
                newnamemod = newname + str(i)
            for rawnet in networklist:
                if rawnet['name'] == newnamemod:
                    flag_nametaken = True
                    break
            if not flag_nametaken:
                break                
        if i == MAX_NETWORK_RENAME_TRIES:
            printusertext('ERROR 11: Unable to create new net name for "%s"' % network['name'])
            sys.exit(2)
                
        #create the network, with cloning if possible
        try:
            returnmsg = createnet(arg_apikey, orgid, shard, newnamemod, basenetid, basetags)
        except:
            printusertext('ERROR 12: Unable to contact Meraki cloud')
            sys.exit(2)
        if returnmsg is None:
            printusertext('ERROR 13: Unable to create new net for "%s"' % network['name'])
            sys.exit(2)
        newnetid = returnmsg['id']
         
        #Standard VLAN assignment
        #NOTE: Reading/writing VLAN group policies via API is not supported right now
        netvlans = getvlans(arg_apikey, network['id'], shard)
        
        #if VLANs, attempt conversion
        if not netvlans is None:
            printusertext('INFO: Copying VLANs...')
            #check to see if VLANs are enabled in new net
            try:
                newvlans = getvlans(arg_apikey, newnetid, shard)
            except:
                printusertext('ERROR 14: Unable to contact Meraki cloud')
                deletenet(arg_apikey, newnetid, shard)
                sys.exit(2)
            if newvlans is None:
                printusertext('ERROR 15: Use a base net with VLANs enabled to convert net "%s"' % network['name'])
                deletenet(arg_apikey, newnetid, shard)
                sys.exit(2)
                          
            #compare netvlans and newvlans for find which will need to be added, modified, removed in new net
            addvlans = []
            delvlans = []
            modvlans = []
            #check which vlans will need to be added/modified
            for vlan in netvlans:
                flag_vlannotfound = True
                for tempvlan in newvlans:
                    if vlan['id'] == tempvlan['id']:
                        modvlans.append(vlan)
                        flag_vlannotfound = False
                        break
                if flag_vlannotfound:
                    addvlans.append(vlan)
            #check which vlans will need to be removed from the template
            for tvlan in newvlans:
                flag_vlannotfound = True
                for mvlan in modvlans:
                    if tvlan['id'] == mvlan['id']:
                        flag_vlannotfound = False
                        break
                if flag_vlannotfound:
                    delvlans.append(tvlan)
                                    
            #process VLANs
            flag_deletepending = True
            if len(modvlans) > 1:
                for vlan in delvlans:
                    try:
                        deletevlan(arg_apikey, newnetid, shard, vlan['id'])
                    except:
                        printusertext('ERROR 16: Unable to remove source net VLAN "%s"' % vlan['id'])
                        deletenet(arg_apikey, newnetid, shard)
                        sys.exit(2)
                flag_deletepending = False
            for vlan in modvlans:
                try:
                    retvalue = updatevlan(arg_apikey, newnetid, shard, vlan)
                except:
                    printusertext('ERROR 17: Unable to modify source net VLAN "%s"' % vlan['id'])
                    deletenet(arg_apikey, newnetid, shard)
                    sys.exit(2)
            if flag_deletepending:
                for vlan in delvlans:
                    try:
                        deletevlan(arg_apikey, newnetid, shard, vlan['id'])
                    except:
                        printusertext('ERROR 18: Unable to remove source net VLAN "%s"' % vlan['id'])
                        deletenet(arg_apikey, newnetid, shard)
                        sys.exit(2)
            for vlan in addvlans:
                try:
                    createvlan(arg_apikey, newnetid, shard, vlan)
                except:
                    printusertext('ERROR 19: Unable to create VLAN "%s" for net "%s"' % (vlan['id'], newnamemod))
                    deletenet(arg_apikey, newnetid, shard)
                    sys.exit(2) 
                    
            #verify VLANs
            printusertext('INFO: Verifying VLANs...')
            try:
                finalvlans = getvlans(arg_apikey, newnetid, shard)
            except:
                    printusertext('ERROR 20: Unable to verify VLANs for net "%s"' % newnamemod)
                    deletenet(arg_apikey, newnetid, shard)
                    sys.exit(2)
            for srcvlan in netvlans:
                flag_nomatchfound = True
                for finvlan in finalvlans:
                    #DEBUG
                    print ('DEBUG: Checking source %s vs final %s' % (srcvlan['id'], finvlan['id']))
                    if srcvlan['id'] == finvlan['id']:
                        flag_allvaluesmatch = True    
                        for label in srcvlan:
                            #DEBUG
                            print ('DEBUG: Checking label %s' % label)
                            if label != 'networkId':
                                if srcvlan[label] != finvlan[label]:
                                    #DEBUG
                                    print ('DEBUG: Check failed')
                                    flag_allvaluesmatch = False
                                    break 
                                else:
                                    #DEBUG
                                    print ('DEBUG: Check passed')
                        if flag_allvaluesmatch:
                            flag_nomatchfound = False
                        break
                if flag_nomatchfound:
                    printusertext('ERROR 21: VLAN "%s" verification failed for net "%s"' % (srcvlan['id'], newnamemod))
                    deletenet(arg_apikey, newnetid, shard)
                    sys.exit(2)
        #endif not netvlans is None
        
        #Process firewall rules
        printusertext('INFO: Copying firewall rules...')
        try:
            netrules = readmxfwruleset(arg_apikey, shard, network['id'])
        except:
            printusertext('ERROR 22: Unable to read firewall rules for net "%s"' % network['name'])
            deletenet(arg_apikey, newnetid, shard)
            sys.exit(2)
            
        if netrules is None:
            printusertext('ERROR 23: Unable to read firewall rules for net "%s"' % network['name'])
            deletenet(arg_apikey, newnetid, shard)
            sys.exit(2)
            
        striprules = stripdefaultrule(netrules)
                    
        if len(striprules) > 0:
            try:
                writemxfwruleset(arg_apikey, shard, newnetid, striprules)
            except:
                printusertext('ERROR 24: Unable to write firewall rules for net "%s"' % newnamemod)
                deletenet(arg_apikey, newnetid, shard)
                sys.exit(2)
            
            #verify firewall rules
            try:
                newrules = readmxfwruleset(arg_apikey, shard, newnetid)
            except:
                printusertext('ERROR 25: Unable to read firewall rules for net "%s"' % newnamemod)
                deletenet(arg_apikey, newnetid, shard)
                sys.exit(2)
            
            if netrules != newrules:
                printusertext('ERROR 26: Firewall rules\' verification failed for net "%s"' % newnamemod)
                deletenet(arg_apikey, newnetid, shard)
                sys.exit(2)
        #end section: Firewall rules
        
        #Network Admin access + privileges
        printusertext('INFO: Setting net admin access...')
        #Go through Org admin list and find the ones that have a matching name. Transfer them to the new network
        #if admin privilege is higher than the one given as a parameter, limit privilege
        for admin in orgadmins:
            for adnet in admin['networks']:
                if adnet['id'] == network['id']:
                    admincopy = admin
                    privilege = {'id': newnetid, 'access': adnet['access']}
                    if arg_adminlvl == 'read-only' and adnet['access'] == 'full':
                        privilege['access'] = 'read-only'
                    admincopy['networks'].append(privilege)
                    
                    try:
                        retvalue = updateorgadmin(arg_apikey, orgid, shard, admincopy)
                    except:
                        printusertext('ERROR 27: Unable update privileges for admin "%s"' % admincopy['email'])
                        deletenet(arg_apikey, newnetid, shard)
                        sys.exit(2)
                    
                    if retvalue is None:
                        printusertext('WARNING: Unable to update admin "%s" (Conflicting privileges?)' % admincopy['email'])
                        
        #TODO: move devices                     
                            
            
    
if __name__ == '__main__':
    main(sys.argv[1:])