# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# Name:         corpus/__init__.py
# Purpose:      Shortcuts to the corpus collection
#
# Authors:      Christopher Ariza
#               Michael Scott Cuthbert
#
# Copyright:    (c) 2009 The music21 Project
# License:      LGPL
#------------------------------------------------------------------------------

'''
The music21 corpus includes a collection of freely distributable
music in MusicXML, Humdrum, and other representations. The corpus
package is an interface for easily working with this data.

To see a complete listing of the works in the music21 corpus,
visit  :ref:`referenceCorpus`.  Note that music21 does not own
most of the music in the corpus -- it has been licensed to us (or
in a free license).  It may not be free in all parts of the world,
but to the best of our knowledge is true for the US.
'''
from __future__ import unicode_literals

import re
import os
import unittest
import zipfile

from music21 import common
from music21 import converter
from music21 import exceptions21
from music21 import metadata
from music21.corpus import chorales
from music21.corpus import corpora
from music21.corpus import virtual

from music21 import environment
_MOD = "corpus.base.py"
environLocal = environment.Environment(_MOD)

# a list of metadata's can reside in this module-level storage; this
# data is loaded on demand.

#------------------------------------------------------------------------------

# update and access through property to make clear
# that this is a corpus distribution or a no-corpus distribution
_NO_CORPUS = False

# store all composers in the corpus (not virtual)
# as two element tuples of path name, full name
COMPOSERS = [
    ('airdsAirs', 'Aird\'s Airs'),
    ('bach', 'Johann Sebastian Bach'),
    ('beethoven', 'Ludwig van Beethoven'),
    ('cpebach', 'C.P.E. Bach'),
    ('ciconia', 'Johannes Ciconia'),
    ('essenFolksong', 'Essen Folksong Collection'),
    ('handel', 'George Frideric Handel'),
    ('haydn', 'Joseph Haydn'),
    ('josquin', 'Josquin des Prez'),
    ('luca', 'D. Luca'),
    ('miscFolk', "Miscellaneous Folk"),
    ('monteverdi', "Claudio Monteverdi"),
    ('mozart', 'Wolfgang Amadeus Mozart'),
    ('oneills1850', 'Oneill\'s 1850'),
    ('ryansMammoth', 'Ryan\'s Mammoth Collection'),
    ('schoenberg', 'Arnold Schoenberg'),
    ('schumann', 'Robert Schumann'),
    ]

# instantiate an instance of each virtual work object in a module
# level constant; this object contains meta data about the work
VIRTUAL = []
for name in dir(virtual): # look over virtual module
    className = getattr(virtual, name)
    if callable(className):
        obj = className()
        if isinstance(obj, virtual.VirtualWork) and obj.corpusPath != None: # @UndefinedVariable
            VIRTUAL.append(obj)


#------------------------------------------------------------------------------


class CorpusException(exceptions21.Music21Exception):
    pass


#------------------------------------------------------------------------------
# core routines for getting file paths

# module-level cache; only higher-level functions cache results
_pathsCache = {}

# store temporary local paths added by a user in a session and not stored in
# Environment
_pathsLocalTemp = []


def getCorePaths(fileExtensions=None, expandExtensions=True):
    '''
    Get all paths in the corpus that match a known extension, or an extenion
    provided by an argument.

    If `expandExtensions` is True, a format for an extension, and related
    extensions, will replaced by all known input extensions.

    This is convenient when an input format might match for multiple
    extensions.

    ::

        >>> from music21 import corpus
        >>> corpusFilePaths = corpus.getCorePaths()
        >>> len(corpusFilePaths)
        3045

    ::

        >>> kernFilePaths = corpus.getCorePaths('krn')
        >>> len(kernFilePaths) >= 500
        True

    ::

        >>> abcFilePaths = corpus.getCorePaths('abc')
        >>> len(abcFilePaths) >= 100
        True

    '''
    return corpora.CoreCorpus().getPaths(
        fileExtensions=fileExtensions,
        expandExtensions=expandExtensions,
        )

