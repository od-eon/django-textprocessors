# -*- coding: iso-8859-1 -*
##
## (c) Fry-IT, www.fry-it.com, 2007
## <peter@fry-it.com>
##
# modified by Stefan Talpalaru

"""
A very spartan attempt of a script that converts HTML to
plaintext.

The original use for this little script was when I send HTML emails out I also
wanted to send a plaintext version of the HTML email as multipart. Instead of 
having two methods for generating the text I decided to focus on the HTML part
first and foremost (considering that a large majority of people don't have a 
problem with HTML emails) and make the fallback (plaintext) created on the fly.

This little script takes a chunk of HTML and strips out everything except the
<body> (or an elemeny ID) and inside that chunk it makes certain conversions 
such as replacing all hyperlinks with footnotes where the URL is shown at the
bottom of the text instead. <strong>words</strong> are converted to *words* 
and it does a fair attempt of getting the linebreaks right.

As a last resort, it strips away all other tags left that couldn't be gracefully
replaced with a plaintext equivalent.
Thanks for Fredrik Lundh's unescape() function things like:
    'Terms &amp; Conditions' is converted to
    'Termss & Conditions'

It's far from perfect but a good start. It works for me for now.


TODO: 
    * proper unit tests
    * understand some basic style commands such as font-weight:bold

    
Announcement here:
    http://www.peterbe.com/plog/html2plaintext
    
Thanks to:
    Philipp (http://www.peterbe.com/plog/html2plaintext#c0708102y47)
"""

__version__='0.2'


import re, sys
from textwrap import TextWrapper
from BeautifulSoup import BeautifulSoup, SoupStrainer, Comment

def word_wrap(string, width=80):
    """ word wrapping function.
        string: the string to wrap
        width: the column number to wrap at
    """
    newstring = ""
    if len(string) > width:
        while True:
            # find position of nearest whitespace char to the left of "width"
            marker = width-1
            while not string[marker].isspace():
                marker = marker - 1

            # remove line from original string and add it to the new string
            newline = string[0:marker] + "\n"
            newstring = newstring + newline
            string = string[marker+1:]

            # break out of loop when finished
            if len(string) <= width:
                break
    return newstring + string

def html2plaintext(html, body_id=None, encoding='utf8', width=80):
    """ from an HTML text, convert the HTML to plain text.
    If @body_id is provided then this is the tag where the 
    body (not necessarily <body>) starts.
    """
    if encoding == 'utf8':
        from django.utils.safestring import SafeUnicode
        html = SafeUnicode(html)
        from django.utils.encoding import force_unicode
        html = force_unicode(html)
        html = html.encode('ascii', 'xmlcharrefreplace')
    urls = []
    if body_id is not None:
        strainer = SoupStrainer(id=body_id)
    else:
        strainer = SoupStrainer('body')
    
    soup = BeautifulSoup(html, parseOnlyThese=strainer, fromEncoding=encoding)
    for link in soup.findAll('a'):
        title = link.renderContents()
        for url in [x[1] for x in link.attrs if x[0]=='href']:
            urls.append(dict(url=str(url), tag=str(link), title=str(title)))

    html = soup.__str__(encoding)
            
    url_index = []
    i = 0
    for d in urls:
        if d['title'] == d['url'] or 'http://'+d['title'] == d['url']:
            html = html.replace(d['tag'], d['url'])
        elif d['url'].startswith('#'): # don't show anchor content
            html = html.replace(d['tag'], '')
        else:
            i += 1
            html = html.replace(d['tag'], '%s [%s]' % (d['title'], i))
            url_index.append(d['url'])

    #html = html.replace('<strong>','*').replace('</strong>','*')
    #html = html.replace('<b>','*').replace('</b>','*')
    #html = html.replace('<h3>','*').replace('</h3>','*')
    #html = html.replace('<h2>','**').replace('</h2>','**')
    #html = html.replace('<h1>','**').replace('</h1>','**')
    #html = html.replace('<em>','/').replace('</em>','/')
    

    # the only line breaks we respect is those of ending tags and 
    # breaks
    
    html = html.replace('\n',' ')
    html = html.replace('<br>', '\n')
    html = html.replace('</p>', '\n\n')
    html = re.sub('<br\s*/>', '\n', html)
    html = html.replace('</tr>', '\n')
    #html = html.replace('</table>', '\n\n')
    html = html.replace(' ' * 2, ' ')


    # for all other tags we failed to clean up, just remove then and 
    # complain about them on the stderr
    def desperate_fixer(g):
        #print >>sys.stderr, "failed to clean up %s" % str(g.group())
        return ' '

    html = re.sub('<.*?>', desperate_fixer, html)

    # lstrip all lines
    html = '\n'.join([x.lstrip() for x in html.splitlines()])

    for i, url in enumerate(url_index):
        if i == 0:
            html += '\n\n'
        html += '[%s] %s\n' % (i+1, url)

    html = unescape(html)
    
    # reduce consecutive empty lines to one
    pat = re.compile(r'(\n\s*\n)+', re.M)
    html = pat.sub('\n\n', html)

    # wrap long lines
    #html = word_wrap(html, width)
    # Use the python TextWrapper instead of the builtin function
    wrapper = TextWrapper(width=80)

    html = wrapper.fill(html)

    return html

import htmlentitydefs
# from http://effbot.org/zone/re-sub.htm#strip-html
##
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)



def test_html2plaintest():
    html = '''
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html>
<body>

<div id="main">
<p>This is a paragraph.</p>

<p><a href="http://one.com">Foobar</a>
<br />

<a href="http://two.com">two.com</a>

</p>
     <p>Visit <a href="http://www.google.com">www.google.com</a>.</p>
<br />
Text elsewhere.

<a href="http://three.com">Elsewhere</a>

</div>
</body>
</html>
    '''
    print html2plaintext(html, body_id='main')

    
if __name__=='__main__':
    if (len(sys.argv) == 1):
        test_html2plaintest()
    else:
        f = open(sys.argv[1])
        print html2plaintext(f.read())
