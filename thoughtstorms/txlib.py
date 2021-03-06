import re, markdown, yaml, urllib.request, urllib.error, urllib.parse, csv


# Environment should have
# sister_sites dict
# site_root

class Environment :
    def __init__(self,sr,ss) :
        self.sister_sites = ss
        self.site_root = sr

## Links
## _____________________________________________________________

class LinkFixer :
    def __init__(self,env) :
        self.r_sister = re.compile("(\[\[((\S+?):(\S+?))\]\])")
        self.r_sqrwiki = re.compile("(\[\[(\S+?)\]\])")
        self.r_sqr_alt = re.compile("(\[\[((\S+?)(\s+)(.+))\]\])")
        self.environment = env

    def sub_sister(self) :
        def ss(mo) :
            mog = mo.groups()
            site_id,page_name = mog[2],mog[3]
            try :
                url = self.environment.sister_sites[site_id].strip("/")
                return """<a href="%s/%s">%s:%s</a>""" % (url,page_name,site_id,page_name)
            except Exception as e :
                return "** | Error in SisterSite link ... seems like %s is not recognised. %s %s"  % (site_id,e,self.environment.sister_sites)
        return ss

    def sister_line(self,s) :
        if self.r_sister.search(s) :
            s = self.r_sister.sub(self.sub_sister(),s)
        return s
    
    def sqrwiki_line(self,s) :
        if self.r_sqrwiki.search(s) :
            s = self.r_sqrwiki.sub(r"""<a href="%s\2">\2</a>"""%self.environment.site_root,s)
        return s
        
    def sqr_alt_line(self,s) :
        if self.r_sqr_alt.search(s) :
            s = self.r_sqr_alt.sub(r"""<a href="%s\3">\5</a>"""%self.environment.site_root,s)
        return s

    def link_filters(self,line) :
        return self.sqr_alt_line(self.sqrwiki_line(self.sister_line(line)))
        
## Tables
## _____________________________________________________________

class DoubleCommaTabler :

    def __init__(self,env) :
        self.tableMode = False
        self.newTable = False
        self.doubleComma = re.compile("(,,)")
        self.env = env
        
    def __call__(self,l) :
        if not self.tableMode :
            if self.doubleComma.findall(l) :
                self.tableMode = True
                self.newTable = True
        
        if self.tableMode :
            if not self.doubleComma.findall(l) :
                l = l + "\n</tbody>\n</table>"
                self.tableMode = False
            else :
                l = self.doubleComma.sub("</td><td>",l)
                l = "<tr><td>"+l+"</td></tr>"

        if self.newTable :
            l = """<table>
  <tbody>
""" + l
            
            self.newTable = False
            
        return l
        

## Magic Markers
## _____________________________________________________________

def magicMarkers(s) :
    marker = re.compile("(\{=(\S+?)=\})")
    if marker.search(s) :
        s = marker.sub(r"",s)
    return s
            


null_env = Environment("",{})


#### Current

from functools import reduce

OPEN = "[<"
CLOSE = ">]"
class BlockParseException(Exception) :
    pass

class UnknownBlock() : 
    def evaluate(self,lines) :
        return ["Block of type Unknown evaluated\n"] + lines + ["\nBLOCK ENDS"]
        

class PreBlock() :
    """Does nothing, passes contents through without changing them"""
    def evaluate(self,lines) :        
        return ["MARKDOWN_TOGGLE"] + lines + ["MARKDOWN_TOGGLE"]

class YouTubeBlock() :
    def evaluate(self,lines) :
        data = yaml.safe_load("\n".join(lines))
        return ["""<div class="youtube-embedded"><iframe width="400" height="271" src="http://www.youtube.com/embed/%s" frameborder="0" allowfullscreen></iframe></div>""" % data["id"]]

class SoundCloudIndividualBlock() :
    def evaluate(self,lines) :
        data = yaml.safe_load("\n".join(lines))
        return [r"""<iframe width="100%" height="450" scrolling="no" frameborder="no" src="https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/""" + "%s" % data["id"] + """&amp;auto_play=false&amp;hide_related=false&amp;show_comments=true&amp;show_user=true&amp;show_reposts=false&amp;visual=true"></iframe>"""]