def getVirtualPaths(fileExtensions=None, expandExtensions=True):
    '''
    Get all paths in the virtual corpus that match a known extension.

    An extension of None will return all known extensions.

    ::

        >>> from music21 import corpus
        >>> len(corpus.getVirtualPaths()) > 6
        True

    '''
    return corpora.VirtualCorpus().getPaths(
        fileExtensions=fileExtensions,
        expandExtensions=expandExtensions,
        )

def getLocalPaths(fileExtensions=None, expandExtensions=True):
    '''
    Access files in additional directories supplied by the user and defined in
    environment settings in the 'localCorpusSettings' list.

    If additional paths are added on a per-session basis with the
    :func:`~music21.corpus.addPath` function, these paths are also returned
    with this method.
    '''
    return corpora.LocalCorpus().getPaths(
        fileExtensions=fileExtensions,
        expandExtensions=expandExtensions,
        )


def addPath(filePath):
    '''
    Add a directory path to the Local Corpus on a *temporary* basis, i.e., just
    for the current Python session.

    All directories contained within the provided directory will be searched
    for files with file extensions matching the currently readable file types.
    Any number of file paths can be added one at a time.

    An error will be raised if the file path does not exist, is already defined
    as a temporary, or is already being searched by being defined with the
    :class:`~music21.environment.Environment` 'localCorpusSettings' setting.

    To permanently add a path to the list of stored local corpus paths,
    set the 'localCorpusPath' or 'localCorpusSettings' setting of
    the :class:`~music21.environment.UserSettings` object.

    ::

        >>> #_DOCS_SHOW corpus.addPath('~/Documents')

    Alternatively, add a directory permanently (see link above
    for more details):

    ::

        >>> #_DOCS_SHOW us = environment.UserSettings()
        >>> #_DOCS_SHOW us['localCorpusPath'] = 'd:/desktop/'

    Restart music21 after adding paths.
    '''
    if filePath is None or not os.path.exists(filePath):
        raise CorpusException(
            'an invalid file path has been provided: {0!r}'.format(filePath))
    if filePath in _pathsLocalTemp:
        raise CorpusException(
            'the provided path has already been added: {0!r}'.format(filePath))
    if filePath in environLocal['localCorpusSettings']:
        raise CorpusException(
            'the provided path is already incldued in the Environment '
            'localCorpusSettings: {0!r}'.format(filePath))

    _pathsLocalTemp.append(filePath)
    # delete all local keys in the cache
    for key in _pathsCache:
        if key[0] == 'local':
            del _pathsCache[key]


def getPaths(
    fileExtensions=None,
    expandExtensions=True,
    domain=('local', 'core', 'virtual'),
    ):
    '''
    Get paths from core, virtual, and/or local domains.
    This is the public interface for getting all corpus
    paths with one function.
    '''
    paths = []
    if 'local' in domain:
        paths += getLocalPaths(
            fileExtensions=fileExtensions,
            expandExtensions=expandExtensions,
            )
    if 'core' in domain:
        paths += corpora.CoreCorpus().getPaths(
            fileExtensions=fileExtensions,
            expandExtensions=expandExtensions,
            )
    if 'virtual' in domain:
        paths += getVirtualPaths(
            fileExtensions=fileExtensions,
            expandExtensions=expandExtensions,
            )
    return paths


#------------------------------------------------------------------------------
# metadata routines


def _updateMetadataBundle():
    '''
    Load the metadata bundle from JSON and store it in the module global
    variable _METADATA_BUNDLES, unless the _METADATA_BUNDLES have already been
    built, in which case, don't do it.

    This relies on the functions `getCorePaths()`, `getVirtualPaths()`, and
    `getLocalPaths()`.

    Note that this updates the in-memory cached metdata bundles not the disk
    caches (that's MUCH slower!) to do that run corpus.metadata.metadata.py
    '''
    corpora.CoreCorpus().updateMetadataBundle()
    corpora.LocalCorpus().updateMetadataBundle()
    corpora.VirtualCorpus().updateMetadataBundle()


