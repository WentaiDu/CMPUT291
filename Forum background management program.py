#----------------------------------------------------
# Mini Project II
#
# Author: Jinglong ,Wentai ,Weitong
# Collaborators:
# References:
#----------------------------------------------------

import pymongo
from pymongo import MongoClient
import datetime
import json
import sys
import re

client = None
db = None

class selfExitError(Exception):
    """Use to exit program safely"""
    pass

def cursorPrinter(cursor):
    """
    -- cursor cursor object
    print cursor out
    return False if nothing print
    """
    i = 0
    for item in cursor:
        for key in item.keys():
            if key != "_id":
                print(key,end="")
                print(": ",end="")
                print(item[key])
                i+=1
    if i == 0:
        return False
    return True

class User:
    def __init__(self,userId):
        '''
        self.userId current user's uid
        self.questionId is the id of current select question, if not selected it is None
        self.answerId is the id of current select answer, if not selected it is None
        '''
        global client, db
        print("Initializing system...")

        self.userId = userId
        self.questionId = None
        self.answerId = None
        if userId == None:
            userId = "Unregistered"

        print("\tCreating Index... please wait...")
        self.create_index()
        print("{:=^100}".format(" User %s "%userId))

    def create_index(self):
        '''
        create index for posts to get ready for search function
        '''
        length = 0
        for index in db.Posts.list_indexes():
            length+=1
        if length > 1:
            db.Posts.drop_indexes()

        db.Posts.create_index(
           [("terms", "text"),("Tags", "text")], name = "search_index"
        )

    def promptpostAction(self):
        '''
        prompt a question action and go to the question action function
        raise selfExitError if terminate
        '''
        print("You have select: ",end ="")
        is_question = True
        if self.answerId != None:
            is_question = False

        print("please select a post action: ")
        if is_question:
            action = (input('\tAnswer(An)\n\tList answers(La)\n\tVote(V)\n\tBack to menu(m)\n\tterminate program(t)\n')).lower()
        else:
            action = (input("\tVote(V)\n\tBack to selected question(b)\n\tBack to menu(m)\n\tterminate program(t)\n")).lower()

        if action == "an" and is_question:
            self.qAnswer()
        elif action == "v":
            if is_question:
                self.qaVote(self.questionId)
            else:
                self.qaVote(self.answerId)
        elif action == "la" and is_question :
            self.qListAnswers()
        elif action == "b" and not is_question:
            self.answerId = None
        elif action == "m":
            self.questionId = None
            self.answerId = None
        elif action == "t":
            raise selfExitError()
        else:
            print('invalid input!')


    def promptAction(self):
        '''
        prompt for actions
        raise selfExitError if terminate
        '''

        print("Please select an action: \n\tpost a question(p)\n\tsearch for questions(s)\n\tterminate program(t)")
        action = input('Action: ')

        if action == 'p':
            self.postQuestion()
        elif action == 's':
            self.questionId = self.Search()

            while self.questionId != None:
                try:
                    self.promptpostAction()
                except selfExitError:
                    raise selfExitError("terminate")
                except Exception as error:
                    print(error)
        elif action == 't':
            raise selfExitError("terminate")

    def tablePrinter(self,printList,page):
        '''
        Use to print table of search result
        '''
        print("\n")
        keyList = ["Title","CreationDate","Score","AnswerCount"]
        formatt = "|{0:^7}|{1:^61}|{2:^25}|{3:^7}|{4:^13}|"
        number =  len(formatt.format("index",*keyList))
        header = "{:=^%ds}"%number
        print(header.format(" Page%d "%page))
        print(formatt.format("index",*keyList))
        print("-"*number)

        for i in range(0,len(printList)):
            result = []
            for key in keyList:
                result.append(printList[i][key])
            print(formatt.format(i,result[0][:61],result[1][:25],str(result[2])[:7],str(result[3])[:13]))
            print("-"*number)

    def postPrinter(self,postId):
        '''
        use to print a single post
        '''
        cursor = db.Posts.find({"Id": postId})
        print("{:=^100}".format("Information"))
        cursorPrinter(cursor)
        print("="*100)

    def Search(self):
        '''
        search main loop
        return selected id of question (string)
        '''
        keyWords = input("what do you want to search? (use space(' ') to split keywords): ")
        x = input("How many items do you want per page? (invalid input will be changed to 5): ")
        if x.isdigit():
            x = int(x)
        else:
            x = 5

        # get title, body, or tag
        # title, the creation date, the score, and the answer count.
        cursor = db.Posts.aggregate(
           [
             { "$match": { "$text": { "$search": keyWords.lower(), "$caseSensitive": False} } },
             { "$match": {"PostTypeId": "1"}},
             { "$project": { "_id": 0, "Id": 1, "Title": 1, "CreationDate": 1, "Score":  1, "AnswerCount":  1 } }
           ]
        )
        resultList = []
        for item in cursor:
            resultList.append(item)

        assert resultList != [], 'No related item! --- Going back'

        choose = None
        page = 0
        lastpage = False
        while choose == None:
            page += 1
            partList = []

            if len(resultList) < x:
                x = len(resultList)
                lastpage = True

            for i in range(x):
                partList.append(resultList.pop(0))
            self.tablePrinter(partList,page)

            while True:
                if lastpage:
                    action = (input("This is the last page! Select a question by enter index. Enter (b) to go back. :")).lower()
                else:
                    action = (input("Select a question by enter index. Enter (s) to see more. Enter (b) to go back. :")).lower()

                if action == 's' and not lastpage:
                    print("\n")
                    break
                elif action == 'b':
                    raise Exception("--- Going back")
                elif action.isdigit():
                    if int(action) in range(x):
                        choose = partList[int(action)]["Id"]
                        break
                else:
                    print("invalid input. Please enter again.")


        print("successfully select this question. Information below: ")
        self.postPrinter(choose)
        db.Posts.update_one({'Id': choose}, {'$inc': {'ViewCount': 1}})

        cursor.close()
        return choose


    def get_id(self,collectionName):
        """get largest Id"""
        idList = []
        cursor = db[collectionName].find()

        for item in cursor:
            idList.append(int(item['Id']))
        idList.sort(reverse=True)

        id = str(idList[0]+1)
        cursor.close()
        return id

    def check_tags(self,tagName):
        """check tags in Tags"""
        a=[]
        cursor = db.Tags.find({"TagName": tagName})
        for item in cursor:
            a.append(item)
        return a == []

    def postQuestion(self):
        tag_list=[]
        #Prompt the player to enter a question
        Title=input('Please enter a title that you want to enter: ')
        Body=input('Please enter a body that you want to enter : ')
        while True:
            action=input("Press (e) to add a tag or (f) to finish: ")
            if action =='f':
                break
            elif action =='e':
                tag=input('enter a tag name: ')
                if tag not in tag_list:
                    tag_list.append(tag)
            else:
                print("Invalid input!")

        tags = ""
        for tag in tag_list:
            tags += '<'+tag+'>'
        print("Posting question...")

        Id = self.get_id("Posts")
        data={"Id": Id,\
            "PostTypeId":"1",\
            "AcceptedAnswerId":None,\
            "CreationDate":datetime.datetime.now().isoformat(),\
            "Score":0,\
            "ViewCount":0,\
            "Body":Body,\
            "LastEditorUserId":"Anonymous",\
            "LastEdit":datetime.datetime.now().isoformat(),\
            "LastActivityDate":datetime.datetime.now().isoformat(),\
            "Title":Title,\
            "Tags":tags,\
            "AnswerCount":0,\
            "CommentCount":0,\
            "FavoriteCount":0,\
            "ContentLicense":"CC BY-SA 2.5"}
        if self.userId != None:
            data["OwnerUserId"] = self.userId

        temp = [data]
        extraction_terms(temp)

        db.Posts.insert_one(data)
        self.create_index()

        for tag in tag_list:
            if self.check_tags(tag):
                tag_Id = self.get_id("Tags")
                tag_data={"Id":tag_Id,\
                        "TagName":tag,\
                        "Count":1,\
                        "ExcerptPostId": Id,\
                        "WikiPostId": str(int(Id)-1)}
                db.Tags.insert_one(tag_data)
            else:
                db.Tags.update_one({ "TagName": tag },{ "$inc": { "Count": 1 } })

        print("Successfully posted the question.")



    def qAnswer(self):
        """User posts answer base on the question that we have selected"""
        #get user input
        Body = input('Please answer question: ')
        #format the data
        #Set ID self-increment
        print("Posting answer...")

        Id = self.get_id("Posts")
        data={"Id": Id,\
                "PostTypeId":"2",\
                "ParentId":self.questionId,\
                "CreationDate":datetime.datetime.now().isoformat(),\
                "Score":0,\
                "Body":Body,\
                "LastActivityDate":datetime.datetime.now().isoformat(),\
                "CommentCount":0,\
                "ContentLicense":"CC BY-SA 2.5"}
        if self.userId != None:
            data["OwnerUserId"] = self.userId
        #insert the data
        temp = [data]
        extraction_terms(temp)
        db.Posts.insert_one(data)
        self.create_index()
        #Success message

        print("Successfully posted the answer.")


    def qListAnswers(self):
        #find answers of the selected question
        #find the accepted answer
        answers = []

        question = db.Posts.find({"Id":self.questionId})
        for item in question:
            if "AcceptedAnswerId" in item.keys():
                accepted_id = item["AcceptedAnswerId"]
                accepted_answer = db.Posts.find({"Id":accepted_id})
                for aanswer in accepted_answer:
                    aanswer['Body'] = '*' + aanswer['Body']
                    answers.append(aanswer)

        #firstly add accepted answer to the list
        cursor = db.Posts.find({"ParentId":self.questionId},{ "_id": 0, "Id":1,"Body": 1,"CreationDate":1,"Score":1})
        for answer in cursor:
        #check that the accepted answer is not added again
            if len(answers) != 0:
                if answer["Id"] != answers[0]["Id"]:
                    answers.append(answer)
            else:
                answers.append(answer)

        assert len(answers) != 0, "No answer related to this question."
        choose = None

        keyList = ["Body","CreationDate","Score"]
        formatt = "|{0:^7}|{1:^80}|{2:^61}|{3:^25}|"
        number =  len(formatt.format("index",*keyList))
        header = "{:=^%ds}"%number
        print(header.format(" Answers "))
        print(formatt.format("index",*keyList))
        print("-"*number)

        for i in range(0,len(answers)):
            printList = []
            for key in keyList:
                printList.append(answers[i][key])
            text = re.sub(r'[^\w\s]','',printList[0])
            print(formatt.format(i,text[:80],printList[1][:61],str(printList[2])[:25]))
            print("-"*number)

        while True:
            action = (input("Select an answer by enter index. Enter (b) to go back. :")).lower()
            if action == 'b':
                raise Exception("--- Going back")
            elif action.isdigit():

                if int(action) in range(len(answers)):
                    choose = answers[int(action)]["Id"]
                    break
            else:
                print("invalid input. Please enter again.")

        print("successfully select this answer. Information below: ")
        self.answerId = choose

    def qaVote(self,postId):
        """
        -- postId is the id of current selected post
        vote on a post
        """
        print("Voting...")
        if self.userId != None:
            cursor = db.Votes.find({"$and":[{"PostId":postId},{"UserId":self.userId}]})
            for item in cursor:
                raise Exception('You have already voted this one, can not vote again')
        #record vote
        Id = self.get_id("Votes")
        data={"Id": Id,\
                "PostId": postId,\
                "VoteTypeId":"2",\
                "CreationDate":datetime.datetime.now().isoformat(),\
                }
        if self.userId != None:
            data["UserId"] = self.userId
        #insert the data
        db.Votes.insert_one(data)
        #update the score by 1 in posts_collection
        db.Posts.update_one({'Id': postId}, {'$inc': {'Score': 1}})
        print("you have successfully voted!")