class SoundCloudBlock() :
    def evaluate(self,lines) :
        data = yaml.safe_load("\n".join(lines))
        return [r"""<div class="soundcloud-embedded"><iframe width="100%" height="450" scrolling="no" frameborder="no" src="https://w.soundcloud.com/player?url=https://api.soundcloud.com/playlists/""" + "%s"%data["id"] + """&amp;visual=true"></iframe></div>"""]

class BandCampBlock() :
    def evaluate(self,lines) :
        data = yaml.safe_load("\n".join(lines))
        return ["""<div class="bandcamp-embedded"><iframe style="border: 0; width: 350px; height: 555px;" src="https://bandcamp.com/EmbeddedPlayer/album=%s/size=large/bgcol=ffffff/linkcol=0687f5/transparent=true/" seamless><a href="%s">%s</a></iframe></div>""" % (data["id"],data["url"],data["description"])]
        
class AudioBlock() :
    def evaluate(self,lines) :
        data = yaml.safe_load("\n".join(lines))
        if "mp3" in data :
            return ["""#### %s

<audio controls>
  <source src="%s" type="audio/mpeg">
Your browser does not support the audio element.
</audio>""" % (data["title"],data["mp3"])]


class LocalFileBlock() :
    def evaluate(self,lines) :
        data = yaml.safe_load("\n".join(lines))
        try :
            f = open(data["path"])
            ext_lines = f.readlines()
            f.close()            
        except Exception as e :
            return ["<pre>"] + ["""Error, can't read %s. 
            
More specifically %s""" % (data["path"],e)] + ["</pre>"]

        if "filter" in data :
            r = re.compile(data["filter"])
            flt = lambda x : r.search(x)
            outlines = (x for x in ext_lines if flt(x))
        else :
            outlines = ext_lines
        return ["<pre>"] + [x for x in outlines] + ["</pre>"]

class SimpleRawTranscludeBlock() :
    def __init__(self,env) :
        self.environment = env

    def evaluate(self,lines,md_eval=True) :
        data = yaml.safe_load("\n".join(lines))
        try :
            url = data["url"]
            response = urllib.request.urlopen(url)
            s = response.read()
            #return s.split("\n")
            if md_eval :
                s = MarkdownThoughtStorms().cook(s,self.environment)
            s = """
<div class="transcluded">

<strong>Transcluded from <a href="%s">%s</a> </strong>

%s

</div>    
""" % (url,url,s)
            return s.split("\n")
            
            
        except Exception as e :
            return ["Error, can't get data from %s" % url]


class CSVBlock() :
    def evaluate(self,lines,md_eval=True) :
        data = yaml.safe_load("\n".join(lines))
        try :
            build = ""
            with open(data["path"]) as csvfile :
                reader = csv.reader(csvfile, delimiter=',', quotechar='"')
                for row in reader:
                    build = build + "<tr><td>" + '</td><td>'.join((i for i in row)) + "</td></tr>\n"
                return ["""\n<table class="table table-striped table-bordered table-condensed">
    %s    
    </table>""" % build]
        except Exception as e :
            return ["Error in CSV Include %s " % e]


    
class GalleryBlockX() :
    def evaluate(self,lines,md_eval=False) :
        data = yaml.safe_load("\n".join(lines))
        try :
            build = """<div class="gallery">"""
            for k,v in data.items() :
                build=build + """\n<figure>
<img src="%s"/>
<figcaption>%s</figcaption>
</figure>""" % (v["url"],v["caption"])
            build=build+"</div>"
            return [build]
        except Exception as e : 
            return ["Error %s" % e]
            


class GalleryBlock() :
    def evaluate(self,lines,md_eval=False) :
        data = yaml.safe_load("\n".join(lines))
        try :
            build = """<section><div class="container gal-container">
"""
            counter=0
            for k,v in data.items() :
                build=build+"""
<div class="col-md-4 col-sm-6 co-xs-12 gal-item">
      <div class="box">
        <a href="#" data-toggle="modal" data-target="#%s">
          <img src="%s" class="img-thumbnail">
        </a>
        <div class="modal fade" id="%s" tabindex="-1" role="dialog">
          <div class="modal-dialog" role="document">
            <div class="modal-content">
                <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">X</span></button>
              <div class="modal-body">
                <img src="%s" class="img-rounded">
              </div>
                <div class="col-md-12 description">
                  <h4>%s</h4>
                </div>
            </div>
          </div>
        </div>
      </div>
    </div>
""" % (counter,v["url"],counter,v["url"],v["caption"])
                counter=counter+1
            build = build+"\n</div></section>"
            return [build]
            
        except Exception as e :
            return ["Error %s" % e]

