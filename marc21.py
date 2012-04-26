import types
import string

#-- Version 1.0.1
#-- November 1, 2000
#-- Due to a recent discovery (thanks to Sue Trombley) that MARC21 records
#-- can have multiple instances of both fields and subfields, I've changed
#-- the MARC21Record and MARC21DataField classes to handle this.
#-- Now, the fields of a MARC21Record can either be a single instance or
#-- a list of instances of the MARC21DataField class.  Similarly for the
#-- subfields.  The contents of M['450']['a'] may be a single string or
#-- a list of strings.

def safeint(s):
    return int(s) if s.isdigit() else 0

class MARC21Record:
    FIELD_TERMINATOR=chr(30)
    RECORD_TERMINATOR=chr(29)

    def __init__(self,data=None):
        self.dataFields={}
        self.record_status=' '
        self.type_of_record=' '
        self.implementation_defined1='  '
        self.character_coding_scheme=' '
        self.implementation_defined2='   '

        #-- "constants" according to the MARC21 standard.
        self.entry_map='4500'
        self.indicator_count=2
        self.subfield_code_length=2

        if data is not None:
            self.parse(data)

    def parse(self,data):
        #-- Extract the leader from the data.
        leaderData=data[:24]
        data=data[24:]

        try:
            #-- Read the fields in the leader and modify the state of the object.
            lengthOfRecord=int(leaderData[:5])
            self.record_status=leaderData[5]
            self.type_of_record=leaderData[6]
            self.implementation_defined1=leaderData[7:9]
            self.character_coding_scheme=leaderData[9]
            self.indicator_count=safeint(leaderData[10])
            self.subfield_code_length=safeint(leaderData[11])
            baseAddressOfData=int(leaderData[12:17])
            self.implementation_defined2=leaderData[17:20]
            self.entry_map=leaderData[20:24]
        except:
            print leaderData
            raise
        #-- Now, read the remaining data until a FIELD_TERMINATOR.
        #-- This data will be the directory.
        FTindex=string.find(data,MARC21Record.FIELD_TERMINATOR)
        directoryData=data[:FTindex]
        data=data[FTindex+1:]

        #-- Parse the directory.
        directory={}
        while len(directoryData)>0:
            directoryEntry=directoryData[:12]
            tag=directoryData[:3]
            fieldLength=int(directoryData[3:7])
            fieldOffset=int(directoryData[7:12])
            if directory.has_key(tag):
                if type(directory[tag])==type([]):
                    directory[tag].append((fieldLength,fieldOffset))
                else:
                    directory[tag]=[directory[tag],(fieldLength,fieldOffset)]
            else:
                directory[tag]=(fieldLength,fieldOffset)
            directoryData=directoryData[12:]

        #-- Now, use the directory to read in the following data.
        for tag in directory.keys():
            directoryEntries=[]
            if type(directory[tag])==type([]):
                directoryEntries=directory[tag]
            else:
                directoryEntries=[directory[tag]]
            for directoryEntry in directoryEntries:
                fieldLength,fieldOffset=directoryEntry
                fieldData=data[fieldOffset:fieldOffset+fieldLength]
                if tag[:2]=='00':
                    taggedData=fieldData[:-1]
                else:
                    taggedData=MARC21DataField(fieldData)
                if self.dataFields.has_key(tag):
                    if type(self.dataFields[tag])==type([]):
                        self.dataFields[tag].append(taggedData)
                    else:
                        self.dataFields[tag]=[self.dataFields[tag],taggedData]
                else:
                    self.dataFields[tag]=taggedData
    def fields(self):
        return self.dataFields.keys()

    def __getitem__(self,tag):
        return self.dataFields[tag]

    def __setitem__(self,tag,value):
        if tag[:2]=='00':
            if type(value)!=types.StringType:
                #-- 00x tags are control fields.  They have no subfields,
                #-- so their data type is just a string.
                raise Exception("Control fields are of type String")
            else:
                self.dataFields[tag]=value
        else:
            if isinstance(value,MARC21DataField):
                self.dataFields[tag]=value
            else:
                #-- Fields that are not control fields *MUST* have a subfield.
                #-- Thus, the proper assignment is {'subfield1':'data1',...}
                #-- ie. {'a','Proper Title'}
                raise Exception("Data fields must be of type MARC21DataField")

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        #-- Serialize all of the data fields and build the directory.
        data=""
        directory={}
        sortedFields=self.dataFields.keys()
        sortedFields.sort()
        for field in sortedFields:
            if type(self.dataFields[field])==type([]):
                contentList=self.dataFields[field]
            else:
                contentList=[self.dataFields[field]]
            for content in contentList:
                offset=len(data)
                if field[:2]=='00':
                    serializedField=content+MARC21Record.FIELD_TERMINATOR
                else:
                    serializedField='%s'%(content)
                length=len(serializedField)
                if directory.has_key(field):
                    directory[field].append((length,offset))
                else:
                    directory[field]=[(length,offset)]
                data=data+serializedField

        #-- Add the record terminator.
        data=data+MARC21Record.RECORD_TERMINATOR

        #-- Now, serialize the directory.
        directoryData=""
        for field in sortedFields:
            for directoryEntry in directory[field]:
                length,offset=directoryEntry
                directoryData=directoryData+"%3s%04d%05d"%(field[:3],length,offset)
        directoryData=directoryData+MARC21Record.FIELD_TERMINATOR

        recordLength=24+len(directoryData)+len(data)
        baseAddressOfData=24+len(directoryData)
        leaderData="%05d"%(recordLength)
        leaderData=leaderData+self.record_status[:1]
        leaderData=leaderData+self.type_of_record[:1]
        leaderData=leaderData+self.implementation_defined1[:2]
        leaderData=leaderData+self.character_coding_scheme[:1]
        leaderData=leaderData+"%01d"%(self.indicator_count)
        leaderData=leaderData+"%01d"%(self.subfield_code_length)
        leaderData=leaderData+"%05d"%(baseAddressOfData)
        leaderData=leaderData+self.implementation_defined2[:3]
        leaderData=leaderData+self.entry_map[:4]

        return leaderData+directoryData+data

