#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import wsgiref.handlers
import os
import urllib
import xml.dom
import xml.dom.minidom
import datetime

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import db
from urlparse import urljoin

main_url = None

class Item():
	id = 0
	date = datetime.datetime.now()
	test =""

class Log(db.Model):
	author = db.UserProperty()
	spec = db.StringProperty(multiline=True)
	content = db.StringProperty(multiline=True)
	date = db.DateTimeProperty(auto_now_add=True)

class MainHandler(webapp.RequestHandler):
	def get(self):
		global main_url 
		main_url = self.request.uri
		if users.get_current_user():
			login_url = users.create_logout_url(main_url)
			url_linktext = 'User(' + users.get_current_user().nickname() + '):Logout'
		else:
			login_url = users.create_login_url(self.request.uri)
			url_linktext = 'Login'
		#method= 'initial'

		items = []
		template_values = {
			'items' : items,
			'url': login_url,
			'url_linktext': url_linktext,
			#'method': method,
			}
		path = os.path.join(os.path.dirname(__file__), 'index.html')
		self.response.out.write(template.render(path, template_values))

class FetchHandler(webapp.RequestHandler):
	def post(self):
		global main_url 
		if main_url == None:
			main_url = urljoin(self.request.uri, './')
		if users.get_current_user():
			login_url = users.create_logout_url(main_url)
			url_linktext = 'User(' + users.get_current_user().nickname() + '):Logout'
		else:
			login_url = users.create_login_url(main_url)
			url_linktext = 'Login'
			
		urls = self.request.get('spec')
		#method = self.request.get('value')
		items = []
		for url in urls.strip().split(" "):
			if url != "":
				item0 = item(id(url))
				if item0 != None:
					items.append(item0)
		template_values = {
			'items' : items,
			'url': login_url,
			'url_linktext': url_linktext,
			#'method': method,
			}
		
		log = Log()
		if users.get_current_user():
			log.author = users.get_current_user()
		log.spec = urls
		contents = str(map(lambda x: " http://twitter.com/" + x.user + "/statuses/" + x.id, items)) 
		log.content = contents.strip()
		log.put()
		
		path = os.path.join(os.path.dirname(__file__), 'index.html')
		self.response.out.write(template.render(path, template_values))

class PrintHandler(webapp.RequestHandler):
	def post(self):
		keyword =self.request.get('keyword').encode('utf-8')
		url = "http://search.twitter.com/search.atom?q=" + urllib.quote(keyword) + "&locale=ja&rpp=30"
		result = urlfetch.fetch(url)
		
		log = Log()
		if users.get_current_user():
			log.author = users.get_current_user()
		log.spec = self.request.get('keyword')
		log.content = ""
		
		if (result.status_code != 200) :
			log.content = str(result.status_code)
			log.put()
			template_values = {
				'keyword' : keyword + ' ( status_code: ' + log.content + ') ',
				'itemsL' : [],
				'itemsR' : [],
				}
			path = os.path.join(os.path.dirname(__file__), 'poster.html')
			self.response.out.write(template.render(path, template_values))
			return None
		entries = xml.dom.minidom.parseString(result.content).getElementsByTagName('entry')
		#itemsL = map (getitem, entries[:20])
		itemsL= []
		for entry in entries[:15]:
			if entry != "":
				item0 = getitem(entry)
				if item0 != None:
					itemsL.append(item0)
		itemsR = map (getitem, entries[15:])
		#itemsR =[]
		template_values = {
			'keyword' : keyword, # + ' (' + str(len(entries)) + ') ',
			'itemsL' : itemsL,
			'itemsR' : itemsR,
			}
		path = os.path.join(os.path.dirname(__file__), 'poster.html')
		self.response.out.write(template.render(path, template_values))
		
		log.put()
		
class LogHandler(webapp.RequestHandler):
	def get(self):
		global main_url 
		main_url = self.request.uri
		if users.get_current_user():
			login_url = users.create_logout_url(main_url)
			url_linktext = 'User(' + users.get_current_user().nickname() + '):Logout'
		else:
			login_url = users.create_login_url(self.request.uri)
			url_linktext = 'Login'
		
		log_query = Log.all().order('-date')
		logs = log_query.fetch(20)
		
		template_values = {
			'logs' : logs,
			'size' : log_query.count(1000),
			'url': login_url,
			'url_linktext': url_linktext,
			}
		path = os.path.join(os.path.dirname(__file__), 'log.html')
		self.response.out.write(template.render(path, template_values))
		
def id(url): # url id or http://twitter.com/username/statuses/id  
	ids = url.rsplit("/")	
	id = ids[len(ids)-1] 
	return id.strip()
	
def item(id):
	url = "http://twitter.com/statuses/show/" + id + ".xml"
	result = urlfetch.fetch(url)
	#if not result : return None
	if (result.status_code != 200) : return None
	dom = xml.dom.minidom.parseString(result.content)
	status = dom.getElementsByTagName('status')[0]
	item = Item()
	item.id = id
	#item.date = datetime.datetime.fromtimestamp(status.getElementsByTagName('created_at')[0].firstChild.data)
	item.date = status.getElementsByTagName('created_at')[0].firstChild.data
	item.text = status.getElementsByTagName('text')[0].firstChild.data.encode('utf-8')
	item.image = status.getElementsByTagName('profile_image_url')[0].firstChild.data
	item.user = status.getElementsByTagName('screen_name')[0].firstChild.data
	return item

def getitem(entry):
	id = entry.getElementsByTagName('id')[0].firstChild.data
	id = id.split(',')[1]
	id = id.split(':')[1]
	# Originally item0 is made from each entry fetched by this ID
	#item0 = item(id)
	#if item0 != None:
	#	return item0
	item0 = 	Item()
	item0.id = id
	item0.date = entry.getElementsByTagName('updated')[0].firstChild.data
	item0.text = entry.getElementsByTagName('content')[0].firstChild.data.encode('utf-8')
	#item0.image = '/images/alternate_logo.png'
	item0.image = entry.getElementsByTagName('link')[1].attributes["href"].value
	item0.user = entry.getElementsByTagName('name')[0].firstChild.data.split('(')[0].strip()
	return item0

def main():
	application = webapp.WSGIApplication([('/', MainHandler),('/fetch', FetchHandler),
	                                      ('/print', PrintHandler),
	('/log', LogHandler)],
                                         debug=True)
	wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
	main()
