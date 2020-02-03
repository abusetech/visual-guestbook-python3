import web
#os module for filesystem functions
import os
#Unique identifier for image naming
import uuid
#Date / time stuff
from pytz import timezone
from datetime import datetime
#Global settings
from settings import *

db = web.database(dbn='sqlite', db=DB)

print ("Setting up the database, creating tables if they don't exist.")

db.query("CREATE TABLE IF NOT EXISTS comments(\
	comment_id INTEGER PRIMARY KEY UNIQUE NOT NULL,\
	image_id TEXT UNIQUE NOT NULL,\
	date INTEGER NOT NULL,\
	name TEXT NOT NULL,\
	ip_address TEXT NOT NULL,\
	approved BOOLEAN DEFAULT TRUE);")

db.query("CREATE TABLE IF NOT EXISTS post_log(\
	ip_address TEXT PRIMARY KEY UNIQUE NOT NULL,\
	banned BOOLEAN DEFAULT FALSE,\
	total_posts INTEGER DEFAULT 0,\
	last_post_date INTEGER NOT NULL);")


def unix_timestamp(dt):
	epoch = datetime(1970, 1, 1)
	if dt < epoch:
		raise ValueError('date occurs before UNIX epoch. Cannot convert to a timestamp.')
	timestamp = (dt - epoch).total_seconds()
	return int(timestamp)


#TODO: Model for the following two functions
def is_allowed_to_post(ip_address):
	params = {'ip_address' : ip_address}
	rows = db.select('post_log', params, where='ip_address=$ip_address')
	try:	
		row = rows[0]
	except IndexError:
		#Not in the post tracking list
		return True
	current_timestamp = unix_timestamp(datetime.utcnow())
	if row.last_post_date + MIN_TIME_BETWEEN_POSTS < current_timestamp and not row.banned:
		return True
	else:
		return False
	

def make_post(ip_address):
	
	'''
	Updates the post tracking list. 
	'''

	params = {'ip_address' : ip_address}
	rows = db.select('post_log', params, where='ip_address=$ip_address')
	new_time = unix_timestamp(datetime.utcnow())

	try:	
		row = rows[0]
	except IndexError:
		db.insert('post_log', 
			ip_address=ip_address, 
			last_post_date=new_time, 
			banned=False,
			total_posts=1)
		return

	new_post_count = row.total_posts + 1

	db.update('post_log',
		where='ip_address=$ip_address',
		last_post_date=new_time, 
		total_posts=new_post_count, vars=params)
	