class MARC21DataField:
    SUBFIELD_DELIMITER=chr(31)

    def __init__(self,data=None):
        self.indicator1=' '
        self.indicator2=' '
        self.contents={}

        if data is not None:
            self.parse(data)

    def subfields(self):
        return self.contents.keys()

    def __getitem__(self,subfield):
        return self.contents[subfield]

    def __setitem__(self,subfield,value):
        self.contents[subfield]=value

    def parse(self,data):
        #-- Read the indicators.
        self.indicator1=data[0]
        self.indicator2=data[1]
        data=data[3:]
        #-- Strip the FIELD_DELIMITER
        data=data[:-1]
        while len(data)>0:
            SDindex=string.find(data,MARC21DataField.SUBFIELD_DELIMITER)
            if SDindex<0:
                SDindex=len(data)
            subfieldData=data[:SDindex]
            data=data[SDindex+1:]
            if not subfieldData:
                continue
            if self.contents.has_key(subfieldData[0]):
                if type(self.contents[subfieldData[0]])==type([]):
                    self.contents[subfieldData[0]].append(subfieldData[1:])
                else:
                    self.contents[subfieldData[0]]=[self.contents[subfieldData[0]],subfieldData[1:]]
            else:
                self.contents[subfieldData[0]]=subfieldData[1:]

    def __str__(self):
        data=self.indicator1[0]+self.indicator2[0]
        sortedSubfields=self.contents.keys()
        sortedSubfields.sort()
        for subfield in sortedSubfields:
            if type(self.contents[subfield])==type([]):
                contentList=self.contents[subfield]
            else:
                contentList=[self.contents[subfield]]
            for content in contentList:
                data=data+MARC21DataField.SUBFIELD_DELIMITER+subfield+content
        data=data+MARC21Record.FIELD_TERMINATOR
        return data

class MARC21File:
    def __init__(self,filename):
        self.index=[0]
        self.current=0
        self.sourceFile=open(filename,'rb')

    def __del__(self):
        self.sourceFile.close()

    def next(self):
        data=self.sourceFile.read(5)
        if data=="":
            return None
        else:
            recordLength=int(data)
            data=data+self.sourceFile.read(recordLength-5)
            self.current=self.current+1
            self.index.append(self.sourceFile.tell())
            return MARC21Record(data)

    def rewind(self, n=1):
        self.current=self.current-n
        if self.current<0:
            self.current=0
        self.sourcefile.seek(self.index[self.current])

def isControlField(tag):
    if tag[:2]=='00':
        return 1
    else:
        return 0

def MARC21PrettyPrint(M):
    sortedFields=M.fields()
    sortedFields.sort()
    for field in sortedFields:
        contentList=[]
        if type(M[field])==type([]):
            contentList=M[field]
        else:
            contentList=[M[field]]
        for content in contentList:
            print field
            if isControlField(field):
                print '\t%s'%(content)
            else:
                subfields=content.subfields()
                subfields.sort()
                for subfield in subfields:
                    if type(content[subfield])==type([]):
                        subfieldContentList=content[subfield]
                    else:
                        subfieldContentList=[content[subfield]]
                    for subfieldContent in subfieldContentList:
                        print '\t%s : %s'%(subfield,subfieldContent)
