'''
Created on 2020-10-29

@author: wf
'''
import unittest
import os
import getpass
from wikibot.wikipush import WikiPush

class TestWikiPush(unittest.TestCase):
    '''
    test pushing pages including images
    '''

    def setUp(self):
        self.debug=False
        pass


    def tearDown(self):
        pass
    
    def testIssue16(self):
        '''
        https://github.com/WolfgangFahl/py-3rdparty-mediawiki/issues/16
        allow mass delete of pages
        '''
        # don't test this in Travis
        if getpass.getuser()=="travis":
            return
        wikipush=WikiPush(None,"test")
        pageTitles=['deleteMe1','deleteMe2','deleteMe3']
        for pageTitle in pageTitles:
            newPage=wikipush.toWiki.getPage(pageTitle)            
            newPage.edit("content for %s" % pageTitle,"created by testIssue16")
        wikipush.nuke(pageTitles, force=False)
        wikipush.nuke(pageTitles, force=True)
    
    def testIssue14(self):
        '''
        https://github.com/WolfgangFahl/py-3rdparty-mediawiki/issues/14
        Pushing pages in File: namespace should be working
        '''
        return # don't test this nightly
        # don't test this in Travis
        if getpass.getuser()=="travis":
            return
        wikipush=WikiPush("master","test")
        wikipush.push(["File:index.png"], force=True, ignore=True, withImages=True)
        
         
    def testIssue12(self):
        '''
        https://github.com/WolfgangFahl/py-3rdparty-mediawiki/issues/12
        add -qf / queryField option to allow to select other property than mainlabel
        '''
        # don't test this in Travis
        if getpass.getuser()=="travis":
            return
        wikipush=WikiPush("smw","test")
        ask="""{{#ask:[[Has conference::+]]
 |mainlabel=Talk
 |?Has description=Description
 |?Has conference=Event
 |sort=Has conference
 |order=descending
 |format=table
 |limit=200
}}"""
        pages=wikipush.query(ask,queryField="Event")
        if self.debug:
            print (pages)
            print (len(pages))
        self.assertTrue(len(pages)>15)
        self.assertTrue(len(pages)<100)
    
    def testTransferPagesFromMaster(self):
        '''
        test transferpages
        '''
        if getpass.getuser()=="travis":
            return
        ask="{{#ask: [[TransferPage page::+]][[TransferPage wiki::Master]]| mainlabel=-| ?TransferPage page = page| format=table|limit=300}}"
        wikipush=WikiPush("master","test")
        pages=wikipush.query(ask,queryField="page")
        if self.debug:
            print (pages)
    
    def testQuery(self):
        '''
        https://github.com/WolfgangFahl/py-3rdparty-mediawiki/issues/10
        Query support for page selection
        '''
        if getpass.getuser()=="travis":
            return
        wp=WikiPush("smw","test")
        pages=wp.query("[[Capital of::+]]")
        if self.debug:
            print (pages)
        self.assertTrue(len(pages)>=5)
        self.assertTrue("Demo:Berlin" in pages)

    def testWikiPush(self):
        '''
        test pushing a page from one wiki to another
        '''
        # don't test this in Travis
        if getpass.getuser()=="travis":
            return
        wp=WikiPush("wikipedia_org_test2","test")
        for force in [False,True]:
            for ignore in [False,True]:
                wp.push(["PictureTestPage"],force=force,ignore=ignore)
        pass
    
    def testDiff(self):
        '''
        check the diff functionality
        '''
        text="Hello World!\nLet's test the search and replace function.\nTry Apples and Oranges!\nOr do you like chocolate better?"
        #print (text)
        modify=WikiPush.getModify("Apples","Peaches")
        newText=modify(text)
        diff=WikiPush.getDiff(text, newText,n=0)
        if self.debug:
            print (diff)
        self.assertEqual(2,len(diff.split("\n")))
        
    def testDownload(self):
        '''
        check the image download
        '''
        # don't test this in Travis
        if getpass.getuser()=="travis":
            return
        wp=WikiPush("wikipedia_org_test2","test")
        page=wp.fromWiki.getPage("PictureTestPage")
        images=list(page.images())
        self.assertEqual(3,len(images))
        for image in images:
            if "Mona" in image.name:
                imagePath,filename=wp.downloadImage(image,"/tmp")
                imageSize=os.path.getsize(imagePath)
                if self.debug:
                    print ("size of %s is %d bytes" % (filename,imageSize))
                self.assertEqual(3506068,imageSize)
                
        
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()