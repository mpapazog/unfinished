import sys, getopt, requests, json
import xml.etree.ElementTree as ET
from flask import Flask, jsonify

#connect and read timeouts for the Requests module
REQUESTS_CONNECT_TIMEOUT = 3
REQUESTS_READ_TIMEOUT    = 3

GAMESTATE = {
        'Error': 'none',
        'ClockPeriodRunning': 'false',
        'ClockPeriodTime': '30:00',
        'ClockPeriodNumber':0,
        'ClockJamRunning': 'false',
        'ClockJamTime': '02:00',
        'ClockJamNumber':0,
        'ClockLineupRunning': 'false',
        'ClockLineupTime': '00:00',
        'ClockLineupNumber':0,
        'ClockIntermissionRunning': 'false',
        'ClockIntermissionTime': '15:00',
        'ClockIntermissionNumber':0,
        'ClockTimeoutRunning': 'false',
        'ClockTimeoutTime': '01:00',
        'ClockTimeoutNumber':0,
        'Team1Score':0,
        'Team1Jamscore':0,
        'Team2Score':0,
        'Team2Jamscore':0} 

LASTSCORE = {'1':0, '2':0}        
        
        
SESSIONKEY = 'none'

SERVER = '127.0.0.1'
        
        
def registertoscoreboard(p_server):
    r = requests.get('http://%s:8000/XmlScoreBoard/register' % p_server, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if r.status_code != requests.codes.ok:
        return (None)
            
    return(r.text)    
    
    
def getgameinfo(p_server, p_sessionkey):
    r = requests.get('http://%s:8000/XmlScoreBoard/get?key=%s' % (p_server, p_sessionkey), timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if r.status_code != requests.codes.ok:
        return (None)
            
    return(r.text)
    

app = Flask(__name__)
 
@app.route("/register/")
def register():
    global SESSIONKEY
    global SERVER
    
    retvalue = registertoscoreboard(SERVER)
    root = ET.fromstring(retvalue)
    for key in root.iter('Key'):
        SESSIONKEY = key.text
    
    return (jsonify({'sessionkey':SESSIONKEY}))
   
@app.route("/status/")   
def status():
    global GAMESTATE
    global LASTSCORE
        
    if SESSIONKEY == 'none':
        return (jsonify({'Error':'Not registered'}))
        
    try:
        retvalue = getgameinfo(SERVER, SESSIONKEY) 
    except:
        print('WARNING: Unable to contact scoreboard server or no update')
        retvalue = None
    if not retvalue is None:        
        root = ET.fromstring(retvalue)
        for clock in root.iter('Clock'):
            clockid = clock.get('Id')
            for elem in clock.iter('Running'):
                GAMESTATE['Clock' + clockid + 'Running'] = elem.text
            for elem in clock.iter('Time'):
                seconds=int(int(elem.text)/1000)
                m, s = divmod(seconds, 60)
                GAMESTATE['Clock' + clockid + 'Time'] = '%02d:%02d' % (m,s)
            for elem in clock.iter('Number'):
                if clockid == 'Jam':
                    if int(elem.text) != GAMESTATE['Clock' + 'Jam' + 'Number']:
                        LASTSCORE['1'] = GAMESTATE['Team' + '1' + 'Score']
                        LASTSCORE['2'] = GAMESTATE['Team' + '2' + 'Score']
                        GAMESTATE['Team' + '1' + 'Jamscore'] = 0
                        GAMESTATE['Team' + '2' + 'Jamscore'] = 0
                GAMESTATE['Clock' + clockid + 'Number'] = int(elem.text)
                    
        for team in root.iter('Team'):
            teamid = team.get('Id')
            for elem in team.iter('Score'):
                GAMESTATE['Team' + teamid + 'Score'] = int(elem.text)
                GAMESTATE['Team' + teamid + 'Jamscore'] = GAMESTATE['Team' + teamid + 'Score'] - LASTSCORE[teamid]
        
    return (jsonify(GAMESTATE))   


def main(argv):
    global SERVER
    
    #get command line arguments
    try:
        opts, args = getopt.getopt(argv, 's:')
    except getopt.GetoptError:
        sys.exit(2)
        
    for opt, arg in opts:
        if opt == '-s':
            SERVER  = arg
    
    print('*** Using source server: %s' % SERVER)

    app.run(host='0.0.0.0')
    
 
if __name__ == "__main__":
    main(sys.argv[1:])