#!/usr/bin/env python

import os
import urllib2
import base64

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.api import images as images_api

from webapp2_extras import json

import jinja2
import webapp2
from webapp2 import Route

NEW_IMAGE = 'new_image'
DELETE_IMAGE = 'delete_image'
IMAGES_LIST = 'images_list'
SONGS_LIST = 'songs_list'
NEW_SONG = 'new_song'
DELETE_SONG = 'delete_song'
EDIT_SONG = 'edit_song'
GENERATE_JSON = 'generate_json'

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

def image_all_key():
    """Constructs a Datastore key for a Image entity.

    """
    return ndb.Key('Images', 'all')

def songs_all_key():
    return ndb.Key('Songs', 'all')

class Image(ndb.Model):
    name = ndb.StringProperty()
    data = ndb.BlobProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)

    def data_url(self):
        return "data:image/png;base64," + base64.b64encode(self.data)
    
class Song(ndb.Model):
    name = ndb.StringProperty()
    image = ndb.KeyProperty(kind=Image)
    notes = ndb.StringProperty()
    
def master_page_params(request_uri):
    user = users.get_current_user()
    if user:
        url = users.create_logout_url(request_uri)
        url_linktext = 'Logout'
    else:
        url = users.create_login_url(request_uri)
        url_linktext = 'Login'

    return {
        'url': url,
        'url_linktext': url_linktext
    }

class ImagesListPage(webapp2.RequestHandler):
    def get(self):
        images_query = Image.query(
            ancestor=image_all_key()).order(Image.name)
        images = images_query.fetch()

        template_values = master_page_params(self.request.uri)

        template_values.update({
            'images': images,
            'new_image_url': self.uri_for(NEW_IMAGE),
            'delete_image_url': self.uri_for(DELETE_IMAGE),
        })

        template = JINJA_ENVIRONMENT.get_template('images.html')
        self.response.write(template.render(template_values))

class NewImage(webapp2.RequestHandler):

    def post(self):
        image = Image(parent=image_all_key())

        image.name = self.request.get('image_name')
        
        url = self.request.get('image_url')
        resp = urllib2.urlopen(url)
        image_data = resp.read()
        
        img = images_api.Image(image_data=image_data)
        img.resize(width=200, height=200)
        thumbnail_data = img.execute_transforms(output_encoding=images_api.PNG)
        
        image.data = thumbnail_data
        
        image.put()

        self.redirect(self.uri_for(IMAGES_LIST))
        
class DeleteImage(webapp2.RequestHandler):
    def post(self):
        urlsafekey = self.request.get('image_key')
        image_key = ndb.Key(urlsafe=urlsafekey)
        image_key.delete()
        
        self.redirect(self.url_for(IMAGES_LIST))

class SongsListPage(webapp2.RequestHandler):
    def get(self):
        songs_query = Song.query(
            ancestor=songs_all_key()).order(Song.name)
        songs = songs_query.fetch()
        
        images = Image.query(ancestor=image_all_key()).order(Image.name).fetch(projection=[Image.name])
        
        template_values = master_page_params(self.request.uri)

        template_values.update({
            'songs': songs,
            'images': images,
            'new_song_url': self.uri_for(NEW_SONG),
            'delete_song_url': self.uri_for(DELETE_SONG),
            'edit_song_url': self.uri_for(EDIT_SONG),
        })

        template = JINJA_ENVIRONMENT.get_template('songs.html')
        self.response.write(template.render(template_values))
        
class NewSong(webapp2.RequestHandler):
    def post(self):
        if (self.request.get('song_key') == ''):
            song = Song(parent=songs_all_key())
        else:
            urlsafekey = self.request.get('song_key')
            song_key = ndb.Key(urlsafe=urlsafekey)        
            song = song_key.get();

        song.name = self.request.get('song_name')
        song_image_urlsafekey = self.request.get('song_image');
        song.image = ndb.Key(urlsafe=song_image_urlsafekey)
        song.notes = self.request.get('song_notes')

        song.put()

        self.redirect(self.url_for(SONGS_LIST))
        
class DeleteSong(webapp2.RequestHandler):
    def post(self):
        urlsafekey = self.request.get('song_key')
        song_key = ndb.Key(urlsafe=urlsafekey)
        song_key.delete()
        
        self.redirect(self.url_for(SONGS_LIST))

class EditSong(webapp2.RequestHandler):
    def get(self):
        urlsafekey = self.request.get('song_key')
        song_key = ndb.Key(urlsafe=urlsafekey)
        
        song = song_key.get();

        images = Image.query(ancestor=image_all_key()).order(Image.name).fetch(projection=[Image.name])

        template_values = master_page_params(self.request.uri)

        template_values.update({
            'song': song,
            'images': images,
            'new_song_url': self.url_for(NEW_SONG)
        })

        template = JINJA_ENVIRONMENT.get_template('edit_song.html')
        self.response.write(template.render(template_values))

class GenerateJson(webapp2.RequestHandler):
    def get(self):
        image_list = Image.query(ancestor=image_all_key()).order(Image.name).fetch()
        
        images = dict( (image.key, image) for image in image_list)
        
        songs = Song.query(ancestor=songs_all_key()).order(Song.name).fetch()

        song_list = []
        for song in songs:
            song_list.append({
                'name': song.name,
                'image': base64.b64encode(images[song.image].data),
                'notes': song.notes
            })
        
        result = {'songs': song_list}
        
        self.response.content_type = 'application/json'
        self.response.write(json.encode(result))
        
        
app = webapp2.WSGIApplication([
    Route('/json', GenerateJson, GENERATE_JSON),
    Route('/', SongsListPage, SONGS_LIST),
    Route('/songs/new', NewSong, NEW_SONG),
    Route('/songs/delete', DeleteSong, DELETE_SONG),
    Route('/songs/edit', EditSong, EDIT_SONG),
    Route('/images', ImagesListPage, IMAGES_LIST),
    Route('/images/new', NewImage, NEW_IMAGE),
    Route('/images/delete', DeleteImage, DELETE_IMAGE),
], debug=True)
