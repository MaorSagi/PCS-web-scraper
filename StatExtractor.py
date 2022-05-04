import pandas as pd
from Extractor import Extractor
from utils import *
from consts import *
from bs4 import BeautifulSoup, NavigableString
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import numpy as np

from unidecode import unidecode
from datetime import datetime


class StatExtractor(Extractor):
    def __init__(self, id=id):
        super().__init__(id=id)


    def fetch_stats(self,years_range=range(2010, 2023),):



        soup = self.browser.get(RANKINGS_URL).soup
        soup_dates = soup.find("select", {"name": "date"}).find_all("option")
        dates = []
        for soup_date in soup_dates:
            date = soup_date.text
            if int(date.split("-")[0]) < min_year:
                break
            dates.append(date)

        def pcs_points_links(date, offset):
            return f"https://www.procyclingstats.com/rankings.php?date={date}&nation=&age=&zage=&page=smallerorequal&team=&offset={offset}&teamlevel=&filter=Filter"

        def uci_points_links(date, offset):
            return f"https://www.procyclingstats.com/rankings.php?date={date}&nation=&age=&zage=&page=smallerorequal&team=&offset={offset}&continent=&teamlevel=&filter=Filter&p=me&s=uci-individual"

        def extract_points(pcs):

            def get_link(date, offset):
                if pcs:
                    return pcs_points_links(date, offset)
                else:
                    return uci_points_links(date, offset)

            res = []
            printProgressBar(0, len(dates), prefix='Progress:', suffix='Complete', length=50)
            i = 0
            for date in dates:
                browser.get(get_link(date, 0))
                soup = BeautifulSoup(browser.page_source, 'html.parser')

                soup_offests = soup.find("select", {"name": "offset"}).find_all("option")
                offsets = []
                for soup_offest in soup_offests:
                    offsets.append(int(soup_offest.text.split("-")[0]) - 1)

                for offset in offsets:
                    browser.get(get_link(date, offset))
                    soup = BeautifulSoup(browser.page_source, 'html.parser')
                    head_lines = [item.text for item in soup.find("thead").find_all("th")]
                    table = soup.find("tbody").find_all("tr")

                    for row in table:
                        new_data = {}
                        columns = row.find_all("td")
                        for i in range(len(columns)):
                            if head_lines[i] == "#":
                                new_data["rank"] = int(columns[i].text)
                            elif head_lines[i] == "Rider":
                                name = columns[i].text
                                new_data["cyclist_name"] = f"{name}".strip().lower()
                            elif head_lines[i] == "Team":
                                new_data["team_name"] = columns[i].find("a").text.strip()
                            elif head_lines[i] == "Points":
                                new_data["points"] = columns[i].find("a").text
                        new_data["date"] = datetime.strptime(date, "%Y-%m-%d")
                        # print(new_data)
                        res.append(new_data)

                i += 1
                printProgressBar(i, len(dates), prefix='Progress:', suffix='Complete', length=50)

            return res

        print("===== Extracting PCS points =====")
        print()
        pcs_points = extract_points(pcs=True)
        print()
        print("===== Extracting UCI points =====")
        print()
        uci_points = extract_points(pcs=False)

        pcs_df = pd.DataFrame(pcs_points)
        uci_df = pd.DataFrame(uci_points)

        print(len(pcs_df))
        print(len(uci_df))

        pcs_df.to_csv("pcs_df.csv")
        uci_df.to_csv("uci_df.csv")

        pcs_df.rename(columns={"rank": "pcs_rank", "points": "pcs_points"})
        uci_df.rename(columns={"rank": "uci_rank", "points": "uci_points"})

        cyclists = get_all_to_df(CyclistModel)[["cyclist_id", "full_name"]].rename(
            columns={"full_name": "cyclist_name"})
        cyclists["cyclist_name"] = cyclists["cyclist_name"].str.lower()

        teams = get_all_to_df(TeamModel)[["team_id", "team_name"]]
        cyclist_ranking = get_all_to_df(CyclistRankingModel)

        # Apply unicode
        cyclists["cyclist_name"] = cyclists["cyclist_name"].apply(unidecode)
        teams["team_name"] = teams["team_name"].apply(unidecode)

        # add cyclists_id and team_id to data
        if len(pcs_df) > 0:
            pcs_df["cyclist_name"] = pcs_df["cyclist_name"].apply(unidecode)
            pcs_df["team_name"] = pcs_df["team_name"].apply(unidecode)

            pcs_df = pd.merge(pcs_df, cyclists, on="cyclist_name", how="inner")
            pcs_df = pd.merge(pcs_df, teams, on="team_name", how="inner")

            # remove duplicates
            pcs_df = pd.merge(pcs_df, cyclist_ranking, on=["cylist_id", "team_id", "date"], how="outer", indicator=True)
            pcs_df = pcs_df[pcs_df['_merge'] == 'left_only']
            pcs_df = pcs_df.drop("_merge", 1)

        if len(uci_df) > 0:
            uci_df["cyclist_name"] = uci_df["cyclist_name"].apply(unidecode)
            uci_df["team_name"] = uci_df["team_name"].apply(unidecode)

            uci_df = pd.merge(uci_df, cyclists, on="cyclist_name", how="inner")
            uci_df = pd.merge(uci_df, teams, on="team_name", how="inner")

            # remove duplicates
            uci_df = pd.merge(uci_df, cyclist_ranking, on=["cylist_id", "team_id", "date"], how="outer", indicator=True)
            uci_df = uci_df[uci_df['_merge'] == 'left_only']
            uci_df = uci_df.drop("_merge", 1)

        print(f"There are {pcs_df} new pcs scores")
        print(f"There are {uci_df} new uci scores")

        # upload_df(pcs_df, 'cyclists_rankings')
        # upload_df(uci_df, 'cyclists_rankings')