class comment:

	'''
		Comment data class.
		name - name of commenter
		comment_id - unique comment id
		image_id - unique image idenitifer
		date - comment post date, this should be a datetime object in utc
		approved - true if the comment can be displayed on the main page
		ip_address - poster's IP address
		new - True if this is a new comment, False if the comment exists in the database.
	'''

	__columns__ = ['name', 'comment_id', 'image_id', 'date', 'approved', 'ip_address']

	def __init__(self):
		self.new = True
		self._set_defaults()

	def __init__(self, **kwargs):
		self.new = True
		for key, value in kwargs.items():
			if key in comment.__columns__ or key == 'new':
				setattr(self, key, value)
			else:
				raise KeyError('Invalid column name: ' + key)
		self._set_defaults()

	@staticmethod
	def _from_row(row):
		'''
		Returns a comment object created from a row returned by a SQL query.
		'''
		return comment(new=False, 
				name=row.name, 
				comment_id=row.comment_id,
				image_id=row.image_id, 
				date=datetime.fromtimestamp(row.date), 
				approved=row.approved,
				ip_address=row.ip_address
				)

	def _set_defaults(self):

		'''
		Sets variable defaults for this class.
		'''

		if not hasattr(self, 'comment_id'):
			#NOTE: SQLite specific: setting the comment_id field to NULL
			#will cause a unique, autoincrementing id to be created.
			#The created id will be monotonically increasing so long as
			#the number of rows created never exceeds 9223372036854775807.
			self.comment_id = None		

		if not hasattr(self, 'name'):
			self.name = ''
		
		if not hasattr(self, 'approved'):
			self.approved = True

		if not hasattr(self, 'date'):
			#default to current UNIX time
			self.date = datetime.utcnow()

		if not hasattr(self, 'image_id'):
			self.image_id = str(uuid.uuid4())

	@staticmethod
	def get_by_id(comment_id):
		'''
		get(comment_id)
		Returns a single comment given a unique id number
		'''
		
		new = False
		params = {'comment_id' : comment_id}
		rows = db.select('comments', params, where='comment_id = $comment_id')
		if not rows:
			return None
		else:
			return _from_row(rows[0])
			
	@staticmethod
	def get_list(n, **kwargs):
		'''
		Returns a list of n comment objects. If after=id is specified,
		this function returns n comments after the comment specified by id.
		If before=id is specified, this function 
		if approved=false is specified, unapproved comments will also be included.

		Rows are always returned in descending order (Most recent first)
		''' 
		print (kwargs)
		params = {'approved' : True if not 'approved' in kwargs.keys() else kwargs['approved'],
			'after' : 0 if not 'after' in kwargs.keys() else kwargs['after'],
			'before' : 0 if not 'before' in kwargs.keys() else kwargs['before'],
		}

		reverse = False

		if 'after' in kwargs.keys():
			rows = db.select('comments', params, where='approved=$approved and comment_id < $after', limit=n, order='comment_id DESC')
		elif 'before' in kwargs.keys():
			rows = db.select('comments', params, where='approved=$approved and comment_id > $before', limit=n, order='comment_id')
			reverse = True
		else:
			rows = db.select('comments', params, where='approved=$approved', limit=n, order='comment_id DESC')

		#Create comment objects
		comments = []
		for row in rows:
			comments.append(comment._from_row(row))

		if reverse:
			comments.reverse()
		
		return comments

	@staticmethod
	def get_most_recent():
		rows = db.select('comments', limit=1, order='comment_id DESC' )
		return comment._from_row(rows[0])

	@staticmethod
	def get_oldest():
		rows = db.select('comments', limit=1, order='comment_id ASC' )
		return comment._from_row(rows[0])


	def local_time(self):
		'''
		Returns the comment date as a string in the format and timezone specified in the settings. 
		'''
		tz = timezone(PYTZ_TIMEZONE)
		return self.date.astimezone(tz).strftime(DATE_FORMAT)

	def get_image_url(self):
		'''
		Returns the URL where this image will be served
		'''
		return SERVED_IMG_DIR + self.image_id + IMG_EXT

	def get_local_filename(self):
		'''
		Returns the location of the image on the local filesystem
		'''
		#TODO: This needs far more validation. Make sure image is in the correct path!
		filename = self.image_id + IMG_EXT
		path = os.path.join(LOCAL_IMG_DIR + filename)
		return path

	def delete(self):
		'''
		Deletes both the row associated with this reply and the image on the
		local filesystem.
		'''
		
		#TODO: Make sure the file we are deleting is in the images directory
		#TODO: Make sure the filename is not blank

		#Make sure we are deleting a regular file and not a directory!
		if os.path.isfile(get_local_filesystem()):
			try:
				os.remove(get_local_filesystem())
			except IOError as e:
				#We can probably safely ignore file not found errors or permission errors here.
				#Nonetheless, they should be logged.
				print ("Failed to remove " + get_local_filesystem() + " " + e)
		else:
			print ("Attempted to delete " + get_local_filesystem() + " not a regular file!")


		if self.comment_id and not self.comment_id == '':
			params = {'comment_id' : comment_id}
			db.delete('comments', params, where='comment_id=$comment_id')
		

	def save(self):

		self._set_defaults()

		if not self.ip_address:
			#We have a problem if not set. Should raise an exception here.
			pass
		
		params = { 
		'name' : self.name,
		'comment_id' : self.comment_id,
		'image_id' : self.image_id,
		'date' : unix_timestamp(self.date),
		'approved' : self.approved,
		'ip_address' : self.ip_address
		}

		if self.new:
			db.insert('comments', **params)
		else:
			db.update('comments', params, where='comment_id=$comment_id', **params)
			











