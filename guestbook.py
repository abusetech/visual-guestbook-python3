#!/usr/bin/env python

import web
import models

#Tools for handling images
import base64
from PIL import Image
import io

import settings

urls = (
        settings.APP_ROOT, 'index', 
)

        

class index:

        def GET(self):
                data = web.input()
                render = web.template.render('templates')

                #Ugly, Ugly pagination logic...
                
                if 'after' in data:
                        try:
                                after = int(data.after)
                        except ValueError:
                                #Fail silently.
                                after = 0

                        comments = models.comment.get_list(settings.COMMENTS_PER_PAGE, after=after)

                elif 'before' in data:
                        try:
                                before = int(data.before)
                        except ValueError:
                                #Fail silently.
                                before = 0

                        comments = models.comment.get_list(settings.COMMENTS_PER_PAGE, before=before)
                else:
                        comments = models.comment.get_list(settings.COMMENTS_PER_PAGE)

                #ID of first comment appearing on the page
                first = None if not len(comments) > 0 else comments[0].comment_id
                #ID of last comment appearing on the page, None there are less than the maximum number of comments per page.
                last = None if len(comments) < settings.COMMENTS_PER_PAGE else comments[settings.COMMENTS_PER_PAGE-1].comment_id
                
                #On first page?
                if first and first == models.comment.get_most_recent().comment_id:
                        first = None
                        #Redirect to remove the before or after GET parameters, if present.
                        if 'before' in data or 'after' in data:
                                raise web.SeeOther(".")
                                return "Redirecting..."
                #On last page?
                if last and last == models.comment.get_oldest().comment_id:
                        last = None

                return render.index(comments, settings, first, last)
                

        def POST(self):
                #User wishes to post a comment or image
                data = web.input()
                name = data.name

                try:
                        raw_image_data = data.image_data
                except ValueError:
                        #No image data...
                        print ("No image data in request!")
                        raise web.SeeOther(".")
                        return

                #get the client IP address
                if settings.USE_FORWARDED_HEADER:
                        ip_address = web.ctx.env['HTTP_X_FORWARDED_FOR']
                else:
                        ip_address = web.ctx.ip

                #validate ip address - TODO: this only validates IPv4 addresses!
                if not web.net.validipaddr(ip_address):
                        print ("web.ctx.ip returned an invalid IP address! Check your WSGI configuration.")
                        raise web.SeeOther(".")
                        return

                if not models.is_allowed_to_post(ip_address):
                        return "You are posting too quickly, slow down!"

                #File size check
                if len(raw_image_data) > settings.MAX_IMAGE_SIZE:
                                print ("Image exceeds maximum size.")
                                raise web.SeeOther(".")
                                return

                if 'data:image/png;base64,' in raw_image_data:
                        try:
                                image_data = bytes(base64.b64decode((raw_image_data.partition('data:image/png;base64,')[2])))
                                print(image_data)
                                image = Image.open(io.BytesIO(image_data))
                        except Exception as e:
                                print ("Error converting image data. \n" + str(e))
                                raise web.SeeOther(".")
                                return
                else:
                        #Comment with no image or an invalid image!
                        raise web.SeeOther(".")
                        return

                #Check that the image is in the correct format and is the correct size.
                if not image.size == (settings.IMAGE_WIDTH, settings.IMAGE_HEIGHT):
                        print ("Invalid image size: " + image.size)
                        raise web.SeeOther(".")
                        return

                #Check that the image format is correct
                if not image.format == "PNG":
                        print ("Invalid image format: " + image.format)
                        raise web.SeeOther(".")
                        return

                #Check that the provided name is a reasonable length
                if len(name) > settings.MAX_NAME_LENGTH:
                        print ("Name is too long! " + str(len(name)))
                        raise web.SeeOther(".")
                        return

                #All good, build the comment.
                reply = models.comment(name=name, ip_address=ip_address, approved=True)

                #Save the image. Could benifit from some sanity checks.
                outfile = open(reply.get_local_filename(), 'wb')
                image.save(outfile)

                #Save the reply
                reply.save()
                print (ip_address)
                models.make_post(ip_address)
                raise web.SeeOther(".")


if __name__ == "__main__":
        app = web.application(urls, globals())
        app.run()

