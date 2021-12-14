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
from requests.api import request

#Go to https://developer.spotify.com/console/get-album-tracks/?id=&market=&limit=&offset=
#Generate new token and add to token variable in line 173 of the function main()

#returns a list of two dictionaries where the first dictionary has a key of the album title with a value of the album's popularity
#and the second dictionary contains keys of track titles from the album, each with a value of a tuple of the track's popularity and id
def get_album_and_track_popularity(token, album_id):
    album_base_url = f"https://api.spotify.com/v1/albums/{album_id}"
    headers = {"Authorization": "Bearer " + token}
    album_response = requests.get(url=album_base_url, headers=headers)
    album_json = album_response.json()
    try:
        album_title = album_json['name']
        album_popularity = album_json['popularity']
        popularity_list = []
        album_popularity_dict = {}
        track_popularity_dict = {}
        album_popularity_dict[album_title] = album_popularity
        popularity_list.append(album_popularity_dict)
        track_ids = []
        for tracks in album_json['tracks']['items']:
        #grabs a maximum of 25 tracks from the album in the Spotify api in order to put a maximum of 25 items into the database at a time
            if len(track_ids) < 25:
                track_ids.append(tracks['id'])    
        for id in track_ids:
            track_base_url = f"https://api.spotify.com/v1/tracks/{id}?limit=25"
            headers = {"Authorization": "Bearer " + token}
            track_response = requests.get(url=track_base_url, headers=headers)
            tracks_json = track_response.json()
            track_title = tracks_json['name']
            track_popularity = tracks_json['popularity']
            track_popularity_dict[track_title] = (track_popularity, id)
        popularity_list.append(track_popularity_dict)
        return popularity_list 
    except:
        print("Spotify token has expired. Generate new token to continue.")

def setUpDatabase(db_name):
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path+'/'+db_name)
    cur = conn.cursor()
    return cur, conn  

### Album database will have all the albums with the album id, album title, album popularity, number of tracks, and the average track popularity for the album
def setUpAlbumsTable(popularity_data, album_id, cur,  conn):
    for key, value in popularity_data[0].items():
        album_title = key
        album_popularity = value
    track_list = []
    track_popularity = []    
    for key, value in popularity_data[1].items():
        track_list.append(key)
        track_popularity.append(value[0])
    average_track_popularity = float(format((sum(track_popularity)/len(track_list)), '.2f'))

    cur.execute("CREATE TABLE IF NOT EXISTS Albums (album_id TEXT PRIMARY KEY, title TEXT UNIQUE, album_popularity INTEGER, track_count INTEGER, average_track_popularity INTEGER)")
    cur.execute("INSERT OR IGNORE INTO Albums (album_id, title, album_popularity, track_count, average_track_popularity) VALUES (?,?,?,?,?)", (album_id, album_title, album_popularity, len(track_list), average_track_popularity))
    conn.commit()

### Track database will have all the tracks with columns of track id, track title, track popularity, and album id
def setUpTracksTable(popularity_data, cur, conn):
    for key, value in popularity_data[0].items():
        album_title = key
    track_list = []
    track_popularity = []
    track_ids =[]    
    for key, value in popularity_data[1].items():
        track_list.append(key)
        track_popularity.append(value[0])
        track_ids.append(value[1])

    count = 0
    cur.execute("SELECT album_id FROM Albums WHERE title = ?", (album_title,))
    album_id = cur.fetchone()[0]
    cur.execute("CREATE TABLE IF NOT EXISTS Tracks (track_id TEXT PRIMARY KEY, title TEXT UNIQUE, track_popularity INTEGER, album_id TEXT)")
    for i in range(len(track_list)):
        cur.execute("INSERT OR IGNORE INTO Tracks (track_id, title, track_popularity, album_id) VALUES (?,?,?,?)", (track_ids[i], track_list[i], track_popularity[i], album_id))
    conn.commit()

def getAverageTrackPopularityCalculation(cur, file):
    albums = []
    albums_and_tracks = []
    album_popularity =[]
    cur.execute("SELECT Albums.title, Albums.track_count, Tracks.track_popularity, Albums.album_popularity FROM Tracks JOIN Albums ON Tracks.album_id = Albums.album_id")
    for row in cur:
        if row[0] not in albums:
            albums.append(row[0])
        if row[3] not in album_popularity:
            album_popularity.append(row[3])
        albums_and_tracks.append(row)
    average_pop_list =[]
    for album in albums:
        popularity_sum = 0
        for track in albums_and_tracks:
            if album == track[0]:
                popularity_sum += track[2]
                count = track[1]
        average_pop = popularity_sum/count
        if average_pop not in average_pop_list:
            average_pop_list.append(float(format(popularity_sum/count, '.2f')))
    
    data = list(zip(albums, album_popularity, average_pop_list))
    dir = os.path.dirname(file)
    out_file = open(os.path.join(dir, file), "w")
    with open(file) as f:
        csv_writer = csv.writer(out_file, delimiter=",", quotechar='"')
        csv_writer.writerow(['Album Title', 'Album Popularity', 'Average Track Popularity'])
        for x in data:
            csv_writer.writerow([x[0], x[1], x[2]])

