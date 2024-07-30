from pysummarization.nlpbase.auto_abstractor import AutoAbstractor
from pysummarization.tokenizabledoc.simple_tokenizer import SimpleTokenizer
from pysummarization.abstractabledoc.top_n_rank_abstractor import TopNRankAbstractor
from datetime import datetime, timedelta
from pymongo import MongoClient
from gnews import GNews
import json
import os
import requests
import base64

def fetch_decoded_batch_execute(id):
    s = (
        '[[["Fbv4je","[\\"garturlreq\\",[[\\"en-US\\",\\"US\\",[\\"FINANCE_TOP_INDICES\\",\\"WEB_TEST_1_0_0\\"],'
        'null,null,1,1,\\"US:en\\",null,180,null,null,null,null,null,0,null,null,[1608992183,723341000]],'
        '\\"en-US\\",\\"US\\",1,[2,3,4,8],1,0,\\"655000234\\",0,0,null,0],\\"'
        + id
        + '\\"]",null,"generic"]]]'
    )

    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        "Referer": "https://news.google.com/",
    }

    response = requests.post(
        "https://news.google.com/_/DotsSplashUi/data/batchexecute?rpcids=Fbv4je",
        headers=headers,
        data={"f.req": s},
    )

    if response.status_code != 200:
        raise Exception("Failed to fetch data from Google.")

    text = response.text
    header = '[\\"garturlres\\",\\"'
    footer = '\\",'
    if header not in text:
        raise Exception(f"Header not found in response: {text}")
    start = text.split(header, 1)[1]
    if footer not in start:
        raise Exception("Footer not found in response.")
    url = start.split(footer, 1)[0]
    return url


def decode_google_news_url(source_url):
    url = requests.utils.urlparse(source_url)
    path = url.path.split("/")
    if url.hostname == "news.google.com" and len(path) > 1 and path[-2] == "articles":
        base64_str = path[-1]
        decoded_bytes = base64.urlsafe_b64decode(base64_str + "==")
        decoded_str = decoded_bytes.decode("latin1")

        prefix = b"\x08\x13\x22".decode("latin1")
        if decoded_str.startswith(prefix):
            decoded_str = decoded_str[len(prefix) :]

        suffix = b"\xd2\x01\x00".decode("latin1")
        if decoded_str.endswith(suffix):
            decoded_str = decoded_str[: -len(suffix)]

        bytes_array = bytearray(decoded_str, "latin1")
        length = bytes_array[0]
        if length >= 0x80:
            decoded_str = decoded_str[2 : length + 2]
        else:
            decoded_str = decoded_str[1 : length + 1]

        if decoded_str.startswith("AU_yqL"):
            return fetch_decoded_batch_execute(base64_str)

        return decoded_str
    else:
        return source_url


def scrapper(language, country, max_results):
    today = datetime.now()
    tom = today + timedelta(days=1)

    path = os.path.join(os.getcwd(), "data")

    # object of automatatic scrapping
    google_news = GNews(language=language, country=country, max_results=max_results)

    # set parameters
    google_news.start_date = (today.year, today.month, today.day)
    google_news.end_date = (tom.year, tom.month, tom.day)

    topics = ["WORLD", "NATION", "BUSINESS", "TECHNOLOGY", "ENTERTAINMENT", "SPORTS", "SCIENCE", "HEALTH"]
    all_results = []

    for topic in topics:
        articles = google_news.get_news_by_topic(topic=topic)

        for article in articles:
            source_url = article["url"]
            decoded_url = decode_google_news_url(source_url)
            full_article = google_news.get_full_article(decoded_url)

            if full_article == None:
                continue

            try:
                getattr(full_article, "text")
                text = full_article.text
            except AttributeError:
                continue

            try:
                getattr(full_article, "text")
                img = full_article.top_image
            except AttributeError:
                img = None

            # object of automatic summarization
            auto_abstractor = AutoAbstractor()

            # set tokenizer
            auto_abstractor.tokenizable_doc = SimpleTokenizer()

            # set delimiter for making a list of sentence
            auto_abstractor.delimiter_list = [".", "\n"]

            # object of abstracting and filtering document
            abstractable_doc = TopNRankAbstractor()

            # summarize document
            result_dict = auto_abstractor.summarize(text, abstractable_doc)

            description = ""
            sentences = 0

            for sentence in result_dict["summarize_result"]:
                description += sentence
                sentences += 1

                if sentences > 1:
                    break

            if description == "":
                continue

            date_obj = datetime.strptime( article['published date'], "%a, %d %b %Y %H:%M:%S %Z")
            news = {
                "Category" : topic,
                "Title" : article['title'],
                "Publisher" : article['publisher'],
                "Published_Date" : date_obj,
                "Description" : description,
                "Link" : decoded_url,
                "Image" : img,
            }

            all_results.append(news)

    MONGO_URL = os.getenv("MONGO_URL")
    conn = MongoClient(MONGO_URL)
    db = conn.NewsBits        
    collection = db.news_data
    collection.insert_many(all_results)
        

if __name__ == "__main__":
    language = 'en'
    country = 'IN'
    max_results = 5
    scrapper(language=language, country=country, max_results=max_results)