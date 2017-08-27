from datetime import datetime,timezone
import requests
import json
import io
import sys    

def download_fixtures_file(teamname):
    url_file = open('data/urls.json','r')
    url_data = json.load(url_file)
    try:
        url = url_data['url'].replace('id',str(url_data['team_id'][teamname]))
    except KeyError:
        print("Ïnvalid team name")
        sys.exit(0)
    try:
        down_request = requests.get(url)
        return io.StringIO(down_request.text)
    except requests.ConnectionError:
        print("No internet. Retrieving offline data...\n")
        return io.StringIO()
    

def get_fixtures_data(teamname):
    team_file = download_fixtures_file(teamname)
    fixture_data=[]
    for line in team_file:
        fixture_data.append(line.strip())
    return fixture_data

def get_list(fixture_data,value_to_get):
    value_list=[]
    for line in fixture_data:
        if(line[:len(value_to_get)]==value_to_get):
            value_list.append(line[len(value_to_get)+1:])
    return value_list

def convert_to_datetime(dt_string):
    year = int(dt_string[:4])
    month = int(dt_string[4:6])
    day = int(dt_string[6:8])
    hour = int(dt_string[9:11])
    minute = int(dt_string[11:13])
    seconds = int(dt_string[13:15])
    return datetime(year,month,day,hour,minute,seconds,tzinfo=timezone.utc)

def get_datetime_list(fixture_data,value_to_get):
    dt_string_list = get_list(fixture_data,value_to_get)
    datetime_list=[]
    for dt_string in dt_string_list:
        datetime_list.append(convert_to_datetime(dt_string).replace(tzinfo=timezone.utc).astimezone(tz=None))
    return datetime_list

def get_fixtures(teamname):
    fixture_data = get_fixtures_data(teamname)
    if fixture_data:
        fixtures = []
        summaries = get_list(fixture_data,'SUMMARY')
        start_times = get_datetime_list(fixture_data,'DTSTART')
        end_times = get_datetime_list(fixture_data,'DTEND')
        venues = get_list(fixture_data,'LOCATION')
        for i in range(len(summaries)):
            fixture = {}
            fixture['Summary'] = summaries[i]
            fixture['Start Time'] = start_times[i].strftime("%d %B %Y, %I:%M %p")
            fixture['End Time'] = end_times[i].strftime("%d %B %Y, %I:%M %p")
            fixture['Venue'] = venues[i]
            fixtures.append(fixture)
        save_fixtures(teamname,fixtures)
        return fixtures
    else:
        return get_offline_fixtures(teamname)

def print_fixtures(fixtures_json):
    try:
        if(fixtures_json == []):
            print("No data to display")
        for fixture in fixtures_json:
            print(fixture['Summary'])
            print("Start Time: "+ fixture['Start Time'])
            print("End Time: "+ fixture['End Time'])
            print("Venue: "+fixture['Venue']+"\n")
    except TypeError:
        print("No data to display")

def save_fixtures(teamname,fixtures_json):
    with open('data/'+teamname+'.json','w') as fixtures_file:
        json.dump(fixtures_json,fixtures_file)
    fixtures_file.close()

def get_offline_fixtures(teamname):
    try:
        fixtures_file = open('data/'+teamname+'.json','r')
        return json.load(fixtures_file)
    except FileNotFoundError:
        print("Sorry! No offline data currently available for "+teamname)
        sys.exit(0)

def main():
    teamname = input('Enter team name: ').lower()
    while(teamname.lower() != 'q'):
        fixtures_json = get_fixtures(teamname)
        print_fixtures(fixtures_json)
        teamname = input('Enter team name(Q to Quit): ').lower()

main()
    
