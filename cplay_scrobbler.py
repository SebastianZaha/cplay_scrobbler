#!/usr/bin/env python
# -*- python -*-

"""
 cplay plugin that scrobbles your listened tracks to last.fm

 (c) 2010 Sebastian Zaha <grimdonkey@gmail.com>; 
 http://sebi.tla.ro/cplay_scrobbler

 Distributed under the terms of the MIT license.
"""

USERNAME = 'YOUR_USERNAME'
PASSWORD = 'YOUR_PASSWORD'


import scrobbler
from datetime import datetime


global playing
playing = None


def read_metadata(pathname):
    """ Read artist and title information from the file. Partially duplicated from the cplay code, 
        but the get_tag method in cplay was un-reusable.
    """
    if re.compile("^http://").match(pathname) or not os.path.exists(pathname): return None
    
    try:
        if re.compile(".*\.ogg$", re.I).match(pathname):
            import ogg.vorbis
            vf = ogg.vorbis.VorbisFile(pathname)
            vc = vf.comment()
            tags = vc.as_dict()
        elif re.compile(".*\.mp3$", re.I).match(pathname):
            import ID3
            vc = ID3.ID3(pathname, as_tuple=1)
            tags = vc.as_dict()
        else:
            return None

        artist = tags.get("ARTIST", [""])[0]
        title = tags.get("TITLE", [""])[0]

        import codecs
        if artist and title:
            return {'artist': codecs.latin_1_encode(artist)[0], 'track': codecs.latin_1_encode(title)[0]}
        else:
            return None
    except: return None


def _play(application, entry, offset = 0):
    """ Method called whenever Application.play is supposed to be called """
    global playing
    
    application._play(entry, offset)
    
    if offset > 0: return
    
    if playing: lastfm_playing()

    meta = read_metadata(entry.pathname)
    if meta:
        meta.update({'time': int(time.mktime(datetime.now().timetuple())), 
                     'submittable': False,
                     'length': None})
        playing = meta

# Hook our method to be called instead of Application.play. We'll call Application.play ourselves.
Application._play = Application.play; Application.play = _play


def _set_position(player, offset, length, values):
    """ Method called whenever Player.set_position is supposed to be called i.e. once every second
        whenever a track is playing. 
    """
    global playing
    
    player._set_position(offset, length, values)
    
    if playing:
        # Is this the first 'tick' in this song? Then set the track length (we are not able to 
        # find it when _play is called). Also submit the now_playing request to last.fm.
        if not playing['length']:
            playing['length'] = player.length
            lastfm_now_playing()
        # We can submit if we exceeded half the current track's length or 240 seconds        
        if (not playing['submittable']) and ((offset > (player.length / 2)) or offset > 240):
            playing['submittable'] = True

# Hook our method to be called instead of Player.set_position. We'll call Player.set_position ourselves.
Player._set_position = Player.set_position; Player.set_position = _set_position


def lastfm_login():
    try:
        scrobbler.login(USERNAME, PASSWORD, True)
    except: pass


def lastfm_playing():
    try:
        if playing and playing['submittable']: 
            if not scrobbler.SESSION_ID: lastfm_login()
            scrobbler.submit(playing['artist'], playing['track'], playing['time'], 
                             length = playing['length'], autoflush = True)
    except: pass


def lastfm_now_playing():
    try:
        if not scrobbler.SESSION_ID: lastfm_login()
        scrobbler.now_playing(playing['artist'], playing['track'], playing['length'])
    except: pass
