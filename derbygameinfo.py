# THIS SCRIPT IS UNFINISHED. CHECK BACK FOR UPDATES
#
# Usage:
#  python derbygameinfo.py -s <source server> [-t <target server>]
#
# This file was last modified on 2018-05-09

import sys, getopt, requests, json, time, datetime
import xml.etree.ElementTree as ET

DATA_UPDATE_INTERVAL = 0.2

#connect and read timeouts for the Requests module
REQUESTS_CONNECT_TIMEOUT = 5
REQUESTS_READ_TIMEOUT    = 5
    

def registertoscoreboard(p_server):
    r = requests.get('http://%s:8000/XmlScoreBoard/register' % p_server, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if r.status_code != requests.codes.ok:
        return (None)
            
    return(r.text)    
    
    
def getgameinfo2(p_server, p_sessionkey):
    r = requests.get('http://%s:8000/XmlScoreBoard/get?key=%s' % (p_server, p_sessionkey), timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if r.status_code != requests.codes.ok:
        return (None)
            
    return(r.text)
    
    
def putgameinfo(p_server, p_gamedata):
    r = requests.post('http://%s' % p_server, data=json.dumps(p_gamedata), headers={'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
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
    print ('Press Ctrl+C repeatedly to exit')
    
    gamestate = {'Clock': 
        {
            'Period'        : {'Running': 'false', 'Time': '30:00', 'Number':0},
            'Jam'           : {'Running': 'false', 'Time': '02:00', 'Number':0},
            'Lineup'        : {'Running': 'false', 'Time': '00:00', 'Number':0},
            'Intermission'  : {'Running': 'false', 'Time': '15:00', 'Number':0},
            'Timeout'       : {'Running': 'false', 'Time': '01:00', 'Number':0}
        },
        'Team':{
            '1': {'Score':0, 'Jamscore':0},
            '2': {'Score':0, 'Jamscore':0}
        }}
        
    lastscore       = {'1':0, '2':0}
        
    sessionkey = ''
    #this may crash if unable to register. that is OK, since the script cannot continue without a sessionkey
    retvalue = registertoscoreboard(arg_sourcesrv)   
    root = ET.fromstring(retvalue)
    for key in root.iter('Key'):
        sessionkey = key.text
             
                
    while True:
        flag_haschanged = False
        time.sleep(DATA_UPDATE_INTERVAL)
        try:
            retvalue = getgameinfo2(arg_sourcesrv, sessionkey)
        except:
            print('WARNING: Unable to contact scoreboard server')
            retvalue = None
        if not retvalue is None:
            #DEBUG
            #print('')
            #print(retvalue)
            
            root = ET.fromstring(retvalue)
            for clock in root.iter('Clock'):
                clockid = clock.get('Id')
                for elem in clock.iter('Running'):
                    gamestate['Clock'][clockid]['Running'] = elem.text
                    flag_haschanged = True
                for elem in clock.iter('Time'):
                    seconds=int(int(elem.text)/1000)
                    m, s = divmod(seconds, 60)
                    gamestate['Clock'][clockid]['Time'] = '%02d:%02d' % (m,s)
                    flag_haschanged = True
                for elem in clock.iter('Number'):
                    if clockid == 'Jam':
                        if int(elem.text) != gamestate['Clock']['Jam']['Number']:
                            lastscore['1'] = gamestate['Team']['1']['Score']
                            lastscore['2'] = gamestate['Team']['2']['Score']
                            gamestate['Team']['1']['Jamscore'] = 0
                            gamestate['Team']['2']['Jamscore'] = 0
                    gamestate['Clock'][clockid]['Number'] = int(elem.text)
                    flag_haschanged = True
                        
            for team in root.iter('Team'):
                teamid = team.get('Id')
                for elem in team.iter('Score'):
                    gamestate['Team'][teamid]['Score'] = int(elem.text)
                    gamestate['Team'][teamid]['Jamscore'] = gamestate['Team'][teamid]['Score'] - lastscore[teamid]
                    flag_haschanged = True
           
        if flag_haschanged:  
            if flag_gottarget:
                try:
                    putgameinfo(arg_targetsrv, gamestate)
                except:
                    print('WARNING: Unable to contact target server')
                print ('Sent update at %s' % datetime.datetime.now())
            else:
                print(gamestate)

if __name__ == '__main__':
    main(sys.argv[1:])