class Block :
    def __init__(self,typ,env) :
        self.type = typ
        self.lines = []
        if self.type == "PRE" :
            self.evaluator = PreBlock()
        elif self.type == "YOUTUBE" :
            self.evaluator = YouTubeBlock()
        elif self.type == "SOUNDCLOUD" :
            self.evaluator = SoundCloudBlock()
        elif self.type == "SOUNDCLOUDINDIVIDUAL" :
            self.evaluator = SoundCloudIndividualBlock()
        elif self.type == "BANDCAMP" :
            self.evaluator = BandCampBlock()
        elif self.type == "AUDIO" :
            self.evaluator = AudioBlock()
        elif self.type == "LOCALFILE" :
            self.evaluator = LocalFileBlock()
        elif self.type == "SIMPLERAWTRANSCLUDE" :
            self.evaluator = SimpleRawTranscludeBlock(env)
        elif self.type == "CSV" :
            self.evaluator = CSVBlock()
        elif self.type == "GALLERY" :
            self.evaluator = GalleryBlock()
            
        else :
            self.evaluator = UnknownBlock()
        
    def add_line(self,l) :
        self.lines.append(l)
        
    def evaluate(self) : return self.evaluator.evaluate(self.lines)
        
class BlockServices : 
    """
    Provides embeddable blocks within pages. This should become the generic mechanism for all inclusions / transclusions 
    """
    def handle_lines(self,lines,env) :
        #if not reduce(lambda a, b : a or b, [OPEN in l for l in lines],False) : return lines
        current_block = None
        in_block = False
        count = 0

        for l in lines :
            if in_block :
                # In Block
                if CLOSE in l :
                    in_block = False
                    count = count + 1
                    for x in current_block.evaluate() :
                        yield x
                    current_block=None
                    continue
                elif OPEN in l :
                    raise BlockParseException("Opening block inside another block at line %s" % count)
                else :
                    # Do stuff inside block
                    current_block.add_line(l)
                    count = count + 1
            else :
                # Not in Block
                if CLOSE in l : 
                    raise BlockParseException("Trying to close a block when we aren't in one at line %s" % count)    
                if OPEN in l :
                    in_block = True
                    block_type = l.split(OPEN)[1].strip()
                    current_block = Block(block_type,env)
                    count = count + 1
                    continue
                # here we are not in a block and not starting one
                yield l
                count = count + 1

        

class MarkdownThoughtStorms :
    """ThoughtStorms Wiki has been converted to Markdown for basic formatting.
    We keep some extra formatting. 
    Double Square brackets for internal links and Double commas as a quick table format, (handled within "wiki_filters")
    social_filters handles the social media embedding we use.
    Finally we do markdown.
    """

    def md(self,p) :
        p = p.replace("<","-=OPEN=-")
        p = p.replace(">","-=CLOSE=-")
        p = markdown.markdown(p)
        p = p.replace("-=CLOSE=-",">")
        p = p.replace("-=OPEN=-","<")
        return p        

    def wiki_filters(self,s) : 
        return LinkFixer(self.env).link_filters(magicMarkers(self.table_line(s)))

    def mystrip(self,s) :
        if s.strip() == "" : return s.strip()
        if s.strip()[0] != "*" : return s.strip()
        return s

    def cook(self,p,env) :
        self.env = env
        self.table_line = DoubleCommaTabler(env)
        lines = p.split("\n")
        lines = BlockServices().handle_lines(lines,env)
        lines = (self.wiki_filters(l) for l in lines)
        page = "\n".join((self.mystrip(l) for l in lines))
        if "MARKDOWN_TOGGLE" in page :
            ps = page.split("\nMARKDOWN_TOGGLE")
            for x in range(len(ps)) :
                if x % 2 == 0 :
                    ps[x] = self.md(ps[x])                    
                else :
                    pass
            return "\n".join(ps)
                   
        return self.md(page) 

