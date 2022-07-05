import pandas as pd

from StageExtractor import StageExtractor
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

    def _is_stat_exists(self, stat_record):
        stats_df = None
        path = get_file_path_with_new_suffix(CSV_PATHS['cyclists_stats'], self.id, 'csv')
        if os.path.exists(path):
            stats_df = pd.read_csv(path)
        if stats_df is None:
            return False
        stat_exist_pred = (stats_df['cyclist_id'] == stat_record['cyclist_id'])
        date = datetime.strftime(stat_record['date'], "%Y-%m-%d")
        stat_exist_pred = stat_exist_pred & (stats_df['date'] == date)
        stat_exist_pred = stat_exist_pred & (stats_df['speciality_type'] == stat_record['speciality_type'])
        result_df = stats_df[stat_exist_pred]
        if result_df.empty:
            return False
        return True


    def handle_missing_stages_results(self, stage, stage_url, cyclist_name, cyclist_url):
        missing_cyclist_result = dict(stage_name_pcs=stage.text, cyclist_name_pcs=cyclist_name, stage_link=stage_url,
                                      cyclist_link=cyclist_url)
        path = get_file_path_with_new_suffix(MISSING_RESULTS_PATH, self.id, 'csv')
        cols = ['stage_name_pcs', 'cyclist_name_pcs', 'stage_link', 'cyclist_link']
        if os.path.exists(path):
            is_result_exists_df = pd.read_csv(path)
            is_result_exists_df = is_result_exists_df[
                (is_result_exists_df['stage_link'] == stage_url) & (is_result_exists_df['cyclist_link'] == cyclist_url)]
            if is_result_exists_df.empty:
                append_row_to_csv(path, missing_cyclist_result,
                                  cols)
        else:
            append_row_to_csv(path, missing_cyclist_result,
                              cols)
        msg = f'Missing result of {cyclist_name} stage {stage_url}'
        log(msg, 'WARNING', id=self.id)

    def handle_missing_stages(self, stage, stage_url):
        missing_stage = dict(stage_name_pcs=stage.text, stage_link=stage_url)
        path = get_file_path_with_new_suffix(MISSING_STAGES_PATH, self.id, 'csv')
        if os.path.exists(path):
            if stage_url not in pd.read_csv(path)['pcs_link'].values:
                append_row_to_csv(path, missing_stage,
                                  ['stage_name_pcs', 'stage_link'])
        else:
            append_row_to_csv(path, missing_stage,
                              ['stage_name_pcs', 'stage_link'])
        msg = f'Missing stage {stage_url}'
        log(msg, 'WARNING', id=self.id)

    def fetch_speciality_stats(self, cyclists_df, cyclist_last=None, years_range=range(2016, 2023)):

        continue_last_session_pred = cyclist_last is None
        for idx, cyclist in cyclists_df.iterrows():
            try:
                cyclist_id = cyclist['cyclist_id']
                cyclist_url = cyclist['pcs_link']
                if (not continue_last_session_pred) and cyclist_url != cyclist_last:
                    continue
                continue_last_session_pred = True
                msg = f'cyclist {cyclist_url}'
                log(msg, 'INFO', id=self.id)
                for stats_points_type in SPECIALITY_POINTS_TYPES:
                    try:
                        url_suffix = SPECIALITY_POINTS_TYPES[stats_points_type]
                        cyclist_url_career = f"{cyclist_url}/results/{url_suffix}"
                        msg = f'cyclist {cyclist_id} {stats_points_type} points, {cyclist_url_career}'
                        log(msg, id=self.id)
                        cyclist_page = self.browser.get(cyclist_url_career).soup

                        # Table Headers
                        points_table = cyclist_page.find('table', attrs={'class': 'basic'})
                        table_headers = points_table.find("thead").find_all("th")
                        headers_text = [t.text for t in table_headers]

                        # Table Records
                        table_rows = points_table.find("tbody").find_all("tr")

                        i = 0
                        while i < len(table_rows) - 1:
                            row = table_rows[i]
                            record = dict(cyclist_id=cyclist_id,speciality_type=stats_points_type)
                            row_values = [td.text for td in row.find_all("td")]
                            for j in range(len(row_values)):
                                if headers_text[j] == "Date":
                                    record['date'] = datetime.strptime(row_values[j], "%Y-%m-%d")
                                    if not record['date'].year in years_range:
                                        break
                                elif headers_text[j] == "Points":
                                    record['points'] = float(row_values[j])
                                elif headers_text[j] == "Race":
                                    link_suffix = row.find('a')['href']
                                    stage_link = f"{PCS_BASE_URL}/{link_suffix}".replace('startlist/preview',
                                                                                         '').replace('/result',
                                                                                                     '').replace(
                                        '/startlist', '')
                                    stage = StageExtractor.get_stage_from_link(stage_link)
                                    if stage is not None:
                                        record['stage_id'] = stage['stage_id']
                                        record['race_id'] = stage['race_id']
                                        stage_cyclist_result = StageExtractor.get_stage_result_from_link(
                                            record['stage_id'], cyclist_id)
                                        if stage_cyclist_result is not None:
                                            record['result_id'] = stage_cyclist_result['result_id']
                                        else:
                                            self.handle_missing_stages_results(row.find_all("td")[j], stage_link,
                                                                               cyclist['cyclist_name_pcs'], cyclist_url)
                                    else:
                                        self.handle_missing_stages(row.find_all("td")[j], stage_link)

                            if record['date'].year in years_range:
                                if not self._is_stat_exists(record):
                                    path = get_file_path_with_new_suffix(CSV_PATHS['cyclists_stats'], self.id, 'csv')
                                    append_row_to_csv(path, record, columns=SPECIALITY_COLS)
                            i += 1


                    except:
                        msg = f'Failed to parse cyclist {cyclist_id} {stats_points_type} stats - {cyclist_url}.'
                        log(msg, 'ERROR', id=self.id)
                        continue
            except:
                msg = f'Failed to parse cyclist stats - {cyclist_url}.'
                log(msg, 'ERROR', id=self.id)
                continue

        # soup = self.browser.get(RANKINGS_URL).soup
        # soup_dates = soup.find("select", {"name": "date"}).find_all("option")
        # dates = []
        # for soup_date in soup_dates:
        #     date = soup_date.text
        #     if int(date.split("-")[0]) < min_year:
        #         break
        #     dates.append(date)
        #
        # def pcs_points_links(date, offset):
        #     return f"https://www.procyclingstats.com/rankings.php?date={date}&nation=&age=&zage=&page=smallerorequal&team=&offset={offset}&teamlevel=&filter=Filter"
        #
        # def uci_points_links(date, offset):
        #     return f"https://www.procyclingstats.com/rankings.php?date={date}&nation=&age=&zage=&page=smallerorequal&team=&offset={offset}&continent=&teamlevel=&filter=Filter&p=me&s=uci-individual"
        #
        # def extract_points(pcs):
        #
        #     def get_link(date, offset):
        #         if pcs:
        #             return pcs_points_links(date, offset)
        #         else:
        #             return uci_points_links(date, offset)
        #
        #     res = []
        #     printProgressBar(0, len(dates), prefix='Progress:', suffix='Complete', length=50)
        #     i = 0
        #     for date in dates:
        #         browser.get(get_link(date, 0))
        #         soup = BeautifulSoup(browser.page_source, 'html.parser')
        #
        #         soup_offests = soup.find("select", {"name": "offset"}).find_all("option")
        #         offsets = []
        #         for soup_offest in soup_offests:
        #             offsets.append(int(soup_offest.text.split("-")[0]) - 1)
        #
        #         for offset in offsets:
        #             browser.get(get_link(date, offset))
        #             soup = BeautifulSoup(browser.page_source, 'html.parser')
        #             head_lines = [item.text for item in soup.find("thead").find_all("th")]
        #             table = soup.find("tbody").find_all("tr")
        #
        #             for row in table:
        #                 new_data = {}
        #                 columns = row.find_all("td")
        #                 for i in range(len(columns)):
        #                     if head_lines[i] == "#":
        #                         new_data["rank"] = int(columns[i].text)
        #                     elif head_lines[i] == "Rider":
        #                         name = columns[i].text
        #                         new_data["cyclist_name"] = f"{name}".strip().lower()
        #                     elif head_lines[i] == "Team":
        #                         new_data["team_name"] = columns[i].find("a").text.strip()
        #                     elif head_lines[i] == "Points":
        #                         new_data["points"] = columns[i].find("a").text
        #                 new_data["date"] = datetime.strptime(date, "%Y-%m-%d")
        #                 # print(new_data)
        #                 res.append(new_data)
        #
        #         i += 1
        #         printProgressBar(i, len(dates), prefix='Progress:', suffix='Complete', length=50)
        #
        #     return res
        #
        # print("===== Extracting PCS points =====")
        # print()
        # pcs_points = extract_points(pcs=True)
        # print()
        # print("===== Extracting UCI points =====")
        # print()
        # uci_points = extract_points(pcs=False)
        #
        # pcs_df = pd.DataFrame(pcs_points)
        # uci_df = pd.DataFrame(uci_points)
        #
        # print(len(pcs_df))
        # print(len(uci_df))
        #
        # pcs_df.to_csv("pcs_df.csv")
        # uci_df.to_csv("uci_df.csv")
        #
        # pcs_df.rename(columns={"rank": "pcs_rank", "points": "pcs_points"})
        # uci_df.rename(columns={"rank": "uci_rank", "points": "uci_points"})
        #
        # cyclists = get_all_to_df(CyclistModel)[["cyclist_id", "full_name"]].rename(
        #     columns={"full_name": "cyclist_name"})
        # cyclists["cyclist_name"] = cyclists["cyclist_name"].str.lower()
        #
        # teams = get_all_to_df(TeamModel)[["team_id", "team_name"]]
        # cyclist_ranking = get_all_to_df(CyclistRankingModel)
        #
        # # Apply unicode
        # cyclists["cyclist_name"] = cyclists["cyclist_name"].apply(unidecode)
        # teams["team_name"] = teams["team_name"].apply(unidecode)
        #
        # # add cyclists_id and team_id to data
        # if len(pcs_df) > 0:
        #     pcs_df["cyclist_name"] = pcs_df["cyclist_name"].apply(unidecode)
        #     pcs_df["team_name"] = pcs_df["team_name"].apply(unidecode)
        #
        #     pcs_df = pd.merge(pcs_df, cyclists, on="cyclist_name", how="inner")
        #     pcs_df = pd.merge(pcs_df, teams, on="team_name", how="inner")
        #
        #     # remove duplicates
        #     pcs_df = pd.merge(pcs_df, cyclist_ranking, on=["cylist_id", "team_id", "date"], how="outer", indicator=True)
        #     pcs_df = pcs_df[pcs_df['_merge'] == 'left_only']
        #     pcs_df = pcs_df.drop("_merge", 1)
        #
        # if len(uci_df) > 0:
        #     uci_df["cyclist_name"] = uci_df["cyclist_name"].apply(unidecode)
        #     uci_df["team_name"] = uci_df["team_name"].apply(unidecode)
        #
        #     uci_df = pd.merge(uci_df, cyclists, on="cyclist_name", how="inner")
        #     uci_df = pd.merge(uci_df, teams, on="team_name", how="inner")
        #
        #     # remove duplicates
        #     uci_df = pd.merge(uci_df, cyclist_ranking, on=["cylist_id", "team_id", "date"], how="outer", indicator=True)
        #     uci_df = uci_df[uci_df['_merge'] == 'left_only']
        #     uci_df = uci_df.drop("_merge", 1)
        #
        # print(f"There are {pcs_df} new pcs scores")
        # print(f"There are {uci_df} new uci scores")

        # upload_df(pcs_df, 'cyclists_rankings')
        # upload_df(uci_df, 'cyclists_rankings')
