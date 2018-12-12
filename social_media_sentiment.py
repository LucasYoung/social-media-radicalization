import re 
import tweepy 
from tweepy import OAuthHandler 
from textblob import TextBlob 
import praw
from praw.models import MoreComments
import pandas as pd
import datetime as dt
import math
import urllib.request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import statistics
import matplotlib.pyplot as pyplot
import json

'''
    TODOs
        Look at replies to comments rather than top level comments?
        Reddit search by query rather than subreddit
        Save the most polarized comments
        Save means/stdevs to reject/fail to reject null hypothesis
        Analyze subjectivity
        Save data in json
        Measure engagement
'''


def parse_configs():
    try:
        read_file = open("configs.json", "r")
        return json.load(read_file)

    except FileNotFoundError:
        raise

def clean_text(text): 
    ''' 
    Utility function to clean tweet text by removing links, special characters 
    using simple regex statements. 
    '''
    return ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", text).split()) 


# Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# tab of
#   https://cloud.google.com/console
# Please ensure that you have enabled the YouTube Data API for your project.
DEVELOPER_KEY = 'AIzaSyAlvsuOqwUDPaByMnJiHF19pmD-IKx3rs0'
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

def youtube_search(configs, queries, count):
    comments = []

    youtube = build(configs['youtube_api_service_name'], configs['youtube_api_version'],
        developerKey=configs['youtube_key'])

    for query in queries:
        sqrt = math.sqrt(count)

        # Call the search.list method to retrieve results matching the specified
        # query term.
        search_response = youtube.search().list(
            q=query,
            part='id,snippet',
            maxResults=math.ceil(sqrt)
        ).execute()

        videos = []
        channels = []
        playlists = []

        # Add each result to the appropriate list, and then display the lists of
        # matching videos, channels, and playlists.
        for search_result in search_response.get('items', []):
            if search_result['id']['kind'] == 'youtube#video':
                id = search_result['id']['videoId']
                comments += get_youtube_comments(youtube, id)
    
    return comments


def get_youtube_comments(youtube, video_id):
    try:
        comments = []
        response = youtube.commentThreads().list(
            part = "snippet",
            videoId = video_id
        ).execute()

        for item in response["items"]:
            comment = item["snippet"]["topLevelComment"]
            comments.append(comment["snippet"]["textOriginal"])
        
        return comments
    except HttpError:
        return []

class RedditClient(object):

    def __init__(self, configs):
        self.reddit = praw.Reddit(client_id=configs['reddit_client_id'],
                        client_secret=configs['reddit_client_secret'],
                        user_agent=configs['reddit_user_agent'],
                        username=configs['reddit_username'],
                        password=configs['reddit_password'])


    def get_comments(self, subreddits, count):
        comments = []

        for subreddit_name in subreddits:
            subreddit = self.reddit.subreddit(subreddit_name)
            sqrt = math.sqrt(count)
            top_subreddit = subreddit.top(limit=math.ceil(sqrt))

            for submission in top_subreddit:
                counter = 0
                for comment in submission.comments:
                    if isinstance(comment, MoreComments):
                        continue
                    else:
                        if counter > sqrt:
                            break
                        comments.append(comment.body)
                        counter += 1

        return comments


class TwitterClient(object): 
    ''' 
    Generic Twitter Class for sentiment analysis. 
    '''
    def __init__(self, configs): 
        ''' 
        Class constructor or initialization method. 
        '''
        # keys and tokens from the Twitter Dev Console 
        consumer_key = configs['twitter_consumer_key']
        consumer_secret = configs['twitter_consumer_secret']
        access_token = configs['twitter_access_token']
        access_token_secret = configs['twitter_access_token_secret']

        # attempt authentication 
        try: 
            # create OAuthHandler object 
            self.auth = OAuthHandler(consumer_key, consumer_secret) 
            # set access token and secret 
            self.auth.set_access_token(access_token, access_token_secret) 
            # create tweepy API object to fetch tweets 
            self.api = tweepy.API(self.auth) 
        except: 
            print("Error: Authentication Failed") 


    def get_tweets(self, queries, count): 
        ''' 
        Main function to fetch tweets and parse them. 
        '''
        # empty list to store parsed tweets 
        tweets = []

        try: 
            # call twitter api to fetch tweets 
            for query in queries:
                fetched_tweets = self.api.search(q = query, count = count)
                tweets += [clean_text(tweet.text) for tweet in fetched_tweets]
            
            return tweets

        except tweepy.TweepError as e: 
            # print error (if any) 
            print("Error : " + str(e)) 

class AggregateData(object):
    def __init__(self):
        pass

comments_of_interest = []

def aggregate_data(comments):

    for comment in comments:
        tb = TextBlob(comment).sentiment.polarity
        if (abs(tb) > 0.95):
            comments_of_interest.append(comment)

    polarities = [abs(TextBlob(comment).sentiment.polarity) for comment in comments]

    mean = statistics.mean(polarities)
    stdev = statistics.stdev(polarities)
    print("μ =", mean, ", σ =", stdev, ", n =", len(comments))

    pyplot.hist(polarities, bins=10, range=(0.00, 1.00))
    pyplot.show()

def main(): 

    controversial_queries = ["Donald Trump", "Hillary Clinton", 
        "Alexandria Ocasio-Cortez", "Brett Kavanaugh", "Abortion", "Mueller"]

    configs = parse_configs()

    print("getting youtube comments")
    youtube_comments = youtube_search(
        configs,
        queries = controversial_queries, 
        count = 50
    )

    aggregate_data(youtube_comments)

    print("getting reddit comments")
    reddit_client = RedditClient(configs)
    reddit_comments = reddit_client.get_comments(
        subreddits = ['politics', 'the_donald', 'latestagecapitalism', 
            'conservative', 'sandersforpresident', 'asktrumpsupporters'],
        count = 50
    )

    aggregate_data(reddit_comments)

    print("getting twitter comments")
    # creating object of TwitterClient Class 
    twitter_client = TwitterClient(configs) 
    # calling function to get tweets 
    tweets = twitter_client.get_tweets(
        queries = controversial_queries,
        count = 50
    )

    aggregate_data(tweets)

    print(comments_of_interest)

if __name__ == "__main__": 
    # calling main function 
    main() 
