'''
Created on 2020-10-29

@author: wf

 script to read push wikipages from one MediaWiki to another
  
  use: python3 wikipush.py --source [sourceId] --target [targetId] --pages [pageTitleList]
  @param sourceId - id of the source wiki
  @param targetId - id of the target wiki
  @param pages - pageList to transfer
  
  example: 
      python3 wikipush -s wikipedia-de -t test Berlin

  @author:     wf
  @copyright:  Wolfgang Fahl. All rights reserved.

'''
from wikibot.wikiclient import WikiClient
from mwclient.image import Image
from wikibot.smw import SMWClient
#from difflib import Differ
import difflib
import os
import re
from pathlib import Path
import sys
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

class WikiPush(object):
    '''
    Push pages from one MediaWiki to another
    '''
    differ=None
    
    def __init__(self, fromWikiId, toWikId,login=False,verbose=True,debug=False):
        '''
        Constructor
        '''
        self.verbose=verbose
        self.debug=debug
        
        self.fromWikiId=fromWikiId
        if self.fromWikiId is not None:
            self.fromWiki=WikiClient.ofWikiId(fromWikiId)
        self.toWikiId=toWikId
        self.toWiki=WikiClient.ofWikiId(toWikId)
        if login and self.fromWikiId is not None:
            self.fromWiki.login()
        self.toWiki.login()
        
    def log(self,msg,end='\n'):
        if self.verbose:
            print (msg,end=end)
     
    def query(self,askQuery,wiki=None,queryField=None):
        '''
        query the given wiki for pages matching the given askQuery
        
        Args:
            askQuery(string): Semantic Media Wiki in line query https://www.semantic-mediawiki.org/wiki/Help:Inline_queries
            wiki(wikibot): the wiki to query - use fromWiki if not specified
            queryField(string): the field to select the pageTitle from
        Returns:
            list: a list of pageTitles matching the given askQuery
        '''
        if wiki is None:
            wiki=self.fromWiki
        smwClient=SMWClient(wiki.getSite())
        pageRecords=smwClient.query(askQuery)  
        if queryField is None:
            return pageRecords.keys()
        # use a Dict to remove duplicates
        pagesDict={}
        for pageRecord in pageRecords.values():
            pagesDict[pageRecord[queryField]]=True
        return pagesDict.keys()
    
    def nuke(self,pageTitles,force=False):
        '''
        delete the pages with the given page Titles
        
        Args:
            pageTitles(list): a list of page titles to be transfered from the formWiki to the toWiki
            force(bool): True if pages should be actually deleted - dry run only listing pages is default
        '''
        total=len(pageTitles)
        self.log("deleting %d pages in %s (%s)" % (total,self.toWikiId,"forced" if force else "dry run"))
        for i,pageTitle in enumerate(pageTitles):
            try:
                self.log("%d/%d (%4.0f%%): deleting %s ..." % (i+1,total,(i+1)/total*100,pageTitle), end='')
                pageToBeDeleted=self.toWiki.getPage(pageTitle)   
                if not force:
                    self.log("👍" if pageToBeDeleted.exists else "👎")
                else:
                    pageToBeDeleted.delete("deleted by wiknuke")    
                    self.log("✅")
            except Exception as ex:
                msg=str(ex)
                self.log("❌:%s" % msg )
                
    @staticmethod
    def getDiff(text,newText,n=1,forHuman=True):
        #if WikiPush.differ is None:
        #    WikiPush.differ=Differ()
        # https://docs.python.org/3/library/difflib.html
        #  difflib.unified_diff(a, b, fromfile='', tofile='', fromfiledate='', tofiledate='', n=3, lineterm='\n')¶
        #diffs=WikiPush.differ.compare(,)
        textLines=text.split("\n")
        newTextLines=newText.split("\n")
        diffs=difflib.unified_diff(textLines,newTextLines,n=n)
        if forHuman:
            hdiffs=[]
            for line in diffs:
                unwantedItems=["@@","---","+++"]
                keep=True
                for unwanted in unwantedItems:
                    if unwanted in line:
                        keep=False
                if keep:
                    hdiffs.append(line)    
        else:
            hdiffs=diffs
        diffStr="\n".join(hdiffs)
        return diffStr
    
    @staticmethod
    def getModify(search,replace):
        searchRegex=r"%s" % search
        replaceRegex=r"%s" % replace
        modify=lambda text: re.sub(searchRegex,replaceRegex,text)
        return modify

                
    def edit(self,pageTitles,modify=None,context=1,force=False):
        '''
        edit the pages with the given page Titles
        
        Args:
            pageTitles(list): a list of page titles to be transfered from the formWiki to the toWiki
            force(bool): True if pages should be actually deleted - dry run only listing pages is default
        '''
        if modify is None:
            raise Exception("wikipush edit needs a modify function!")
        total=len(pageTitles)
        self.log("editing %d pages in %s (%s)" % (total,self.toWikiId,"forced" if force else "dry run"))
        for i,pageTitle in enumerate(pageTitles):
            try:
                self.log("%d/%d (%4.0f%%): editing %s ..." % (i+1,total,(i+1)/total*100,pageTitle), end='')
                pageToBeEdited=self.toWiki.getPage(pageTitle)   
                if not force and not pageToBeEdited.exists:
                    self.log("👎")
                else:
                    comment="edited by wikiedit" 
                    text=pageToBeEdited.text()
                    newText=modify(text)
                    if newText!=text:
                        if force:
                            pageToBeEdited.edit(newText,comment)  
                            self.log("✅")
                        else:
                            diffStr=self.getDiff(text, newText,n=context)
                            self.log("👍%s" % diffStr)
                    else:
                        self.log("↔")
            except Exception as ex:
                msg=str(ex)
                self.log("❌:%s" % msg )            
                
    def upload(self,files,force=False):
        '''
        push the given files
        Args:
            files(list): a list of filenames to be transfered to the toWiki
            force(bool): True if images should be overwritten if they exist
        '''
        total=len(files)
        self.log("uploading %d files to %s" % (total,self.toWikiId))
        for i,file in enumerate(files):
            try:
                self.log("%d/%d (%4.0f%%): uploading %s ..." % (i+1,total,(i+1)/total*100,file), end='')
                description="uploaded by wikiupload" 
                filename=os.path.basename(file)
                self.uploadImage(file, filename, description, force)
            except Exception as ex:
                self.log("❌:%s" % str(ex) )
        
    def push(self,pageTitles,force=False,ignore=False,withImages=False):
        '''
        push the given page titles
        
        Args:
            pageTitles(list): a list of page titles to be transfered from the formWiki to the toWiki
            force(bool): True if pages should be overwritten if they exist
            ignore(bool): True if warning for images should be ignored (e.g if they exist)
            withImages(bool): True if the image on a page should also be copied
        '''
        total=len(pageTitles)
        self.log("copying %d pages from %s to %s" % (total,self.fromWikiId,self.toWikiId))
        for i,pageTitle in enumerate(pageTitles):
            try:
                self.log("%d/%d (%4.0f%%): copying %s ..." % (i+1,total,(i+1)/total*100,pageTitle), end='')
                page=self.fromWiki.getPage(pageTitle)
                if page.exists:
                    # is this an image?
                    if isinstance(page,Image):
                        self.pushImages([page],ignore=ignore)
                    else:
                        newPage=self.toWiki.getPage(pageTitle)
                        if not newPage.exists or force:
                            try:
                                comment="pushed from %s by wikipush" % self.fromWikiId
                                newPage.edit(page.text(),comment)
                                self.log("✅")
                                pageOk=True
                            except Exception as ex:
                                pageOk=self.handleException(ex, ignore)
                            if withImages and pageOk:
                                self.pushImages(page.images(),ignore=ignore)
                        else:
                            self.log("👎")
                else:
                    self.log("❌")
            except Exception as ex:
                self.log("❌:%s" % str(ex) )
                
    def getDownloadPath(self):
        '''
        get the download path
        '''
        downloadPath=str(Path.home() / "Downloads/mediawiki")
        if not os.path.isdir(downloadPath):
            os.makedirs(downloadPath)
        return downloadPath
            
    def pushImages(self,imageList,ignore=False):
        '''
        push the images in the given image List
        
        Args:
            imageList(list): a list of images to be pushed
            ignore(bool): True to upload despite any warnings.
        '''        
        for image in imageList:
            try:
                self.log("copying image %s ..." % image.name, end='')  
                imagePath,filename=self.downloadImage(image);
                description=image.imageinfo['comment'] 
                self.uploadImage(imagePath,filename,description,ignore)
                if self.debug:
                    print(image.imageinfo)
            except Exception as ex:
                self.handleException(ex,ignore)
                
    def handleException(self,ex,ignoreExists=False):
        '''
        handle the given exception and ignore it if it includes "exists" and ignoreExists is True
        
        Args:
            ex(Exception): the exception to handle
            ignoreExists(bool): True if "exists" should be ignored
            
        Returns:
            bool: True if the exception was handled as ok False if it was logged as an error
        '''
        msg=str(ex)
        return self.handleWarning(msg, ignoreExists=ignoreExists)
        
    def handleWarning(self,msg,ignoreExists=False):
        '''
        handle the given warning and ignore it if it includes "exists" and ignoreExists is True
        
        Args:
            msg(string): the warning to handle
            ignoreExists(bool): True if "exists" should be ignored
            
        Returns:
            bool: True if the exception was handled as ok False if it was logged as an error
        '''
        marker="❌"
        #print ("handling warning %s with ignoreExists=%r" % (msg,ignoreExists))
        if ignoreExists and "exists" in msg:
            marker="✅"
        self.log("%s:%s" % (marker,msg))
        return marker=="✅"
        
                
    def downloadImage(self,image,downloadPath=None):
        '''
        download the given image
        
        Args:
            image(image): the image to download
            downloadPath(str): the path to download to if None getDownloadPath will be used
        '''
        filename=image.name.replace("File:","")
        if downloadPath is None:
            downloadPath=self.getDownloadPath()
        imagePath="%s/%s" % (downloadPath,filename)
        with open(imagePath,'wb') as imageFile:
            image.download(imageFile)
        return imagePath,filename
                            
    def uploadImage(self,imagePath,filename,description,ignoreExists=False):
        '''
        upload an image
        
        Args:
            imagePath(str): the path to the image
            filename(str): the filename to use
            description(str): the description to use
            ignoreExists(bool): True if it should be ignored if the image exists
        '''
        with open(imagePath,'rb') as imageFile:
            warnings=None
            response=self.toWiki.site.upload(imageFile,filename,description,ignoreExists)
            if 'warnings' in response:
                warnings=response['warnings']
            if 'upload' in response and 'warnings' in response['upload']:
                warningsDict=response['upload']['warnings']
                warnings=[]
                for item in warningsDict.items():
                    warnings.append(item)
            self.handleWarning("\n".join(warnings),ignoreExists)
       