def cacheMetadata(domainList=('local')):
    '''
    Rebuild the metadata cache.
    '''
    if not common.isListLike(domainList):
        domainList = [domainList]
    for domain in domainList:
        # remove any cached values
        corpora.Corpus._metadataBundles[domain] = None
    metadata.cacheMetadata(domainList)


def search(
    query,
    field=None,
    domain=('core', 'virtual', 'local'),
    fileExtensions=None,
    ):
    '''
    Search all stored metadata and return a list of file paths; to return a
    list of parsed Streams, use `searchParse()`.

    The `domain` parameter can be used to specify one of three corpora: core
    (included with music21), virtual (defined in music21 but hosted online),
    and local (hosted on the user's system (not yet implemented)).

    This method uses stored metadata and thus, on first usage, will incur a
    performance penalty during metadata loading.
    '''
    searchResults = []
    return corpora.Corpus.search(
        query,
        field=field,
        domain=domain,
        fileExtensions=fileExtensions,
        )


#------------------------------------------------------------------------------


def getComposer(composerName, fileExtensions=None):
    '''
    Return all filenames in the corpus that match a composer's or a
    collection's name. An `fileExtensions`, if provided, defines which
    extensions are returned. An `fileExtensions` of None (default) returns all
    extensions.

    Note that xml and mxl are treated equivalently.

    ::

        >>> a = corpus.getComposer('beethoven')
        >>> len(a) > 10
        True

    ::

        >>> a = corpus.getComposer('mozart')
        >>> len(a) > 10
        True

    ::

        >>> a = corpus.getComposer('bach', 'krn')
        >>> len(a) < 10
        True

    ::

        >>> a = corpus.getComposer('bach', 'xml')
        >>> len(a) > 10
        True

    '''
    paths = getPaths(fileExtensions)
    results = []
    for path in paths:
        # iterate through path components; cannot match entire string
        # composer name may be at any level
        stubs = path.split(os.sep)
        for stub in stubs:
            # need to remove extension if found
            if composerName.lower() == stub.lower():
                results.append(path)
                break
            # get all but the last dot group
            # this is done for file names that function like composer names
            elif '.' in stub and \
                '.'.join(stub.split('.')[:-1]).lower() == composerName.lower():
                results.append(path)
                break
    results.sort()
    return results


def getComposerDir(composerName):
    '''
    Given the name of a composer, get the path to the top-level directory of
    that composer:

    ::

        >>> import os
        >>> a = corpus.getComposerDir('beethoven')
        >>> a.endswith(os.path.join('corpus', os.sep, 'beethoven'))
        True

    ::

        >>> a = corpus.getComposerDir('bach')
        >>> a.endswith(os.path.join('corpus', os.sep, 'bach'))
        True

    ::

        >>> a = corpus.getComposerDir('mozart')
        >>> a.endswith(os.path.join('corpus', os.sep, 'mozart'))
        True

    '''
    return corpora.CoreCorpus().getComposerDirectoryPath(composerName)


@property
def noCorpus():
    '''
    Return True or False if this is a `corpus` or `noCoprus` distribution.

    ::

        >>> corpus.noCorpus
        False

    '''
    return corpora.CoreCorpus.noCorpus

#------------------------------------------------------------------------------


def getWorkList(workName, movementNumber=None, fileExtensions=None):
    '''
    Search the corpus and return a list of filenames of works, always in a
    list.

    If no matches are found, an empty list is returned.

    ::

        >>> len(corpus.getWorkList('beethoven/opus18no1'))
        8

    ::

        >>> len(corpus.getWorkList('beethoven/opus18no1', 1))
        2

    ::

        >>> len(corpus.getWorkList('beethoven/opus18no1', 1, '.krn'))
        1

    ::

        >>> len(corpus.getWorkList('beethoven/opus18no1', 1, '.xml'))
        1

    ::

        >>> len(corpus.getWorkList('beethoven/opus18no1', 0, '.xml'))
        0

    ::

        >>> len(corpus.getWorkList('handel/hwv56', '1-02', '.md'))
        1

    ::

        >>> len(corpus.getWorkList('handel/hwv56', (2,1), '.md'))
        1

    ::

        >>> len(corpus.getWorkList('bach/artOfFugue_bwv1080', 2, '.md'))
        1

    Make sure that 'verdi' just gets the single Verdi piece and not the
    Monteverdi pieces:

    ::

        >>> len(corpus.getWorkList('verdi'))
        1

    '''
    return corpora.CoreCorpus().getWorkList(
        workName,
        movementNumber=movementNumber,
        fileExtensions=fileExtensions,
        )


