from pysummarization.nlpbase.auto_abstractor import AutoAbstractor
from pysummarization.tokenizabledoc.simple_tokenizer import SimpleTokenizer
from pysummarization.abstractabledoc.top_n_rank_abstractor import TopNRankAbstractor
from datetime import datetime, timedelta
from pymongo import MongoClient
from gnews import GNews
import json
import os

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
            link = article["url"]
            full_article = google_news.get_full_article(link)

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
                "Link" : link,
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