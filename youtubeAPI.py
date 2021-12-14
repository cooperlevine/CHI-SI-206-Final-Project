import requests 
import json 
import sys
import os
import matplotlib
import sqlite3
import unittest
import csv
import re
import numpy as np
import matplotlib.pyplot as plt
from pprint import pprint

def getAlbumfeatues(artist):
    base_url = f"https://itunes.apple.com/search?term={artist}&entity=song&attribute=allArtistTerm&limit=200"
    response = requests.get(url=base_url)
    json_response = response.json()
    return json_response

#gets artists from the title of a song
def cleanName(name):
    # split artists by "," and "&", then make sure there are no hanging characters or spaces
    names = name.replace('&', ',').split(',')
    for i in range(len(names)):
        names[i] = names[i].split('[')[0].replace(')', '').replace(']', '').strip() 
    return names

#get all artists from a song
def getArtists(song):
    ret = set(cleanName(song['artistName']))
    others = song['trackName']
    if 'feat.' in others:
        for name in cleanName(others.split('feat.')[1]):
            ret.add(name)
    return ret

# generate dictionary with artists and song IDs
def getData(json):
    songs = json['results']
    artists = {}
    songIDs = {}
    for song in songs:
        #GETTING ARTISTS
        a = getArtists(song)
        for artist in a:
            if artist not in artists:
                artists[artist] = 0
            artists[artist] += 1
        
        # GET SONG / SONG ID
        # "feat." in song['trackName'] and 'Drake' not in song['trackName']:
        songIDs[song['trackName']] = [song['trackId'], song['artistName']]
    
    del artists['Drake'] # making sure it's not counting Drake since it's his songs
    #print(len(songIDs))
    return {
        'artists': artists,
        'ids': songIDs
    }

def setUpDatabase(db_name):
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path+'/'+db_name)
    cur = conn.cursor()
    return cur, conn  

def setUpFeatures(data, id_list, cur, conn):
    artists = []
    tracks = []
    ids = []
    features = []
    reg_expression = r'(\(.+\))'
    for track, value in data['ids'].items():
        tracks.append(track.split('(')[0])
        artists.append(value[1])
        ids.append(value[0])
        if 'feat.' in track:
            feature = re.findall(reg_expression, track)
            features.append(feature)
        else:
            features.append('None')
    
    index = 0
    for id in ids:
        if str(id) in id_list:
            index += 1

    '''
    try:
        cur.execute("SELECT track_id FROM Features WHERE track_id = (SELECT MAX(track_id) FROM Features)")
        start = cur.fetchone()[0] + 1
    except:
        start = 0
    '''
    for i in range(len(ids))[index:index + 25]:
        cur.execute("CREATE TABLE IF NOT EXISTS Features (track_id INTEGER PRIMARY KEY, title TEXT UNIQUE, artist TEXT, features TEXT)")
        cur.execute("INSERT OR IGNORE INTO Features (track_id, title, artist, features) VALUES (?,?,?,?)", (ids[i], tracks[i], artists[i], features[i][0]))
    conn.commit()

def main():
    json = getAlbumfeatues("drake")
    data = getData(json)
    '''
        data = {
            artsits: {
                name: count, ...
            }
            ids: {
                title: id, ...
            }
        }
    '''
    cur, conn = setUpDatabase('Features.db')
    #cur.execute("DROP TABLE IF EXISTS Features")

    id_list = []
    try:
        cur.execute("SELECT track_id FROM Features")
        for row in cur:
            id_list.append(row[0])
    except:
        id_list = []
    


    setUpFeatures(data, id_list, cur, conn)
    pprint(data)


if __name__ == '__main__':
    main()