#plots the popularity over the course of each Drake album
def createLinePlot(cur):
    title_lst = []
    popularity_lst = []
    cur.execute("SELECT title, album_popularity FROM Albums")
    for row in cur:
        title_lst.append(row[0])
        popularity_lst.append(row[1])
    title_lst.reverse()
    popularity_lst.reverse()
    
    fig, ax = plt.subplots()
    ax.plot(title_lst, popularity_lst, 'bD-')
    ax.set_xlabel('Album Title')
    ax.set_ylabel('Album Popularity') 
    ax.set_title("Popularity of Drake Albums by Popularity on Spotify")
    ax.set_xticklabels(title_lst, FontSize = '5.5', rotation = 30)
    ax.grid()
    plt.show()

#plots the album popularity compared to the average track popularity for that album
def createBarPlot(cur):
    album_titles = []
    album_popularity = []
    average_track_popularity = []
    cur.execute("SELECT title, album_popularity, average_track_popularity FROM Albums")
    for row in cur:
        album_titles.append(row[0])
        album_popularity.append(row[1])
        average_track_popularity.append(row[2])
    album_titles.reverse()
    album_popularity.reverse()
    average_track_popularity.reverse()

    fig, ax = plt.subplots()
    N = 12
    width = 0.35
    ind = np.arange(N)

    plot1 = ax.bar(ind, album_popularity, width = .35, color ='black')
    plot2 = ax.bar(ind + width, average_track_popularity, width = .35, color = 'red')

    ax.set_xticks(ind + width / 2)
    ax.set_xticklabels(album_titles, FontSize = '5.5', rotation = 30)
    ax.legend((plot1[0], plot2[0]), ('Album Popularity', 'Average Track Popularity'))
    ax.autoscale_view()
    ax.set(xlabel='Album Title', ylabel='Popularity', title="Drake Album Popularity and Average Track Popularity on Spotify" )
    ax.grid()
    plt.show()

def main():
    try:
        token = 'BQAl1rOXtzI7lE3ZHuEdwQPL56rtcQJtn6SrbqZN3CQdbogqLmwJs8QKFXDiQAUQMqTdmrCD9bnGXqEF0ErLQpIHbkRB4YZ9lsKL_2apRc0EQzAmrbYNpT808s1fvttahMXvblp-Cm2Fr7mFtg'
        artist_id = '3TVXtAsR1Inumwj472S9r4'
        base_url = f"https://api.spotify.com/v1/artists/{artist_id}/albums?market=US&limit=50"
        headers = {"Authorization": "Bearer " + token}
        response = requests.get(url=base_url, headers=headers)
        response_json = response.json()
        album_id_list = []
        album_title_list = []
        for album in response_json['items']:
            if album['name'] not in album_title_list and album['name'][-10:] != '(Explicit)' and album['name'][-8:] != '(Deluxe)' and album['name'][-17:] != '(Explicit Deluxe)' and album['name'][-15:] != "(Int'l Version)" and album['album_type'] == 'album':
                album_title_list.append(album['name'])
                album_id_list.append(album['id'])
    except:
        print("Spotify token has expired.\nGenerate new token to continue.")

    

    cur, conn = setUpDatabase('Drake.db')

    #Section 1: Uncommment lines below to start building the table from the beginning. 
    #Make sure to re-comment the lines after your first execution (after grabbing the first album) 
    #cur.execute("DROP TABLE IF EXISTS Albums")
    #cur.execute("DROP TABLE IF EXISTS Tracks")

    album_ids = []
    album_titles = []
    try:
        cur.execute("SELECT album_id, title FROM Albums")
        for row in cur:
            album_ids.append(row[0])
            album_titles.append(row[1])
    except:
        album_ids = []
    
    #removes the albums that have already been added to the database from album_id_list
    for i in range(len(album_ids)):
        try:
            album_id_list.remove(album_ids[i])
        except:
            break
    
    #adds only the next album in the album_id_list to the database after the albums that have already been added have been removed from album_id_list
    try:
        album_id = album_id_list[0]
        popularity_data = get_album_and_track_popularity(token, album_id)
        setUpAlbumsTable(popularity_data, album_id, cur, conn)
        setUpTracksTable(popularity_data, cur, conn)
    except:
        album_count =[]
        try:
            cur.execute("SELECT title FROM Albums")
            for row in cur:
                album_count.append(row)
        except:
            print('Spotify token has expired.\nGenerate new token to continue.')
        if len(album_title_list) == len(album_count):
            print("You have reached the maximum number of Drake albums.")
    try:
        getAverageTrackPopularityCalculation(cur, 'AverageTrackPopularity.txt')
    except:
        print('Spotify token has expired.\nGenerate new token to continue')

#Section 2: Uncomment the lines below to create visualitions
    #createLinePlot(cur)
    #createBarPlot(cur)

if __name__ == '__main__':
    main()