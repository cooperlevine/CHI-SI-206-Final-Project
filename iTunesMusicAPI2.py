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

# generate dictionary with artists and song IDs, 
#dictionary is artist and key inside dict is also artiist but value is count
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

    id_list_sorted = []
    index = 0
    for id1 in ids:
        for id2 in id_list:
            if id1 == id2 and id2 not in id_list_sorted:
                id_list_sorted.append(id2)
    for id in ids:
        if id in id_list_sorted:
            index +=1 

    for i in range(len(ids))[index:index + 25]:
        cur.execute("CREATE TABLE IF NOT EXISTS Features (track_id INTEGER PRIMARY KEY, title TEXT UNIQUE, artist TEXT, features TEXT)")
        cur.execute("INSERT OR IGNORE INTO Features (track_id, title, artist, features) VALUES (?,?,?,?)", (ids[i], tracks[i], artists[i], features[i][0]))
    conn.commit()

def getFeatureCount(cur, file):
    cur.execute("SELECT Features.features FROM Features")
    feat = []
    for row in cur:
        ftr = row[0]
        feat.append(ftr)
    
    features = []
    for feature in feat:
        new_ftrs = cleanName(feature)
        if new_ftrs != 'N':
            if '(' in new_ftrs[0]:
                try:
                    clean_lst = cleanName(new_ftrs[0][1:].split('feat.')[1])
                except:
                    clean_lst = cleanName(new_ftrs[0][1:])
                for name in clean_lst:
                    features.append(name)
            else:
                features.append(new_ftrs[0])
        else:
            features.append(new_ftrs)

    dict = {}
    for artist in features:
        if artist not in dict:
            dict[artist] = 1
        else:
            dict[artist] += 1
    del dict['Drake']
    del dict['N']

    #Writing CSV File
    dir = os.path.dirname(file)
    out_file = open(os.path.join(dir, file), "w")
    with open(file) as f:
        csv_writer = csv.writer(out_file, delimiter=",", quotechar='"')
        csv_writer.writerow(['Artist', 'Count'])
        for key, value in dict.items():
            csv_writer.writerow([key,value])

def setUpVisualization(cur):
    cur.execute("SELECT Features.features FROM Features")
    feat = []
    for row in cur:
        ftr = row[0]
        feat.append(ftr)
    
    features = []
    for feature in feat:
        new_ftrs = cleanName(feature)
        if new_ftrs != 'N':
            if '(' in new_ftrs[0]:
                try:
                    clean_lst = cleanName(new_ftrs[0][1:].split('feat.')[1])
                except:
                    clean_lst = cleanName(new_ftrs[0][1:])
                for name in clean_lst:
                    features.append(name)
            else:
                features.append(new_ftrs[0])
        else:
            features.append(new_ftrs)

    dict = {}
    for artist in features:
        if artist not in dict:
            dict[artist] = 1
        else:
            dict[artist] += 1
    del dict['Drake']
    del dict['N']
    
    artist_list = []
    count_list =[]
    for k, v in dict.items():
        artist_list.append(k)
        count_list.append(v)

    fig, ax = plt.subplots()
    N = 12
    width = 0.35
    ind = np.arange(N)

    plot = ax.bar(artist_list, count_list, width = .35, color ='green')

    ax.set_xticklabels(artist_list, FontSize = '5', rotation = 50)
    ax.autoscale_view()
    ax.set(xlabel='Artist Name', ylabel='Count of Features with Drake', title="Number of Times Artists Have Worked With Drake" )
    ax.grid()
    plt.show()

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
    cur, conn = setUpDatabase("Drake.db")

    id_list = []
    try:
        cur.execute("SELECT Features.track_id FROM Features")
        for row in cur:
            id_list.append(row[0])
    except:
        id_list =[]
    
    setUpFeatures(data, id_list, cur, conn)
    pprint(data)
    getFeatureCount(cur, "featureFile.txt")

#Uncomment in order to see visualization
    setUpVisualization(cur)


if __name__ == '__main__':
    main()