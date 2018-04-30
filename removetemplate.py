# NOTE: THIS SCRIPT IS UNFINISHED. CHECK BACK FOR UPDATES
#
# This is a script to convert networks configured as template-based to indivudually managed networks without templates.
#  At this stage the script is limited to MX-only networks.
#
# Usage:
#  removetemplate.py -k <key> -o <org> [-a <admin privilege> -f <filter> -b <base net>]
#   Base net needs to be type 'appliance' and NOT bound to a template
#
#TODO: flow:
#   get list of networks (with template mappings)
#   create new net
#   copy settings from temp to new net
#   copy admins to new net, possibly changing permissions
#   move devices (beware of static IP config)
#
# On clone source VLAN:
#   * Have VLANs enabled
#   * Any VLANs should have subnets that are NOT used in the production network
#
# This file was last modified on 2018-04-30

import sys, getopt, requests, json, time
from datetime import datetime

#Used for time.sleep(API_EXEC_DELAY). Delay added to avoid hitting dashboard API max request rate
API_EXEC_DELAY = 0.21

#connect and read timeouts for the Requests module
REQUESTS_CONNECT_TIMEOUT = 60
REQUESTS_READ_TIMEOUT    = 60

#used by merakirequestthrottler(). DO NOT MODIFY
LAST_MERAKI_REQUEST = datetime.now() 

        
class c_network:
    def __init__(self):
        self.id         = ''
        self.name       = ''
        self.template   = ''


def printusertext(p_message):
    #prints a line of text that is meant for the user to read
    #do not process these lines when chaining scripts
    print('@ %s' % p_message) 


