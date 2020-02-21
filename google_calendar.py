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

    SCOPES = 'https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile'
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
        reauth = True
        while flags and reauth:
            try:
                credentials = tools.run_flow(flow, store, flags)
                print("Successfully authenticated. Stored credentials.")
                reauth = False
            except:
                reauth = input("Authentication failed! Retry?(y/n)").lower() == 'y'
    return credentials

def get_logged_in_user():

    credentials = get_credentials(False)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('people', 'v1', http=http)

    user = service.people().get(resourceName='people/me', personFields='emailAddresses,names').execute()
    print("Logged in as " + user['names'][0]['displayName'] + "(" + user['emailAddresses'][0]['value'] + ")")


def get_calendar(relogin):

    credentials = get_credentials(relogin)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar in calendar_list['items']:
            if calendar['summary'] == 'Cricket Fixtures':
                return calendar['id']
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break
    return create_calendar()

def create_calendar():

    credentials = get_credentials(False)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    calendar = {}
    calendar['summary'] = 'Cricket Fixtures'

    created_calendar = service.calendars().insert(body=calendar).execute()
    return created_calendar['id']

def create_update_events(events_json):

    credentials = get_credentials(False)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    calendar_id = events_json['calendarId']
    color_id = events_json['colorId']

    event_dict = get_event_list(calendar_id)


    for event_json in events_json['fixtures']:
        if event_json['Summary'] in event_dict:
            update_event(service, calendar_id, event_dict[event_json['Summary']], event_json, color_id)
        else:
            create_event(service, calendar_id, event_json, color_id)

def delete_events(events_json):

    credentials = get_credentials(False)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    calendar_id = events_json['calendarId']

    event_dict = get_event_list(calendar_id)

    for event_json in events_json['fixtures']:
        if event_json['Summary'] in event_dict:
            delete_event(service,calendar_id,event_dict[event_json['Summary']])
            print('Event Deleted: %s' % event_json['Summary'])

def get_event_list(calendar_id):

    credentials = get_credentials(False)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    page_token = None
    event_dict = {}
    while True:
        events = service.events().list(calendarId=calendar_id, timeMin=now, pageToken=page_token).execute()
        for event in events['items']:
            event_dict[event['summary']] = event['id']
        page_token = events.get('nextPageToken')
        if not page_token:
            break
    return event_dict

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

    event['reminders'] = {}
    event['reminders']['useDefault'] = False
    event['reminders']['overrides'] = [
      {'method': 'popup', 'minutes': 10}
    ]

    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    print('Event created: %s' % created_event['summary'])


def update_event(service,calendar_id,event_id,event_json,color_id):

    from googleapiclient.errors import HttpError
    try:
        event = service.events().get(calendarId=calendar_id,eventId=event_id).execute()
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
    if event['reminders']['useDefault'] == True:
        event['reminders']['useDefault'] = False
        event['reminders']['overrides'] = [
            {'method': 'popup', 'minutes': 10}
        ]
        changes = True

    if changes:
        updated_event = service.events().update(calendarId=calendar_id,eventId=event_id,body=event).execute()
        print('Event Updated: %s' % updated_event['summary'])
    else:
        print("%s: No updation needed" % event_json['Summary'])

def delete_event(service,calendar_id,event_id):
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()