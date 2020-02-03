#Visual guestbook settings

#Date format to display on the page
DATE_FORMAT = '%A, %d %B, %Y, %I:%M%p'
#(Dates are stored as UNIX timestamps in the database)

#Timezone to use when displaying the page
PYTZ_TIMEZONE = 'Canada/Eastern'

#Maximum size of raw image data (bytes)
MAX_IMAGE_SIZE = 200000
IMAGE_WIDTH = 320
IMAGE_HEIGHT = 200

#Name field settigns
MAX_NAME_LENGTH = 30

#Comments per page
COMMENTS_PER_PAGE = 6

#Time between posts in seconds, how frequently can a user post? 
#(This uses the user's IP address to rate limit)
MIN_TIME_BETWEEN_POSTS = 0

#Do we repect the X-Forarded-For Header?
USE_FORWARDED_HEADER = False

#The following paths should all be ABSOLUTE PATHS.
#and include trailing slashes.
#Directory from which static files are served
STATIC_FILES = '/static'

#Root directory this app is served from (don't forget the trailing slash!)
APP_ROOT = '/'

#Where should images be stored
LOCAL_IMG_DIR = './static/uploads/'
SERVED_IMG_DIR = '/static/uploads/'
IMG_EXT = '.png'

#Database location (this should not be in a place that is served by the web server)
DB = 'sqlite/testing.sqlite3'