def printhelp():
    #prints help text
    #DEBUG
    printusertext('Help text not implemented.')
    
    
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
    
    
def getorgadmins(p_apikey, p_orgid, p_shardhost):
    #returns the list of admins for a specified organization
    
    merakirequestthrottler()
    
    r = requests.get('https://%s/api/v0/organizations/%s/admins' % (p_shardhost, p_orgid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if r.status_code != requests.codes.ok:
        return (None)
    
    rjson = r.json()
    
    return(rjson)
    
    
def main(argv):

#  removetemplate.py -k <key> -o <org> -m <mapping mode> [-a <admin privilege> -f <filter> -b <base net>]

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
        
    #set unset optional parameters to defaults
    if arg_filter  == '':
        arg_filter  = 'all'
    #arg_basenet  == '' means not specified
    #arg_adminlvl == '' means not specified
    
    #get orgid and shard host
    try:
        orgid = getorgid(arg_apikey, arg_orgname)
    except:
        printusertext('ERROR XX1: Unable to contact Meraki cloud')
        sys.exit(2)
    if orgid is None:
        printusertext('ERROR XX: Unable to find org "%s"' % arg_orgname)
        sys.exit(2)
    try:
        shard = getshard(arg_apikey, orgid)
    except:
        printusertext('ERROR XX2: Unable to contact Meraki cloud')
        sys.exit(2)
    if shard is None:
        printusertext('ERROR XX: Unable to resolve shard for org "%s"' % arg_orgname)
        sys.exit(2)
        
    #get list of networks
    #network fields: {'id', 'organizationId', 'name', 'timeZone', ('tags'), 'type', ('configTemplateId')}
    try:
        networklist = getnetworks(arg_apikey, orgid, shard)
    except:
        printusertext('ERROR XX3: Unable to contact Meraki cloud')
        sys.exit(2)
    if networklist is None:
        printusertext('ERROR XX: Org "%s" contains no networks' % arg_orgname)
        sys.exit(2)
        
    cleannetlist = []
    for network in networklist:
        if 'configTemplateId' in network:
            cleannetlist.append(network)
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
                    printusertext('ERROR XX: Base net "%s" must not be bound to a template' % arg_basenet)
                    sys.exit(2)
                if network['type'] != 'appliance':
                    printusertext('ERROR XX: Base net "%s" must be type "appliance", not "%s"' % (arg_basenet, network['type']))
                    sys.exit(2)
                if network['tags'] is None:
                    basetags = NEW_NET_ADDED_TAGS
                else:
                    basetags = network['tags'] + ' ' + NEW_NET_ADDED_TAGS
                break
        if basenetid is None:
            printusertext('ERROR XX: Unable to find network with name "%s"' % arg_basenet)
            sys.exit(2)
        
    for network in cleannetlist:
        if network['type'] == 'combined' or network['type'].find('appliance') != -1:
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
                printusertext('ERROR XX: Unable to create new net name for "%s"' % network['name'])
                sys.exit(2)
                    
            #create the network, with cloning if possible
            try:
                returnmsg = createnet(arg_apikey, orgid, shard, newnamemod, basenetid, basetags)
            except:
                printusertext('ERROR XX4: Unable to contact Meraki cloud')
                sys.exit(2)
            if returnmsg is None:
                printusertext('ERROR XY: Unable to create new net for "%s"' % network['name'])
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
                    printusertext('ERROR XX5: Unable to contact Meraki cloud')
                    deletenet(arg_apikey, newnetid, shard)
                    sys.exit(2)
                if newvlans is None:
                    printusertext('ERROR XZ1: Use a base net with VLANs enabled to convert net "%s"' % network['name'])
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
                            printusertext('ERROR Xdel: Unable to remove source net VLAN "%s"' % vlan['id'])
                            deletenet(arg_apikey, newnetid, shard)
                            sys.exit(2)
                    flag_deletepending = False
                for vlan in modvlans:
                    try:
                        retvalue = updatevlan(arg_apikey, newnetid, shard, vlan)
                    except:
                        printusertext('ERROR Xmod: Unable to modify source net VLAN "%s"' % vlan['id'])
                        deletenet(arg_apikey, newnetid, shard)
                        sys.exit(2)
                if flag_deletepending:
                    for vlan in delvlans:
                        try:
                            deletevlan(arg_apikey, newnetid, shard, vlan['id'])
                        except:
                            printusertext('ERROR Xdel2: Unable to remove source net VLAN "%s"' % vlan['id'])
                            deletenet(arg_apikey, newnetid, shard)
                            sys.exit(2)
                for vlan in addvlans:
                    try:
                        createvlan(arg_apikey, newnetid, shard, vlan)
                    except:
                        printusertext('ERROR Xadd: Unable to create VLAN "%s" for net "%s"' % (vlan['id'], newnamemod))
                        deletenet(arg_apikey, newnetid, shard)
                        sys.exit(2) 
                        
                #verify VLANs
                printusertext('INFO: Verifying VLANs...')
                try:
                    finalvlans = getvlans(arg_apikey, newnetid, shard)
                except:
                        printusertext('ERROR Xver: Unable to verify VLANs for net "%s"' % newnamemod)
                        deletenet(arg_apikey, newnetid, shard)
                        sys.exit(2)
                for srcvlan in netvlans:
                    flag_nomatchfound = True
                    for finvlan in finalvlans:
                        if srcvlan['id'] == finvlan['id']:
                            flag_allvaluesmatch = True    
                            for label in srcvlan:
                                if label != 'networkId':
                                    if srcvlan[label] != finvlan[label]:
                                        flag_allvaluesmatch = False
                                        break                        
                            if flag_allvaluesmatch:
                                flag_nomatchfound = False
                            break
                    if flag_nomatchfound:
                        printusertext('ERROR Xver2: VLAN "%s" verification failed for net "%s"' % (srcvlan['id'], newnamemod))
                        deletenet(arg_apikey, newnetid, shard)
                        sys.exit(2)
            
            #Firewall rules with Network templates
            #DHCP
            #Threat protection: AMP + IPS
            #Content filtering
            #1:1 NAT?
            #Network Admin access + privileges
            #take into account local overrides
            #DHCP
            #NAT
            #Traffic shaping
            #Local admins
            #Content filtering
            #AMP whitelisting
            #DHCP + static
    
if __name__ == '__main__':
    main(sys.argv[1:])