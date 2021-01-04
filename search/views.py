import requests
import math
import os
import json
from django.conf import settings
from django.shortcuts import render
from whoosh.index import create_in
from whoosh.fields import *
from .forms import SortMethod
from django.views.decorators.cache import cache_control, never_cache
from django.http import HttpResponseRedirect
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.paginator import Paginator

# from .read_stopword import stopword


# index_schema = Schema(user = TEXT(stored=True),
#                 likeCount = NUMERIC(stored=True),
#                 content = TEXT(stored=True),
#                 url = ID(stored=True)
#                 )

# index_dir = "indexdir/"
# if not os.path.exists(index_dir):
#     os.mkdir(index_dir)
# ix = create_in(index_dir, index_schema)
# index_writer = ix.writer()

session_key = ''


# Create your views here.
@cache_control(no_cache=True, must_revalidate=False, no_store=True)
def index(request):
    # print(stopword)

    search_url = 'https://www.googleapis.com/youtube/v3/search'
    video_url = 'https://www.googleapis.com/youtube/v3/videos'
    comment_url = 'https://www.googleapis.com/youtube/v3/commentThreads'
    channel_url = 'https://www.googleapis.com/youtube/v3/channels'

    form = SortMethod()
    err_message = ''
    comments = []
    channel = ''
    searchTerms = ''
    sort = ''
    channelID = ''
    context = {
        'comments': [],
        'form': form,
        'err_message': err_message
    }

    if request.method == 'POST':
        form = SortMethod(request.POST)
        if form.is_valid():
            channel = form.cleaned_data['channel']
            searchTerms = form.cleaned_data['comment']
            sort = form.cleaned_data['sort']

    elif request.GET.get('channel', '') and request.GET.get('searchTerms', ''):
        channel = request.GET['channel']
        searchTerms = request.GET['searchTerms']

    if channel != '' and searchTerms != '':
        getChannel_params = {
            'part': 'id',
            'forUsername': channel,  # 'ChinaSNH48',
            'key': settings.YOUTUBE_API_KEY
        }

        r = requests.get(channel_url, params=getChannel_params)
        channelID = r.json().get('items')

        if channelID == None:
            if r.json().get('pageInfo') != None:
                err_message = 'Channel Name Not Found'
                context = {
                    'comments': [],
                    'form': form,
                    'err_message': err_message
                }
                return render(request, 'search/index.html', context)

            else:
                err_message = 'Network Problem!'
                context = {
                    'comments': [],
                    'form': form,
                    'err_message': err_message
                }
                return render(request, 'search/index.html', context)

        else:
            channelID = channelID[0]['id']

        comment_params = {
            'part': 'snippet',
            'allThreadsRelatedToChannelId': channelID,
            'searchTerms': searchTerms,
            'order': 'time',
            'maxResults': 100,
            'key': settings.YOUTUBE_API_KEY
        }

        r = requests.get(comment_url, params=comment_params)

        comment_results = r.json().get('items')
        if comment_results == None:
            err_message = 'Network Problem!'
            context = {
                'comments': [],
                'form': form,
                'err_message': err_message
            }
            return render(request, 'search/index.html', context)

        if len(comment_results) == 0:
            err_message = 'Comments Not Found!'
            context = {
                'comments': [],
                'form': form,
                'err_message': err_message
            }
            return render(request, 'search/index.html', context)

        if 'nextPageToken' in r.json():
            nextPageToken = r.json()['nextPageToken']
        else:
            nextPageToken = ''

        for comment in comment_results:
            comment_data = {
                'comment': comment['snippet']['topLevelComment']['snippet']['textDisplay'],
                'video': comment['snippet']['topLevelComment']['snippet'].get('videoId'),
                'likeCount': comment['snippet']['topLevelComment']['snippet']['likeCount']
            }
            # index_writer.add_document(user = comment['snippet']['topLevelComment']['snippet']['authorDisplayName'],
            # 					likeCount = comment['snippet']['topLevelComment']['snippet']['likeCount'],
            # 					content = comment['snippet']['topLevelComment']['snippet']['textDisplay'],
            # 					url = comment['snippet']['topLevelComment']['snippet'].get('videoId'))
            comments.append(comment_data)

        while nextPageToken != '':
            comment_params.update({'pageToken': nextPageToken})
            r = requests.get(comment_url, params=comment_params)

            if 'nextPageToken' in r.json():
                nextPageToken = r.json()['nextPageToken']
            else:
                nextPageToken = ''

            comment_results = r.json().get('items')
            if comment_results is not None:
                for comment in comment_results:
                    comment_data = {
                        'comment': comment['snippet']['topLevelComment']['snippet']['textDisplay'],
                        'video': comment['snippet']['topLevelComment']['snippet'].get('videoId'),
                        'likeCount': comment['snippet']['topLevelComment']['snippet']['likeCount']
                    }
                    # index_writer.add_document(user = comment['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                    # 			likeCount = comment['snippet']['topLevelComment']['snippet']['likeCount'],
                    # 			content = comment['snippet']['topLevelComment']['snippet']['textDisplay'],
                    # 			url = comment['snippet']['topLevelComment']['snippet'].get('videoId'))
                    comments.append(comment_data)

        # index_writer.commit()
        # index_searcher = ix.searcher()
        # results = index_searcher.find("content", "tako")
        # for i in results:
        # 	print(i)

        comments = calculateRelevance(comments, list(searchTerms.split(" ")))
        if sort == 'like':
            comments = sorted(comments, key=lambda i: i['like_score'], reverse=True)
        elif sort == 'relevance':
            comments = sorted(comments, key=lambda i: i['score'], reverse=True)
        else:
            comments = sorted(comments, key=lambda i: i['score'] * i['like_score'], reverse=True)

        # count = 0
        # for comment in comments :
        # 	print(str(count) + ' ' + comment['comment'])
        # 	print(str(comment['video']) + ' ' + str(comment['score']) + ' ' + str(comment['like_score']) + ' ' + str(comment['like_score'] * comment['score']) + '\n')
        # 	count += 1

        # top_comments = comments[:9]

        # for i in range(len(comments)) :
        # 	video_params = {
        # 		'part' : 'snippet',
        # 		'key' : settings.YOUTUBE_API_KEY,
        # 		'id' : comments[i]['video']
        # 	}
        # 	r = requests.get(video_url, params = video_params, verify=False)
        # 	result = r.json()['items'][0]
        # 	img = result['snippet']['thumbnails']['high']['url']
        # 	title = result['snippet']['title']
        # 	comments[i].update({'thumbnail' : img})
        # 	comments[i].update({'title' : title})

        # context = {
        # 	'comments' : comments,
        # 	#'form' : form
        # }
        s = SessionStore()
        s['searchTerms'] = searchTerms
        s['comments'] = comments
        s['channel'] = channel
        s.create()
        global session_key
        session_key = s.session_key

        return HttpResponseRedirect("/result")

    # print(sort)

    return render(request, 'search/index.html', context)


