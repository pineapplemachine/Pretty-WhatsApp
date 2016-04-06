**This repo is currently under construction. Please come back soon!**

# Summary

When long pressing a conversation in WhatsApp it presents an option to "Email chat". This is a script for Python 2.7 which generates an easy-on-the-eyes html page from the jumble of files attached to a received email.

Tested with Chrome. Functionality and aesthetics are not guaranteed in other browsers, least of all IE.

Pretty-WhatsApp is released under the [zlib/libpng license](license.txt).

# Usage

To use, run this script with an argument which is the path to a directory containing *all* of the attachments included with an archive email sent using WhatsApp.

``` python
python pretty-whatsapp.py -i path/to/archive -o path/to/output.html
```