def getVirtualWorkList(workName, movementNumber=None, fileExtensions=None):
    '''
    Given a work name, search all virtual works and return a list of URLs for
    any matches.


    ::

        >>> from music21 import corpus
        >>> corpus.getVirtualWorkList('bach/bwv1007/prelude')
        ['http://kern.ccarh.org/cgi-bin/ksdata?l=cc/bach/cello&file=bwv1007-01.krn&f=xml']

    ::

        >>> corpus.getVirtualWorkList('junk')
        []

    '''
    if not common.isListLike(fileExtensions):
        fileExtensions = [fileExtensions]
    for obj in VIRTUAL:
        if obj.corpusPath != None and workName.lower() in obj.corpusPath.lower():
            return obj.getUrlByExt(fileExtensions)
    return []


#------------------------------------------------------------------------------


def getWorkReferences(sort=True):
    '''
    Return a data dictionary for all works in the corpus and (optionally) the
    virtual corpus. Returns a list of reference dictionaries, each each
    dictionary for a each composer. A 'works' dictionary for each composer
    provides references to dictionaries for all associated works.

    This is used in the generation of corpus documentation

    ::

        >>> post = corpus.getWorkReferences()

    '''
    # from music21 import corpus; corpus.getWorkReferences()
    # TODO: update this to use metadata
    results = []
    for composerDirectory, composer in corpora.CoreCorpus._composers:
        ref = {}
        ref['composer'] = composer
        ref['composerDir'] = composerDirectory
        ref['works'] = {}  # store by keys of name/dirname
        works = getComposer(composerDirectory)
        for path in works:
            # split by the composer dir to get relative path
            #environLocal.printDebug(['dir composer', composerDirectory, path])
            junk, fileStub = path.split(composerDirectory)
            if fileStub.startswith(os.sep):
                fileStub = fileStub[len(os.sep):]
            # break into file components
            fileComponents = fileStub.split(os.sep)
            # the first is either a directory for containing components
            # or a top-level name
            m21Format, ext = common.findFormatExtFile(fileComponents[-1])
            if ext is None:
                #environLocal.printDebug([
                #    'file that does not seem to have an extension',
                #    ext, path])
                continue
            # if not a file w/ ext, we will get None for format
            if m21Format is None:
                workStub = fileComponents[0]
            else:  # remove the extension
                workStub = fileComponents[0].replace(ext, '')
            # create list location if not already added
            if workStub not in ref['works']:
                ref['works'][workStub] = {}
                ref['works'][workStub]['files'] = []
                title = common.spaceCamelCase(workStub).title()
                ref['works'][workStub]['title'] = title
                ref['works'][workStub]['virtual'] = False
            # last component is name
            m21Format, ext = common.findFormatExtFile(fileComponents[-1])
            fileDict = {}
            fileDict['format'] = m21Format
            fileDict['ext'] = ext
            # all path parts after corpus
            fileDict['corpusPath'] = os.path.join(composerDirectory, fileStub)
            fileDict['fileName'] = fileComponents[-1]  # all after
            title = None
            # this works but takes a long time!
