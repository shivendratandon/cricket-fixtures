import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import datetime

def get_credentials(relogin):
    try:
        import argparse
        flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
    except ImportError:
        flags = None

    SCOPES = 'https://www.googleapis.com/auth/calendar'
    CLIENT_SECRET_FILE = 'client_secret.json'
    APPLICATION_NAME = 'Cricket Fixtures'

    cred_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),'.credentials')
    if not os.path.exists(cred_dir):
        os.makedirs(cred_dir)
    cred_path = os.path.join(cred_dir,'credentials.json')

    store = Storage(cred_path)
    credentials = store.get()

    if not credentials or credentials.invalid or relogin:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
            print("Stored ceredentials")
    return credentials

def get_list(calendar_id):
    
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    eventsResult = service.events().list(
        calendarId=calendar_id, timeMin=now, maxResults=10, singleEvents=True,
        orderBy='startTime').execute()
    events = eventsResult.get('items', [])

    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])

def create_calendar(relogin):

    credentials = get_credentials(relogin)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    calendar = {}
    calendar['summary'] = 'Cricket Fixtures'

    created_calendar = service.calendars().insert(body=calendar).execute()
    return created_calendar['id']

def create_update_events(events_json):

    credentials = get_credentials(None)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    event_ids = []

    for event_json in events_json['fixtures']:
        if 'event_id' in event_json:
            event_id = update_event(service,events_json['calendarId'],event_json, events_json['colorId'])
        else:
            event_id = create_event(service, events_json['calendarId'], event_json, events_json['colorId'])
        event_ids.append(event_id)

    return event_ids

def create_event(service,calendar_id,event_json,color_id):

    event = {}
    event['colorId'] = color_id

    event['summary'] = event_json['Summary']
    event['location'] = event_json['Venue']

    event['start'] = {}
    event['start']['dateTime'] = event_json['Start Time']
    event['start']['timeZone'] = 'UTC'

    event['end'] = {}
    event['end']['dateTime'] = event_json['End Time']
    event['end']['timeZone'] = 'UTC'

    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    print('Event created: %s' % created_event['id'])

    return created_event['id']


def update_event(service,calendar_id,event_json,color_id):

    from googleapiclient.errors import HttpError
    try:
        event = service.events().get(calendarId=calendar_id,eventId=event_json['event_id']).execute()
    except HttpError:
        return create_event(service,calendar_id,event_json,color_id)


    changes = None

    if not 'location' in event or event['location'] != event_json['Venue']:
        event['location'] = event_json['Venue']
        changes = True
    if not 'end' in event or event['start']['dateTime'] != event_json['Start Time'] + 'Z':
        event['start']['dateTime'] = event_json['Start Time']
        changes = True
    if not 'end' in event or event['end']['dateTime'] != event_json['End Time'] + 'Z':
        event['end']['dateTime'] = event_json['End Time']
        changes = True

    if changes:
        updated_event = service.events().update(calendarId=calendar_id,eventId=event_json['event_id'],body=event).execute()
        print('Event Updated: %s' % updated_event['id'])
        return updated_event['id']
    else:
        print("No updation needed")
        return event_json['event_id']


def delete_event(service,calendar_id,event_id):
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()