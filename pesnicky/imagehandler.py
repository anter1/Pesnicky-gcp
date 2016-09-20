#!/usr/bin/env python

# [START imports]
import os
import urllib2
import base64

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.api import images as images_api

import jinja2
import webapp2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
# [END imports]

def image_all_key():
    """Constructs a Datastore key for a Image entity.

    """
    return ndb.Key('Images', 'all')


class Image(ndb.Model):
    """A main model for representing an individual Guestbook entry."""
    name = ndb.StringProperty()
    data = ndb.BlobProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
# [END greeting]


# [START main_page]
class MainPage(webapp2.RequestHandler):

    def get(self):
        images_query = Image.query(
            ancestor=image_all_key()).order(Image.name)
        images = images_query.fetch()

        for image in images:
            image.dataurl = "data:image/png;base64," + base64.b64encode(image.data)

        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template_values = {
            'user': user,
            'images': images,
            'url': url,
            'url_linktext': url_linktext,
        }

        template = JINJA_ENVIRONMENT.get_template('images.html')
        self.response.write(template.render(template_values))
# [END main_page]


# [START guestbook]
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

        self.redirect('/images')
        
class DeleteImage(webapp2.RequestHandler):
    
    def post(self):
        urlsafekey = self.request.get('image_key')
        image_key = ndb.Key(urlsafe=urlsafekey)
        image_key.delete()
        
        self.redirect('/images')
        
# [END guestbook]


# [START app]
app = webapp2.WSGIApplication([
    ('/images', MainPage),
    ('/images/new', NewImage),
    ('/images/delete', DeleteImage)
], debug=True)
# [END app]