def calculateRelevance(comments, query_terms):
    collection_length = 0
    gamma = 0.9
    score_list = [1 for i in range(len(comments))]
    likes_list = []

    for i in comments:
        tmp = 0
        likes_list.append(i['likeCount'])
        # t = list(i['comment'].split(" "))
        # for word in t :
        # 	if word.lower() not in stopword :       #ignore stopwords
        # 		tmp += 1
        collection_length = collection_length + len(list(i['comment'].split(" ")))

    for term in query_terms:
        doc_f = []
        terms_f = 0
        tf = 0
        for i in comments:
            f = 0
            for word in list(i['comment'].lower().split(" ")):
                if term.lower() in word:
                    tf = tf + 1
                    f = f + 1
            doc_f.append(f / len(list(i['comment'].split(" "))))
        terms_f = tf / collection_length

        for i in range(len(comments)):
            score = gamma * terms_f + (1 - gamma) * doc_f[i]
            # score_list.append(score)
            score_list[i] = score_list[i] * score

    for i in range(len(comments)):
        comments[i].update({'score': (score_list[i] - min(score_list)) / (max(score_list) - min(score_list))})
        comments[i].update({'like_score': (likes_list[i] - min(likes_list) + 1) / (max(likes_list) - min(likes_list))})

    return comments


def result(request):
    global session_key
    s = SessionStore(session_key=session_key)
    comments = s['comments']
    form = SortMethod()
    channel = s['channel']
    searchTerms = s['searchTerms']
    sort = ''

    if request.GET.get('sort', ''):
        if request.GET['sort'] == 'default':
            sort = 'default'
            comments = sorted(comments, key=lambda i: i['score'] * i['like_score'], reverse=True)
        elif request.GET['sort'] == 'relevance':
            sort = 'relevance'
            comments = sorted(comments, key=lambda i: i['score'], reverse=True)
        else:
            sort = 'like'
            comments = sorted(comments, key=lambda i: i['like_score'], reverse=True)

    if request.method == 'POST':
        # print("Post The Form!!!")
        form = SortMethod(request.POST)
        if form.is_valid():
            channel = form.cleaned_data['channel']
            searchTerms = form.cleaned_data['comment']
            # print(form.cleaned_data)
            Session.objects.all().delete()
            return HttpResponseRedirect("/?" + "&channel=" + channel + "&searchTerms=" + searchTerms)

    paginator = Paginator(comments, 9)  # Show 9 contacts per page
    page = request.GET.get('page')
    comments_page = paginator.get_page(page)

    context = {
        'comments': comments_page,  # comments[:9],
        'form': form,
        'sort': sort,
        'searchTerms': searchTerms,
        'channel': channel
    }

    return render(request, 'search/result.html', context)

# 1. result.html页面为drop down list绑定onClick事件，点击后附带sort参数链接到‘/result’
# 2. view.result中取得form的channel，comment字段值后附带query字段跳转到/index
# 3. view.result先判断是否有query参数
# 4. view.index判断是否有query参数