#             if format == 'musicxml':
#                 mxDocument = musicxml.Document()
#                 mxDocument.open(path)
#                 title = mxDocument.getBestTitle()
            if title is None:
                title = common.spaceCamelCase(
                    fileComponents[-1].replace(ext, ''))
                title = title.title()
            fileDict['title'] = title
            ref['works'][workStub]['files'].append(fileDict)
            # add this path
        results.append(ref)
    # get each VirtualWork object
    for vw in VIRTUAL:
        composerDir = vw.corpusPath.split('/')[0]
        match = False
        for ref in results:
            # check composer reference or first part of corpusPath
            if (ref['composer'] == vw.composer or
                composerDir == ref['composerDir']):
                match = True
                break  # use this ref
        if not match:  # new composers, create a new ref
            ref = {}
            ref['composer'] = vw.composer
            ref['composerDir'] = composerDir
            ref['works'] = {}  # store by keys of name/dirname
        # work stub should be everything other than top-level
        workStub = vw.corpusPath.replace(composerDir + '/', '')
        ref['works'][workStub] = {}
        ref['works'][workStub]['virtual'] = True
        ref['works'][workStub]['files'] = []
        ref['works'][workStub]['title'] = vw.title
        for url in vw.urlList:
            m21Format, ext = common.findFormatExtURL(url)
            fileDict = {}
            fileDict['format'] = m21Format
            fileDict['ext'] = ext
            # all path parts after corpus
            fileDict['corpusPath'] = vw.corpusPath
            fileDict['title'] = vw.title
            fileDict['url'] = url
            ref['works'][workStub]['files'].append(fileDict)
        if not match:  # not found already, need to add
            results.append(ref)
    if sort:
        sortGroup = []
        for ref in results:
            sortGroupSub = []
            for workStub in ref['works']:
                # add title first for sorting
                sortGroupSub.append([
                    ref['works'][workStub]['title'],
                    workStub,
                    ])
            sortGroupSub.sort()
            ref['sortedWorkKeys'] = [y for unused_x, y in sortGroupSub]
            # prepare this sort group
            sortGroup.append([ref['composerDir'], ref])
        sortGroup.sort()
        results = [ref for junk, ref in sortGroup]
    return results


#------------------------------------------------------------------------------


def getWork(workName, movementNumber=None, fileExtensions=None):
    '''
    Search the corpus, then the virtual corpus, for a work, and return a file
    path or URL.  N.B. does not parse the work: but it's suitable for passing
    to converter.parse.

    This method will return either a list of file paths or, if there is a
    single match, a single file path. If no matches are found an Exception is
    raised.

    ::

        >>> from music21 import corpus
        >>> import os
        >>> a = corpus.getWork('opus74no2', 4)
        >>> a.endswith(os.path.sep.join([
        ...     'haydn', 'opus74no2', 'movement4.mxl']))
        True

    ::

        >>> a = corpus.getWork(['haydn', 'opus74no2', 'movement4.xml'])
        >>> a.endswith(os.path.sep.join([
        ...     'haydn', 'opus74no2', 'movement4.mxl']))
        True

    ::

        >>> trecentoFiles = corpus.getWork('trecento')
        >>> len(trecentoFiles) > 100 and len(trecentoFiles) < 200
        True

    '''
    if not common.isListLike(fileExtensions):
        fileExtensions = [fileExtensions]
    results = getWorkList(workName, movementNumber, fileExtensions)
    if len(results) == 0:
        if common.isListLike(workName):
            workName = os.path.sep.join(workName)
        if workName.endswith(".xml"):  # might be compressed MXL file
            newWorkName = workName[0:len(workName) - 4] + ".mxl"
            return getWork(newWorkName, movementNumber, fileExtensions)
        results = getVirtualWorkList(workName, movementNumber, fileExtensions)
    if len(results) == 1:
        return results[0]
    elif len(results) == 0:
        raise CorpusException(
            'Could not find a file/url that met these criteria')
    return results