__version__ = 0.1
__date__ = '2020-10-31'
__updated__ = '2020-10-31'
DEBUG=False

def mainNuke(argv=None):
    main(argv,mode='wikinuke')
    
def mainEdit(argv=None):
    main(argv,mode='wikiedit')
    
def mainPush(argv=None):
    main(argv,mode='wikipush')
    
def mainUpload(argv=None):
    main(argv,mode='wikiupload')
        
    
def main(argv=None,mode='wikipush'): # IGNORE:C0111
    '''main program.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)   
    
    program_name = mode
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    user_name="Wolfgang Fahl"
    
    program_license = '''%s

  Created by %s on %s.
  Copyright 2020 Wolfgang Fahl. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc,user_name, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-d", "--debug", dest="debug",   action="count", help="set debug level [default: %(default)s]")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)       
        if mode=="wikipush":
            parser.add_argument("-l", "--login", dest="login", action='store_true', help="login to source wiki for access permission")
            parser.add_argument("-s", "--source", dest="source", help="source wiki id", required=True)
            parser.add_argument("-f", "--force", dest="force", action='store_true', help="force to overwrite existing pages")
            parser.add_argument("-i", "--ignore", dest="ignore", action='store_true', help="ignore upload warnings e.g. duplicate images")
            parser.add_argument("-wi", "--withImages", dest="withImages", action='store_true', help="copy images on the given pages")
        elif mode=="wikinuke":
            parser.add_argument("-f", "--force", dest="force", action='store_true', help="force to delete pages - default is 'dry' run only listing pages")            
        elif mode=="wikiedit":
            parser.add_argument("--search", dest="search", help="search pattern", required=True)
            parser.add_argument("--replace", dest="replace", help="replace pattern", required=True)
            parser.add_argument("--context", dest="context",type=int, help="number of context lines to show in dry run diff display",default=1)
            parser.add_argument("-f", "--force", dest="force", action='store_true', help="force to edit pages - default is 'dry' run only listing pages")            
        elif mode=="wikiupload":
            parser.add_argument("--files", nargs='+', help="list of files to be uploaded", required=True)
            parser.add_argument("-f", "--force", dest="force", action='store_true', help="force to (re)upload existing files - default is false")            
            pass
        if mode in  ["wikipush","wikiedit","wikinuke"]: 
            parser.add_argument("-q", "--query", dest="query", help="select pages with given SMW ask query", required=False)
            parser.add_argument("-qf", "--queryField",dest="queryField",help="query result field which contains page")
            parser.add_argument("-p", "--pages", nargs='+', help="list of page Titles to be pushed", required=False)
        
        parser.add_argument("-t", "--target", dest="target", help="target wiki id", required=True)    
        # Process arguments
        args = parser.parse_args()
        
        if mode=="wikipush":
            wikipush=WikiPush(args.source,args.target,login=args.login)
            queryWiki=wikipush.fromWiki
        elif mode=="wikiupload":
            wikipush=WikiPush(None,args.target)
        else:
            wikipush=WikiPush(None,args.target)
            queryWiki=wikipush.toWiki
        if mode=="wikiupload":
            wikipush.upload(args.files,args.force)
        else:    
            if args.pages:
                pages=args.pages
            elif args.query:
                pages=wikipush.query(args.query,wiki=queryWiki,queryField=args.queryField)
            if pages:
                if mode=="wikipush":
                    wikipush.push(pages,force=args.force,ignore=args.ignore,withImages=args.withImages)
                elif mode=='wikinuke':
                    wikipush.nuke(pages,force=args.force)
                elif mode=='wikiedit':
                    modify=WikiPush.getModify(args.search,args.replace)
                    wikipush.edit(pages,modify=modify,context=args.context,force=args.force)
                else:
                    raise Exception("undefined wikipush mode %s" % mode)
      
        
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 1
    except Exception as e:
        if DEBUG:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2
                
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    sys.exit(mainPush())