###############################################################
def connectToDB():
    '''
    Connect to Database and set global variables
    '''
    global client, db
    port = input("please enter a mango client port: ")
    port = int(port)
    client = MongoClient('localhost', port)
    db = client["291db"]
    print("successfully connect to port %s. Database set to 291db."%port)

def extraction_terms (data):
    '''
    -- data is a list include many dictionaries
    add key "terms" into each dictionary, which value is extracted terms
    '''
    global client, db

    for each in data:
        extractList = list()
        titleList = list()
        bodyList = list()
        try:
            text = each["Title"]
            titleList = text.split(" ")
        except Exception:
            pass
        try:
            text = each["Body"]
            text = re.sub(r"<.*?>", "", text)
            text = re.sub(r'[^\w\s]','',text)
            text = text.replace("\n","").replace("\t","").replace("\r","")
            bodyList = text.split(" ")
        except Exception:
            pass
        for wordList in [titleList,bodyList]:
            for item in wordList:
                if len(item) >= 3:
                    extractList.append(item.lower())

        each['terms'] = list(set(extractList))

def buildCollections():
    '''
    Phrase 1 setup collections
    '''
    global client, db
    collist = db.list_collection_names()

    for fileName in ["Posts","Votes","Tags"]:
        print("Initializing collection %s..."%fileName)
        collist = db.list_collection_names()
        if fileName in collist:
            print("\tThe collection exists. Dropping it...")
            db.drop_collection(fileName)
            print("\t\tSuccessfully drop it")

        print("\tCreating collection %s... please wait..."%fileName)
        currentCollection = db[fileName]
        try:
            with open(fileName+".json",'r') as file:
                print("\t\tLoading data...")
                fileData = json.load(file)
                insideData = fileData[fileName.lower()]["row"]
                if fileName == "Posts":
                    print("\t\tExtraction terms...")
                    extraction_terms(insideData)
                print("\t\tInserting data...")
                currentCollection.insert_many(insideData)
                file.close()
        except FileNotFoundError as error:
            sys.exit("--- Creating failed. %s Please check the file, program ends."%error)

        print("\tSuccessfully create Collection %s.\n"%fileName)

    return