def parse(
    workName,
    movementNumber=None,
    number=None,
    fileExtensions=None,
    forceSource=False,
    ):
    '''
    The most important method call for corpus.

    Similar to the :meth:`~music21.converter.parse` method of converter (which
    takes in a filepath on the local hard drive), this method searches the
    corpus (including the virtual corpus) for a work fitting the workName
    description and returns a :class:`music21.stream.Stream`.

    If `movementNumber` is defined, and a movement is included in the corpus,
    that movement will be returned.

    If `number` is defined, and the work is a collection with multiple
    components, that work number will be returned.  For instance, some of our
    ABC documents contain dozens of folk songs within a single file.

    Advanced: if `forceSource` is True, the original file will always be loaded
    freshly and pickled (e.g., pre-parsed) files will be ignored.  This should
    not be needed if the file has been changed, since the filetime of the file
    and the filetime of the pickled version are compared.  But it might be
    needed if the music21 parsing routine has changed.

    Example, get a chorale by Bach.  Note that the source type does not need to
    be specified, nor does the name Bach even (since it's the only piece with
    the title BWV 66.6)

    ::

        >>> from music21 import corpus
        >>> bachChorale = corpus.parse('bwv66.6')
        >>> len(bachChorale.parts)
        4

    After parsing, the file path within the corpus is stored as
    `.corpusFilePath`

    ::

        >>> bachChorale.corpusFilepath
        u'bach/bwv66.6.mxl'

    '''
    return corpora.Corpus.parse(
        workName,
        movementNumber=movementNumber,
        number=number,
        fileExtensions=fileExtensions,
        forceSource=forceSource,
        )


def _addCorpusFilepath(streamObj, filePath):
    # metadata attribute added to store the file path,
    # for use later in identifying the score
    #if streamObj.metadata == None:
    #    streamObj.insert(metadata.Metadata())
    corpusFilePath = common.getCorpusFilePath()
    lenCFP = len(corpusFilePath) + len(os.sep)
    if filePath.startswith(corpusFilePath):
        fp2 = filePath[lenCFP:]
        ### corpus fix for windows
        dirsEtc = fp2.split(os.sep)
        fp3 = '/'.join(dirsEtc)
        streamObj.corpusFilepath = fp3
    else:
        streamObj.corpusFilepath = filePath


def parseWork(*arguments, **keywords):
    '''
    This function exists for backwards compatibility.

    All calls should use :func:`~music21.corpus.parse` instead.
    '''
    import warnings
    warnings.warn(
        'the corpus.parseWork() function is deprecated: use corpus.parse()',
        DeprecationWarning,
        )
    return parse(*arguments, **keywords)


#------------------------------------------------------------------------------
# compression


def compressAllXMLFiles(deleteOriginal=False):
    '''
    Takes all filenames in corpus.paths and runs
    :meth:`music21.corpus.compressXML` on each.  If the musicXML files are
    compressed, the originals are deleted from the system.
    '''
    environLocal.warn("Compressing musicXML files...")
    for filename in getPaths(fileExtensions=('.xml',)):
        compressXML(filename, deleteOriginal=deleteOriginal)
    environLocal.warn(
        'Compression complete. '
        'Run the main test suite, fix bugs if necessary,'
        'and then commit modified directories in corpus.'
        )


def compressXML(filename, deleteOriginal=False):
    '''
    Takes a filename, and if the filename corresponds to a musicXML file with
    an .xml extension, creates a corresponding compressed .mxl file in the same
    directory.

    If deleteOriginal is set to True, the original musicXML file is deleted
    from the system.
    '''
    if not filename.endswith('.xml'):
        return  # not a musicXML file
    environLocal.warn("Updating file: {0}".format(filename))
    filenameList = filename.split(os.path.sep)
    # find the archive name (name w/out filepath)
    archivedName = filenameList.pop()
    # new archive name
    filenameList.append(archivedName[0:len(archivedName) - 4] + ".mxl")
    newFilename = os.path.sep.join(filenameList)  # new filename
    # contents of container.xml file in META-INF folder
    container = '<?xml version="1.0" encoding="UTF-8"?>\n\
<container>\n\
  <rootfiles>\n\
    <rootfile full-path="{0}"/>\n\
  </rootfiles>\n\
</container>\n\
    '.format(archivedName)
    # Export container and original xml file to system as a compressed XML.
    with zipfile.ZipFile(
        newFilename,
        'w',
        compression=zipfile.ZIP_DEFLATED,
        ) as myZip:
        myZip.write(filename=filename, archivedName=archivedName)
        myZip.writestr(
            zinfo_or_archivedName='META-INF{0}container.xml'.format(
                os.path.sep),
            bytes=container,
            )
    # Delete uncompressed xml file from system
    if deleteOriginal:
        os.remove(filename)


