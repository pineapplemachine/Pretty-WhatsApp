#!/usr/bin/env python
# coding: utf-8

__author__ = 'Sophie Kirschner'
__license__ = 'zlib/libpng'
__email__ = 'sophiek@pineapplemachine.com'
__version__ = '1.0.0'



import sys, os
import re
from datetime import datetime, timedelta
import argparse
import shutil



# Regular expressions for matching and grouping text in the plaintext chat log
newline_pattern = re.compile(r'\d\d/\d\d/20\d\d, \d\d?:\d\d [AP]M - ')
message_pattern = re.compile(r'(?s)(\d\d/\d\d/20\d\d, \d\d?:\d\d [AP]M) - (.*?): (.*)')
chatlog_pattern = re.compile(r'WhatsApp Chat with (.*?)\.txt')
attachment_pattern = re.compile(r'((.*?)-.*?-.*?\.(.*?)) \(file attached\)\s*(.*)')
contact_pattern = re.compile(r'(.*?\.vcf) \(file attached\)')
location_pattern = re.compile(r'location: (.*?\?q=(.*?),(.*))')

# Format of dates in plaintext chat log
input_dateformat = '%d/%m/%Y, %I:%M %p'
output_dateformat = '%d/%m/%y %H:%M'

# Location of default files
defaulthtmlpath = 'pretty-whatsapp.html'
defaultcsspath = 'pretty-whatsapp.css'



def __main__(args):
    
    print('Pretty-WhatsApp %(version)s by %(author)s' % {
        'version': __version__,
        'author': __author__
    })
    
    # Verify inputs
    fail = False
    if not os.path.exists(args.css):
        print('CSS path "%s" does not exist.' % args.css)
        fail = True
    if not (os.path.exists(args.input) and os.path.isdir(args.input)):
        print('Input path "%s" does not exist or is not a directory.' % args.input)
        fail = True
    if fail: exit(0)
    
    # Default to outputting HTML to the input directory itself if no output path is specified
    mediapath = os.path.abspath(args.input)
    if not args.output:
        args.output = os.path.join(args.input, defaulthtmlpath)
        mediapath = '.'
    
    # Check whether output files already exist and request confirmation for overwriting
    cssfilename = os.path.basename(args.css)
    cssoutput = os.path.join(os.path.dirname(args.output), cssfilename)
    csssame = os.path.exists(cssoutput) and os.path.abspath(cssoutput) == os.path.abspath(args.css) # Input and output CSS paths are the same
    if not args.yes:
        htmlexists = os.path.exists(args.output)
        cssexists = os.path.exists(cssoutput) and not csssame
        if htmlexists or cssexists:
            if htmlexists: print('Output HTML path "%s" already exists and would be overwritten.' % args.output)
            if cssexists: print('Output CSS path "%s" already exists and would be overwritten.' % cssoutput)
            if(raw_input('Continue anyway? (y/N) ').lower() != 'y'): exit(0)
    
    print('Reading chat log from input directory "%s".' % args.input)
    chatpath, chatmatch = getchatcontentpath(args.input)
    chattitle = chatmatch.group(1).title()
    with open(chatpath, 'r') as chatfile: chatcontent = chatfile.read()
    
    print('Parsing chat messages.')
    messages = parsechatmessages(getchatmessages(chatcontent))
    
    print('Generating output HTML from messages.')
    templates = loadtemplates('templates')
    htmlitems = messagestohtml(messages, mediapath, templates, args.dateformat, args.timedelta)
    html = templates['webpage'] % {
        'title': chattitle,
        'body': '\n'.join(item for item in htmlitems),
        'css': cssfilename
    }
    
    outputdir = os.path.dirname(args.output)
    if outputdir and not os.path.exists(outputdir):
        print('Creating directory "%s".' % outputdir)
        os.makedirs(outputdir)
    if not csssame:
        print('Copying CSS to path "%s".' % cssoutput)
        shutil.copyfile(args.css, cssoutput)
    with open(args.output, 'w') as htmlfile:
        print('Writing HTML to path "%s".' % args.output)
        htmlfile.write(html)
    
    print('All done!')



