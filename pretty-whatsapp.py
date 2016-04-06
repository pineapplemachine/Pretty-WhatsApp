import os
import re
from datetime import datetime, timedelta

path = 'brian' # path to test data

newline_pattern = re.compile(r'\d\d/\d\d/20\d\d, \d\d?:\d\d [AP]M - ')
message_pattern = re.compile(r'(?s)(\d\d/\d\d/20\d\d, \d\d?:\d\d [AP]M) - (.*?): (.*)')
chatlog_pattern = re.compile(r'WhatsApp Chat with .*?\.txt')
attachment_pattern = re.compile(r'((.*?)-.*?-.*?\.(.*?)) \(file attached\)')

time_divider = '<div class="divider"></div>'

with open('template.html', 'r') as templatefile:
    webpage_template = templatefile.read()

input_dateformat = '%d/%m/%Y, %I:%M %p'

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
    def __repr__(self):
        return '%s - %s: %s' % (
            datetime.strftime(self.date, input_dateformat),
            self.author, self.content
        )
    def html(self, path):
        match = attachment_pattern.match(self.content)
        content = self.content
        contentclass = 'TXT'
        if match is not None:
            filename = match.group(1)
            filepath = os.path.join(path, filename)
            filetype = match.group(2)
            fileext = match.group(3)
            contentclass = filetype
            if filetype == 'IMG':
                content = '<a href="%s"><img src="%s"></a>' % (
                    filepath, filepath
                )
            elif filetype =='PTT':
                content = '<audio controls><source src="%s" type="audio/%s"></audio>' % (
                    filepath, fileext
                )
            else:
                content = 'Unrecognized content type %s: <a href="%s">%s</a>' % (
                    filetype, filepath, filename
                )
        return (
            '<div class="message"><div class="datetime">%s</div><div class="author">%s</div><div class="content %s">%s</div></div>' % (
                datetime.strftime(self.date, input_dateformat), self.author, contentclass, content
            )
        )



def process(path):
    content = getchatcontent(path)
    messagetext = getchatmessages(content)
    messages = parsechatmessages(messagetext)
    htmlmessages = messagestohtml(messages, path)
    html = makewebpage(htmlmessages, path.title())
    return html
    
def getchatcontent(path):
    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)
        if os.path.isfile(filepath) and chatlog_pattern.match(filename):
            with open(filepath, 'r') as chatfile:
                return chatfile.read()
                
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
    
def parsechatmessages(messages):
    return [message.parse(messagetext) for messagetext in messages]
    
def messagestohtml(messages, path):
    htmlitems = []
    lastmessage = None
    for message in messages:
        if lastmessage is not None and (message.date - lastmessage.date).total_seconds() >= 18000:
            htmlitems.append(time_divider)
        htmlitems.append(message.html(path))
        lastmessage = message
    return htmlitems
    
def makewebpage(messageshtml, title):
    messagecontent = '\n'.join(message for message in messageshtml)
    return webpage_template % {
        'title': title,
        'body': messagecontent,
        'css': 'pretty-whatsapp.css'
    }
    


with open('%s.html' % path, 'w') as htmlfile:
    htmlfile.write(process(path))
