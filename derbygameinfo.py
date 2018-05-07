# THIS SCRIPT IS UNFINISHED. CHECK BACK FOR UPDATES
#
# Usage:
#  python derbygameinfo.py -s <source server> [-t <target server>]
#
# This file was last modified on 2018-05-07

import sys, getopt, requests, json, time, datetime
import xml.etree.ElementTree as ET

DATA_UPDATE_INTERVAL = 0.2

#connect and read timeouts for the Requests module
REQUESTS_CONNECT_TIMEOUT = 60
REQUESTS_READ_TIMEOUT    = 60
    
    
def getgameinfo2(p_server):
    r = requests.get('http://%s:8000/XmlScoreBoard/get?key=85238ed0-2509-448c-b4fa-0a600da7eab9' % p_server, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if r.status_code != requests.codes.ok:
        return (None)
            
    return(r.text)
    
    
def putgameinfo(p_server, p_gamedata):
    r = requests.put('http://%s' % p_server, data=json.dumps(p_gamedata), headers={'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if r.status_code != requests.codes.ok:
        return (None)
            
    return(r.text)
    
    
def main(argv):

    arg_sourcesrv = ''
    arg_targetsrv = ''
    
    #get command line arguments
    try:
        opts, args = getopt.getopt(argv, 's:t:')
    except getopt.GetoptError:
        sys.exit(2)
        
    for opt, arg in opts:
        if opt == '-s':
            arg_sourcesrv  = arg
        elif opt == '-t':
            arg_targetsrv  = arg  
            
    flag_gottarget = False       
    if arg_targetsrv != '':
        flag_gottarget = True
    
    print ('Source server: %s' % arg_sourcesrv)
    print ('Target server: %s' % arg_targetsrv)
    print ('Press Ctrl+C to exit')
    
    gamestate = {'Clock': 
        {
            'Period'        : '30:00',
            'Jam'           : '2:00',
            'Lineup'        : '00:00',
            'Intermission'  : '15:00'
        },
        'Team':{
            '1': {'Score':'0'},
            '2': {'Score':'0'}
        }}
                
    while True:
        flag_haschanged = False
        time.sleep(DATA_UPDATE_INTERVAL)
        retvalue = getgameinfo2(arg_sourcesrv)
        #print(retvalue)
        if not retvalue is None:
            root = ET.fromstring(retvalue)
            for clock in root.iter('Clock'):
                clockid = clock.get('Id')
                for elem in clock.iter('Time'):
                    seconds=int(int(elem.text)/1000)
                    m, s = divmod(seconds, 60)
                    gamestate['Clock'][clockid] = '%02d:%02d' % (m,s)
                    flag_haschanged = True
            for team in root.iter('Team'):
                teamid = team.get('Id')
                for elem in team.iter('Score'):
                    gamestate['Team'][teamid]['Score'] = elem.text
                    flag_haschanged = True

        #print(prevstate)
           
        if flag_haschanged:   
            print('here')
            if flag_gottarget:
                putgameinfo(arg_targetsrv, gamestate)
            else:
                print(gamestate)

if __name__ == '__main__':
    main(sys.argv[1:])