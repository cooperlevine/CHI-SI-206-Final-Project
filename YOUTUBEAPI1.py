import requests
import json
import sys
import os
import matplotlib
import sqlite3
import unittest
import csv
import numpy as np
import matplotlib.pyplot as plt
from pprint import pprint
from requests.api import request
import urllib.parse


apikey = 'AIzaSyBUWJV2fjUdbNxa-LRmSJU7fI39oQmCJws'
spotifyKey = 'BQD2FAeuLvaMC3rBL-JQmN_m9I5ecb3AwJAhrrPQsXQxOpLBDZj_N2kP52hjQZ7aGGQ26Va3gfT_sDn1BEAt7IrGEnWHKPjA0npSJCfRJurLJ4kY8fSmsyhMiUWe_T2mBApTAntg_84'

listid = 'PLweBOpkJk2GAYgEu72fFosH6M8_6HmftN'
url = f'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId={listid}&key={apikey}&maxResults=50'

def inDB(song):
    return False

def setUpDatabase(db_name):
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path+'/'+db_name)
    cur = conn.cursor()
    return cur, conn

def addLikes(cur, file):
    cur.execute("SELECT Tracks.likes, Tracks.comments FROM Tracks")
    popularity_list = []
    for row in cur:
        like = int(row[0])
        comment = int(row[1])
        sum = like + comment
        popularity_list.append(sum)   
      
    dir = os.path.dirname(file)
    out_file = open(os.path.join(dir, file), "w")
    with open(file) as f:
        csv_writer = csv.writer(out_file, delimiter=",", quotechar='"')
        csv_writer.writerow(['Number of Likes and Comments'])
        for num in popularity_list:
            csv_writer.writerow([str(num)])

# gets album of song from Spotify after searching for name
def get_album(name):
    album_base_url = f"https://api.spotify.com/v1/search?q={urllib.parse.quote(name)}&type=track"
    headers = {"Authorization": "Bearer " + spotifyKey}
    req = requests.get(url=album_base_url, headers=headers)
    try:
        tracks = req.json()['tracks']['items']
        if len(tracks) == 0: return ''
        for track in tracks:
            if track['album']['artists'][0]['name'] == 'Drake':
                return track['album']['name']
    except:
        pprint(req.json()['tracks']['items'])
        raise

# gets the song title from the youtube video title
def extractName(name):
    parts = name.split('Drake -')
    if len(parts) > 1: name = parts[1]
    parts = name.split('Drake-')
    if len(parts) > 1: name = parts[1]
    parts = name.split('feat')
    if len(parts) > 1: name = parts[0]
    parts = name.split('ft.')
    if len(parts) > 1: name = parts[0]
    parts = name.split('(')
    if len(parts) > 1: name = parts[0]
    return name.strip()

# get all of the data from each video in the playlist
def getItems():
    nextPageToken = ''
    items = []

    # request 50 videos (you cna only request 50 videos max at a time)
    resp = requests.get(url)
    json = resp.json()
    for item in json['items']:
        items.append(item)
    
    # while there are more videos, request them and add the video information to the list
    while 'nextPageToken' in json:
        nextPageToken = json['nextPageToken']
        resp = requests.get(url + '&pageToken=' + nextPageToken)
        json = resp.json()
        for item in json['items']:
            items.append(item)
    return items

# extract wanted information from each video
def getVideoData(items):
    data = []
    for i in items:
        # get title and id, request video statistics for the specific video
        title = i['snippet']['title']
        album = get_album(extractName(title))
        id =  i['contentDetails']['videoId']
        stats = requests.get(f'https://www.googleapis.com/youtube/v3/videos?part=statistics&key={apikey}&id={id}&limit=200').json()

        # if the video is private
        if len(stats['items']) == 0: continue

        # get the views, likes, dislikes, and # of comments, and then append them to the data array
        items = stats['items'][0]['statistics']
        views = items['viewCount']
        likes = items['likeCount'] if 'likeCount' in items else 0
        dislikes = items['dislikeCount'] if 'dislikeCount' in items else 0
        comments = items['commentCount'] if 'commentCount' in items else 0
        data.append({
            "title": extractName(title),
            "album": album,
            "id": id,
            "views": views,
            "likes": likes,
            "dislikes": dislikes,
            "comments": comments,
        })
    return data

### for the databses: one database will have all the albums with the album id, album popularity, number of tracks, and maybe the average track popularity for the album
### track id - title - album - views - likes - dislikes - comments
def setUpYouTubeTable(data, track_ids, cur,  conn):
    cur.execute("CREATE TABLE IF NOT EXISTS Tracks (track_id TEXT PRIMARY KEY, title TEXT UNIQUE, album TEXT, views INTEGER, likes INTEGER, dislikes INTEGER, comments INTEGER)")

    trackids = []
    trackids_db = []
    index = 0
    for item in data:
        trackids.append(item['id'])   
    for id1 in trackids:
        for id2 in track_ids:
            if id1 == id2 and id2 not in trackids_db:
                trackids_db.append(id2)
    for id in trackids:
        if id in trackids_db:
            index += 1
    
    
    for item in data[index:index+25]:   
        cur.execute("INSERT OR IGNORE INTO Tracks (track_id, title, album, views, likes, dislikes, comments) VALUES (?,?,?,?,?,?,?)", (item['id'], item['title'], item['album'], item['views'], item['likes'], item['dislikes'], item['comments']))
    conn.commit()

def makeLinePlot(cur):
    title_lst = []
    pop_lst = []
    cur.execute("SELECT title, likes FROM Tracks ORDER BY likes")
    for row in cur:
        title_lst.append(row[0])
        pop_lst.append(row[1])
    title_lst.reverse()
    pop_lst.reverse()
    
    fig, ax = plt.subplots()
    ax.plot(title_lst, pop_lst, 'bD-')
    ax.set_xlabel('Song Title')
    ax.set_ylabel('Song Popularity') 
    ax.set_title("Popularity of Drake Songs by Likes on YouTube")
    ax.set_xticklabels(title_lst, FontSize = '7', rotation = 30)
    ax.grid()
    plt.show()

def main():
    items = getItems()
    data = getVideoData(items)
    cur, conn = setUpDatabase('YoutubeTracks.db')
    #cur.execute("DROP TABLE IF EXISTS Tracks")
    try:
        track_ids = []
        cur.execute("SELECT track_id FROM Tracks")
        for row in cur:
            track_ids.append(row[0])
    except:
        track_ids = []
    setUpYouTubeTable(data, track_ids, cur, conn)
    pprint(data)
    addLikes(cur, "likes.txt")

 #Section 2: Uncomment the line below to create the visualition
    makeLinePlot(cur)  

if __name__ == '__main__':
    main()