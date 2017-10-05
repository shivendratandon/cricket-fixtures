import requests
import json
import io
import sys
from datetime import datetime,timezone
import os
import google_calendar

DATA_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)),'data')

def download_fixtures_file(teamname):
    url_file = open(os.path.join(DATA_FOLDER,'metadata.json'),'r')
    url_data = json.load(url_file)
    try:
        url = url_data['url'].replace('id',str(url_data['teams'][teamname]['id']))
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

def get_datetime_list(fixture_data,value_to_get):
    dt_string_list = get_list(fixture_data,value_to_get)
    date_format = '%Y%m%dT%H%M%SZ'
    datetime_list=[]
    for dt_string in dt_string_list:
        datetime_list.append(datetime.strptime(dt_string,date_format).isoformat('T'))
    return datetime_list

def save_fixtures(teamname,fixtures_json):

    saved_fixtures_json = json.load(open(os.path.join(DATA_FOLDER,teamname+'.json'),'r'))

    event_id_dict = {}

    for saved_fixture in saved_fixtures_json:
        if 'event_id' in saved_fixture:
            event_id_dict[saved_fixture['Summary']] = saved_fixture['event_id']

    for i in range(len(fixtures_json)):
        if fixtures_json[i]['Summary'] in event_id_dict:
            fixtures_json[i]['event_id'] = event_id_dict[fixtures_json[i]['Summary']]

    with open(os.path.join(DATA_FOLDER,teamname+'.json'),'w') as fixtures_file:
        json.dump(fixtures_json,fixtures_file)
    fixtures_file.close()
    return fixtures_json

def get_offline_fixtures(teamname):
    try:
        fixtures_file = open(os.path.join(DATA_FOLDER,teamname+'.json'),'r')
        return json.load(fixtures_file)
    except FileNotFoundError:
        print("Sorry! No offline data currently available for "+teamname)
        sys.exit(0)

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
            fixture['Start Time'] = start_times[i]
            fixture['End Time'] = end_times[i]
            fixture['Venue'] = venues[i]
            fixtures.append(fixture)
        fixtures = save_fixtures(teamname,fixtures)
        return fixtures
    else:
        return get_offline_fixtures(teamname)

def print_fixtures(fixtures_json):
    try:
        if(fixtures_json == []):
            print("No data to display")
        for fixture in fixtures_json:
            print(fixture['Summary'])
            date_format = '%Y-%m-%dT%H:%M:%S'
            print("Start Time: "+ datetime.strptime(fixture['Start Time'],date_format).replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%d %B %Y, %I:%M %p"))
            print("End Time: "+ datetime.strptime(fixture['End Time'],date_format).replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%d %B %Y, %I:%M %p"))
            print("Venue: "+fixture['Venue']+"\n")
    except TypeError:
        print("No data to display")

def google_calendar_init(fixtures_json,teamname):
    metadata_file = open(os.path.join(DATA_FOLDER, 'metadata.json'), 'r')
    metadata = json.load(metadata_file)

    fixture_data = {}
    fixture_data['colorId'] = metadata['teams'][teamname]['calendar_color']
    fixture_data['fixtures'] = fixtures_json

    try:
        fixture_data['calendarId'] = metadata['calendarId']
        google_calendar.get_logged_in_user()
        if input('Login as another user?(y/n)').lower() == 'y':
            metadata['calendarId'] = google_calendar.get_calendar(True)
            fixture_data['calendarId'] = metadata['calendarId']
    except KeyError:
        metadata['calendarId'] = google_calendar.get_calendar(None)
        fixture_data['calendarId'] = metadata['calendarId']

    with open(os.path.join(DATA_FOLDER, 'metadata.json'), 'w') as metadata_file:
        json.dump(metadata, metadata_file)

    return fixture_data


def main():
    teamname = input('Enter team name: ').lower()
    while(teamname.lower() != 'q'):
        fixtures_json = get_fixtures(teamname)
        print_fixtures(fixtures_json)
        calendar_choice = input('GOOGLE CALENDAR:\n' +
                                '1. Add to/Update Google Calendar\n' +
                                '2. Delete from Google Calendar\n' +
                                'Enter Choice(1,2) or press Enter to continue')
        if calendar_choice == '1' or calendar_choice == '2':
            events_json = google_calendar_init(fixtures_json,teamname)
            if calendar_choice == '1':
                google_calendar.create_update_events(events_json)
            elif calendar_choice == '2':
                google_calendar.delete_events(events_json)

        teamname = input('Enter team name(Q to Quit): ').lower()

main()
    