def generate_report(userId):
    '''
    generate and print report
    '''
    global client, db
    print("{:=^100}".format(" User Report "))

    # the number of questions owned and the average score for those questions
    cursor = db.Posts.aggregate([{"$match": {"OwnerUserId": userId,"PostTypeId":"1"}},
    {"$group" : {"_id": {"user": "$OwnerUserId"},"Number of Questions Owned": {"$sum" : 1},"Average Score": {"$avg": "$Score"}}}])
    result = cursorPrinter(cursor)
    if not result:
        print("Number of Questions Owned: 0")
        print("Average Score: 0")
    print("\n")

    # the number of answers owned and the average score for those answers
    cursor = db.Posts.aggregate([{"$match": {"OwnerUserId": userId,"PostTypeId":"2"}},
    {"$group" : {"_id": {"user": "$OwnerUserId"},"Answers Owned": {"$sum" : 1},"Average Score": {"$avg": "$Score"}}}])
    result = cursorPrinter(cursor)
    if not result:
        print("Answers Owned: 0")
        print("Average Score: 0")
    print("\n")

    # the number of votes registered for the user
    cursor = db.Posts.aggregate([{"$match": {"OwnerUserId": userId}},
    {"$project" : {"_id": {"user": "$OwnerUserId"}, "postId": "$Id"}}])
    idList = []
    for item in cursor:
        idList.append(item["postId"])

    cursor = db.Votes.aggregate([{"$match": {"PostId": { "$in": idList }}},
    {"$group" : {"_id": {"user": "$OwnerUserId"}, "Number of Votes": {"$sum" : 1}}}])
    result = cursorPrinter(cursor)

    if not result:
        print("Number of Votes: 0")
    print("\n")

    cursor.close()
    print("{:=^100}".format(" Report Ends "))

def userReport():
    '''
    prompt for an user id
    '''
    global client, db
    while True:
        userId = input("Please enter your user id or s to skip this process: ")
        if userId.lower() == "s":
            return
        elif not userId.isdigit():
            print("Invalid input. User id is a numeric field")
        else:
            print("Generating report...")
            try:
                generate_report(userId)
            except Exception as error:
                print(error)
            return userId

def main():
    global client, db
    try:
        connectToDB()
        buildCollections()

        userId = userReport()
        user = User(userId)
    except Exception:
        sys.exit("Initializing fail. ends.")
    while True:
        try:
            user.promptAction()
        except selfExitError:
            break
        except Exception as error:
            print(error)

    client.close()
    print("Exit successfully, have a nice day.")


if __name__ == "__main__":
    main()