def uncompressMXL(filename, deleteOriginal=False):
    '''
    Takes a filename, and if the filename corresponds to a compressed musicXML
    file with an .mxl extension, creates a corresponding uncompressed .xml file
    in the same directory.

    If deleteOriginal is set to True, the original compressed musicXML file is
    deleted from the system.
    '''
    if not filename.endswith(".mxl"):
        return  # not a musicXML file
    environLocal.warn("Updating file: {0}".format(filename))
    filenames = filename.split(os.path.sep)
    # find the archive name (name w/out filepath)
    archivedName = filenames.pop()

    unarchivedName = os.path.splitext(archivedName)[0] + '.xml'
    extractPath = os.path.sep.join(filenames)
    # Export container and original xml file to system as a compressed XML.
    with zipfile.ZipFile(
        filename,
        'r',
        compression=zipfile.ZIP_DEFLATED,
        ) as myZip:
        myZip.extract(member=unarchivedName, path=extractPath)
    # Delete uncompressed xml file from system
    if deleteOriginal:
        os.remove(filename)


#------------------------------------------------------------------------------
# libraries


# additional libraries to define


def getBachChorales(fileExtensions='xml'):
    ur'''
    Return the file name of all Bach chorales.

    By default, only Bach Chorales in xml format are returned, because the
    quality of the encoding and our parsing of those is superior.

    N.B. Look at the module corpus.chorales for many better ways to work with
    the chorales.

    ::

        >>> from music21 import corpus
        >>> a = corpus.getBachChorales()
        >>> len(a) > 400
        True

    ::

        >>> a = corpus.getBachChorales('krn')
        >>> len(a) > 10
        False

    ::

        >>> a = corpus.getBachChorales('xml')
        >>> len(a) > 400
        True

    ::

        >>> #_DOCS_SHOW a[0]
        >>> u'/Users/cuthbert/Documents/music21/corpus/bach/bwv1.6.mxl' #_DOCS_HIDE
        u'/Users/cuthbert/Documents/music21/corpus/bach/bwv1.6.mxl'

    '''
    return corpora.CoreCorpus().getBachChorales(
        fileExtensions=fileExtensions,
        )

#bachChorales = property(getBachChorales)


def getHandelMessiah(fileExtensions='md'):
    '''
    Return a list of the filenames of all parts of Handel's Messiah.


    ::

        >>> from music21 import corpus
        >>> a = corpus.getHandelMessiah()
        >>> len(a)
        43

    '''
    return corpora.CoreCorpus().getHandelMessiah(
        fileExtensions=fileExtensions,
        )


def getMonteverdiMadrigals(fileExtensions='xml'):
    '''
    Return a list of the filenames of all Monteverdi madrigals.

    ::

        >>> from music21 import corpus
        >>> a = corpus.getMonteverdiMadrigals()
        >>> len(a) > 40
        True

    '''
    return corpora.CoreCorpus().getMonteverdiMadrigals(
        fileExtensions=fileExtensions,
        )


def getBeethovenStringQuartets(fileExtensions=None):
    '''
    Return a list of all Beethoven String Quartet filenames.

    ::

        >>> from music21 import corpus
        >>> a = corpus.getBeethovenStringQuartets()
        >>> len(a) > 10
        True

    ::

        >>> a = corpus.getBeethovenStringQuartets('krn')
        >>> len(a) < 10 and len(a) > 0
        True

    ::

        >>> a = corpus.getBeethovenStringQuartets('xml')
        >>> len(a) > 400
        False

    '''
    return corpora.CoreCorpus().getBeethovenStringQuartets(
        fileExtensions=fileExtensions,
        )


#------------------------------------------------------------------------------
# define presented order in documentation


_DOC_ORDER = [parse, getWork]


if __name__ == "__main__":
    import music21
    music21.mainTest()


#------------------------------------------------------------------------------
# eof