class message(object):
    
    def __init__(self, date, author, content):
        self.date = date
        self.author = author
        self.content = content
    
    @staticmethod
    def parse(text):
        match = message_pattern.match(text)
        if match is not None:
            return message(
                datetime.strptime(match.group(1), input_dateformat),
                match.group(2), match.group(3)
            )
        else:
            return None
            
    def __str__(self):
        return self.content
    
    # Reproduce input string used to generate this message
    def __repr__(self):
        return '%s - %s: %s' % (
            datetime.strftime(self.date, input_dateformat),
            self.author, self.content
        )
    
    def html(self, path, templates, dateformat):
        ismedia = False
        filename, filetype, fileext, comment, url = '', '', '', '', ''
        lat, lon = '', ''
        datestring = datetime.strftime(self.date, dateformat)
        
        # Audio, images, and videos
        mediamatch = attachment_pattern.match(self.content)
        contactmatch = contact_pattern.match(self.content)
        locmatch = location_pattern.match(self.content)
        if mediamatch is not None:
            filename, filetype, fileext, comment = mediamatch.group(1, 2, 3, 4)
            ismedia = True
        # vCards
        elif contactmatch is not None:
            filename = contactmatch.group(1)
            fileext = 'vcf'
            filetype = 'CON'
            ismedia = True
        # Lat/lon
        elif locmatch is not None:
            url, lat, lon = locmatch.group(1, 2, 3)
            filetype = 'LOC'
            ismedia = True
        
        if ismedia:
            filepath = os.path.join(path, filename)
            comment = makeparagraphs(comment)
            # Get template for file type, or default template if unsupported
            templatekey = 'content.%s' % filetype
            if templatekey not in templates: templatekey = 'content.unsupported'
            # Generate content from template
            content = templates[templatekey] % {
                'name': filename,
                'path': filepath,
                'type': filetype,
                'ext': fileext,
                'date': datestring,
                'author': self.author,
                'comment': comment,
                'url': url,
                'lat': lat,
                'lon': lon
            }
        else:
            content = makeparagraphs(self.content)
            
        # Finally, generate the message div (or whatever) from a template
        return (
            templates['message'] % {
                'date': datestring,
                'author': self.author,
                'content': content
            }
        )



# Load template HTML files from templates directory
def loadtemplates(templatesdir):
    templates = {}
    for filename in os.listdir(templatesdir):
        filepath = os.path.join(templatesdir, filename)
        if os.path.isfile(filepath):
            with open(filepath, 'r') as templatefile:
                templatekey = os.path.splitext(os.path.basename(filename))[0]
                templates[templatekey] = templatefile.read()
    return templates

# Find the plaintext chat log in an input directory
def getchatcontentpath(path):
    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)
        match = chatlog_pattern.match(filename)
        if os.path.isfile(filepath) and match:
            return filepath, match

# Turn a chat log into a list of message strings
def getchatmessages(content):
    lines = content.split('\n')
    message = ''
    messages = []
    for line in lines:
        if newline_pattern.match(line):
            if message: messages.append(message)
            message = line
        else:
            message += '\n' + line
    if message: messages.append(message)
    return messages

# Get a list of message objects given a list of message strings
def parsechatmessages(messages):
    return [message.parse(messagetext) for messagetext in messages]

# Get an HTML representation of each message object in a list, and also intersperse time dividers
def messagestohtml(messages, path, templates, dateformat, timedelta):
    htmlitems = []
    lastmessage = None
    for message in messages:
        if(
            lastmessage is not None and timedelta > 0 and
            (message.date - lastmessage.date).total_seconds() >= timedelta
        ):
            htmlitems.append(templates['divider'])
        htmlitems.append(message.html(path, templates, dateformat))
        lastmessage = message
    return htmlitems
    
# Turn text with newlines into text with <p> tags
def makeparagraphs(text):
    if text:
        return '<p>%s</p>' % text.replace('\n', '</p><p>')
    else:
        return ''



def parseargs():
    parser = argparse.ArgumentParser('Make pretty HTML out of WhatsApp chat logs exported using the app\'s "Email chat" option.')
    parser.add_argument('-i', '--input', help='Path to directory containing all attachments included in an emailed archive.', type=str, required=True)
    parser.add_argument('-o', '--output', help='Path to write the generated HTML file.', type=str)
    parser.add_argument('-c', '--css', help='Path CSS file to use and copy to the output directory.', type=str, default=defaultcsspath)
    parser.add_argument('-t', '--timedelta', help='Messages with at least this many seconds between are separated by a divider. 0 for no dividers.', type=int, default=18000)
    parser.add_argument('-f', '--dateformat', help='Set the outputted date format using a Python strftime string.', type=str, default=output_dateformat)
    parser.add_argument('-y', '--yes', help='Overwrite output files without asking.', action='store_true')
    return parser.parse_args()

if __name__ == "__main__": __main__(parseargs())
