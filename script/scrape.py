import datetime
import os
from typing import Any, Dict, List

import bs4
import numpy as np
import pandas as pd
import pytz
import requests
from bs4 import BeautifulSoup
from cfg.urls import url

ny_tz = pytz.timezone('US/Eastern')


class MATOME_WALKER:

    def __init__(self):
        self.ranking_until = 10
        self.titles = None
        self.links = None
        self.comment_until = 20
        date = datetime.datetime.now(ny_tz)
        self.save_path = f"db/{date.strftime('%Y_%m_%d')}/"
        os.makedirs(self.save_path, exist_ok=True)

    def exec(self):
        self._title_get()
        for ind_rank in range(self.ranking_until):
            dic_page = self._page_get(ind_rank)
            self._save(ind_rank, dic_page)

    def _title_get(self) -> None:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        titles = np.empty(self.ranking_until, dtype=object)
        links = np.empty(self.ranking_until, dtype=object)
        for rank in range(self.ranking_until):
            title = soup.select("body > div.wrap.flc > div.main > div.topic-list-wrap > ul.topic-list > li:nth-of-type({}) > a".format(rank + 1))[0].find('p', class_='title').contents[0].encode('cp932', errors='ignore').decode('cp932').replace('\u3000', '')
            link = soup.select("body > div.wrap.flc > div.main > div.topic-list-wrap > ul.topic-list > li:nth-of-type({}) > a".format(rank + 1))[0].attrs['href']
            links[rank] = url + link
            titles[rank] = title
        self.titles = titles
        self.links = links

    def _page_get(self, ind_rank) -> Dict:
        page_url = self.links[ind_rank]
        res = requests.get(page_url)
        soup = BeautifulSoup(res.text, 'html.parser')
        dic_page = {}
        for comment_ind in range(self.comment_until):
            selected_soup = self._soup_select(soup, comment_ind+1)
            if selected_soup:
                filtered_sentence = self._sentence_filter(selected_soup)
                if filtered_sentence:
                    comment_single = self._clean_sentence(filtered_sentence)
                    validity = True
                else:
                    comment_single = ''
                    validity = False
            else:
                comment_single = ''
                validity = False
            dic_page[str(comment_ind+1)] = {}
            dic_page[str(comment_ind+1)]['comment'] = comment_single
            dic_page[str(comment_ind+1)]['valid'] = validity
        return dic_page

    def _save(self, ind_rank, dic_comment) -> None:
        rank_theme = f"rank_{ind_rank}_meta.csv"
        rank_comment = f"rank_{ind_rank}_comment.csv"
        pd.DataFrame.from_dict({
            'title': [self.titles[ind_rank]],
            'link': [self.links[ind_rank]],
        }).to_csv(f"{self.save_path}{rank_theme}", index=False)
        pd.DataFrame.from_dict(dic_comment, orient='index').to_csv(f"{self.save_path}{rank_comment}", index=False)

    @staticmethod
    def _soup_select(soup, comment_ind):
        if not soup.select(f"#comment{comment_ind}"):
            return None
        else:
            cout = 1
            while (not soup.select(f"#comment{comment_ind}")[0].find('div', class_=f"body lv{cout}")):
                cout += 1
                if cout >= 5:
                    return None
            return soup.select(f"#comment{comment_ind}")[0].find('div', class_=f"body lv{cout}").contents[:]

    @staticmethod
    def _sentence_filter(list_contents):
        comment_type = bs4.element.NavigableString
        remove_keywords = [
            '\n',
            ' ',
        ]
        res = [i for i in list_contents if type(i) == comment_type]
        if not res:
            return None
        else:
            res = [i for i in res if i not in remove_keywords]
            if res:
                return res
            else:
                return None

    @staticmethod
    def _clean_sentence(before_cleaned_sentence):
        return [i[:-1] for i in before_cleaned_sentence]
