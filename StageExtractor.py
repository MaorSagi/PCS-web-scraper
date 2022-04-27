import os.path

import pandas as pd
from unidecode import unidecode

from CyclistTeamsExtractor import CyclistTeamsExtractor
from Extractor import Extractor
from utils import *
from consts import *

stages_df = get_df('stages')


class StageExtractor(Extractor):
    def __init__(self, id=id):
        super().__init__(id=id)

    @staticmethod
    def get_stage_type(stage_header, race_header, stage_points_scale):
        if ('TTT' in stage_header) or ('TTT' in race_header) or (
                (stage_points_scale is not None) and ('TTT' in stage_points_scale)):
            return 'Team Time Trial'
        if ('ITT' in stage_header) or ('Time Trial' in stage_header):
            return 'Individual Time Trial'
        elif 'Stage' in stage_header:
            return 'Stage'
        else:
            return stage_header

    def extract_infolist_data(self, stage_soup, stage):

        infolist = stage_soup.find("ul", {"class": "infolist"}).find_all("li")
        for info in infolist:
            try:
                label = info.find_all("div")[0].text
                value = info.find_all("div")[1]

                if "Date" in label:
                    stage["stage_date"] = datetime.strptime(value.text.split(',')[0], "%d %B %Y")
                elif "Departure" in label:
                    stage["pcs_city_start"] = unidecode(value.find("a").text.strip())
                elif "Arrival" in label:
                    stage["pcs_city_finish"] = unidecode(value.find("a").text.strip())
                elif "Race category" in label:
                    stage["race_category"] = value.text
                elif "Parcours type" in label:
                    parcours_type_text = value.find("span").attrs.get("class")[2][-1]
                    parcours_type = int(parcours_type_text) if check_int(parcours_type_text) else None
                    if (parcours_type is None) or (parcours_type not in range(len(PARCOURS_TYPES))):
                        raise ValueError(
                            f'Problem parsing parcours type, unfamiliar type {parcours_type}, stage {stage["stage_link"]}')
                    stage['parcours_type'] = parcours_type
                    stage['parcours_type_name'] = PARCOURS_TYPES[parcours_type]
                elif "ProfileScore" in label:
                    stage["profile_score"] = int(value.text) if check_int(value.text) else None
                    if check_float(value.text):
                        stage['profile_score'] = float(value.text)
                elif "Distance" in label:
                    if 'km' not in value.text:
                        raise ValueError(f'Distance units have to be measured in km, stage {stage["stage_link"]}')
                    distance_str = value.text.split()[0]
                    distance = float(distance_str) if (check_float(distance_str) or check_int(distance_str)) else None
                    if distance == 0:
                        stage["distance"] = None
                    else:
                        stage["distance"] = distance * 1000
                elif "Race ranking" in label:
                    stage['stage_ranking'] = int(value.text) if check_int(value.text) else None
                    if check_float(value.text):
                        stage['stage_ranking'] = float(value.text)
                elif "Start time" in label:
                    if value.text == '-':
                        stage['start_time'] = None
                        continue
                    stage['start_time'] = value.text.strip()
                elif "Avg. speed winner" in label:
                    avg_speed_winner = value.text.split()[0]
                    avg_speed_winner = float(avg_speed_winner) if (
                            check_float(avg_speed_winner) or check_int(avg_speed_winner)) else None
                    if avg_speed_winner == 0 or avg_speed_winner is None:
                        stage["avg_speed_winner"] = None
                        continue
                    elif 'km/h' not in value.text:
                        raise ValueError(f'Speed units have to be measured in km/h, stage {stage["stage_link"]}')
                    stage["avg_speed_winner"] = avg_speed_winner
                elif "Vert. meters" in label:
                    stage['elevation_gain'] = float(value.text) if (
                            check_float(value.text) or check_int(value.text)) else None
                elif "Points scale" in label:
                    stage['stage_points_scale'] = value.text
            except:
                msg = f'Failed to parse property {label}, value: {value}, in stage {stage["stage_link"]}.'
                log(msg, 'ERROR', id=self.id)

    def update_stage(self, stage):
        global stages_df
        stage_link = stage['stage_link']
        stage_idx = stages_df[stages_df['stage_link'] == stage_link].index[0]
        stage_row = stages_df.loc[stage_idx]
        diff_exists = False
        for k in stage_row.index:
            if (k in stage) and k not in ['race_id', 'stage_id', 'race_link', 'stage_link']:
                if (stage[k] is not None) and (stage[k] != ''):
                    if stage_row[k] != stage[k]:
                        print(k, f"{stage_row[k]} != {stage[k]}")
                        stages_df.loc[stage_idx, k] = stage[k]
                        diff_exists = True
        if diff_exists:
            stages_df.to_csv(CSV_PATHS['stages'], header=True, index=False)

    # TODO: overwrite handling
    def non_stage_handler(self, soup, stage, overwrite):
        global stages_df
        try:
            overwrite = overwrite if overwrite is not None else False
            # option_filter = soup.find_all("div", {"class": "pageSelectNav"})
            # if len(option_filter) > 1:
            #     raise ValueError(f'Problem in race parsing - soppuse to be one day race, race {stage["stage_link"]}')
            stage_link = stage['race_link']
            stage_exists = ((stages_df is not None) and (stage_link in stages_df['stage_link'].values))
            if stage_exists and (not overwrite):
                return
            stage_id = stages_df['stage_id'].max() + 1 if stages_df is not None else 1
            stage_name = soup.find('span', attrs={'class': 'blue'}).text
            self.extract_infolist_data(soup, stage)
            stage.update({"stage_id": stage_id,
                          "stage_link": stage_link,
                          'stage_type': StageExtractor.get_stage_type(stage_name, stage['race_name'],
                                                                      stage['stage_points_scale']),
                          'stage_name': stage_name
                          })
            stage['stage_date'] = stage['stage_date'].strftime("%Y-%m-%d")
            stage['race_date'] = stage['race_date'].strftime("%Y-%m-%d")
            if stage_exists:
                self.update_stage(stage)
            else:
                append_row_to_csv(CSV_PATHS['stages'], stage, columns=STAGETS_COLS)
                stages_df = get_df('stages')
        except:
            msg = f'Failed to parse one day race stage {stage["stage_link"]}.'
            log(msg, 'ERROR', id=self.id)

    # TODO: overwrite handling
    def stages_handler(self, soup, stage, overwrite):
        global stages_df
        try:
            overwrite = overwrite if overwrite is not None else False
            option_filter = soup.find_all("div", {"class": "pageSelectNav"})
            option_filter = option_filter[1].find_all("option")
            i = 1
            for option in option_filter:
                new_stage = stage.copy()
                i += 1
                stage_name = option.text.split("|")[0].strip()
                stage_type = StageExtractor.get_stage_type(stage_name, stage['race_name'], stage['stage_points_scale'])
                if stage_type in SPECIAL_RACE_TYPES:
                    continue
                stage_number = stage_name.split()[1].strip() if len(stage_name.split()) > 1 else None
                stage_link = f"{PCS_BASE_URL}/{option['value']}".replace('startlist/preview', '').replace(
                    '/result/result', '')
                stage_exists = ((stages_df is not None) and (stage_link in stages_df['stage_link'].values))
                if stage_exists and (not overwrite):
                    continue
                stage_id = stages_df['stage_id'].max() + 1 if stages_df is not None else 1
                new_stage.update({'stage_id': stage_id,
                                  'stage_type': stage_type,
                                  'stage_name': stage_name,
                                  'stage_number': stage_number,
                                  'stage_link': stage_link
                                  })
                stage_soup = self.browser.get(stage_link).soup
                self.extract_infolist_data(stage_soup, new_stage)
                if stage_exists:
                    self.update_stage(new_stage)
                else:
                    append_row_to_csv(CSV_PATHS['stages'], new_stage, columns=STAGETS_COLS)
                    stages_df = get_df('stages')
        except:
            msg = f'Failed to parse stage {stage["race_link"]}.'
            log(msg, 'ERROR', id=self.id)

    def fetch_race(self, race, year, table_headers, cont_pred, stage_last, overwrite, race_class=None):
        global stages_df
        try:
            # race_link = None
            if 'class' in race.attrs and 'striked' in race.attrs['class']:
                return cont_pred
            tds = race.find_all('td')
            # if race_class.lower() in [r_c.lower for r_c in RACES_CLASS_TO_IGNORE]:
            #     return cont_pred
            # if race_class.lower() not in [r_c.lower() for r_c in RACE_CLASSES_TO_INCLUDE]:
            #     return cont_pred
            race_idx = table_headers.index('Race')
            race_name = tds[race_idx].find('a').text
            race_link = f"{PCS_BASE_URL}/{tds[race_idx].find('a')['href']}".replace('startlist/preview', '').replace(
                '/result/result', '')
            race_nation = tds[race_idx].find('span')['class'][1]
            end_date, race_date, race_page = None, None, None
            if 'Date' in table_headers:
                if tds[1].text != tds[0].text:
                    end_date_str = tds[0].text.split("-")[1].strip()
                    end_date = datetime.strptime(f"{end_date_str}.{year}", '%d.%m.%Y')
                race_date = datetime.strptime(f"{tds[1].text}.{year}", '%d.%m.%Y')
            else:
                race_overview_page = self.browser.get(f"{race_link}/result/overview").soup
                race_info = race_overview_page.select('ul[class*="infolist"]')
                if len(race_info) == 0:
                    race_page = self.browser.get(race_link).soup
                    preview_href = race_page.find(lambda tag: (tag.name == "a") and ("Preview" in tag.text))['href']
                    preview_link = f"{PCS_BASE_URL}/{preview_href}"
                    race_overview_page = self.browser.get(preview_link).soup
                    race_info = race_overview_page.select('ul[class*="infolist"]')

                race_info_list = race_info[0].find_all('li')
                race_info_headers = [h.contents[0].text for h in race_info_list]
                race_info_values = [h.contents[2].text for h in race_info_list]
                race_date_idx = race_info_headers.index('Startdate:')
                end_date_idx = race_info_headers.index('Enddate:')
                race_date = datetime.strptime(race_info_values[race_date_idx], '%Y-%m-%d')
                end_date = datetime.strptime(race_info_values[end_date_idx], '%Y-%m-%d')
            if race_date >= datetime.now():
                return cont_pred
            if (end_date is not None) and (end_date >= datetime.now()):
                return cont_pred
            if (not cont_pred) and race_link != stage_last:
                return cont_pred
            cont_pred = True
            race_id = stages_df['race_id'].max() + 1 if stages_df is not None else 1
            race_name = unidecode(race_name)
            stage = {'race_id': race_id, 'race_name': race_name,
                     'classification': race_class, 'race_link': race_link,
                     'race_date': race_date, 'nation': race_nation}
            if race_page is None:
                race_page = self.browser.get(race_link).soup
            # msg = f'race {race_link}'
            # log(msg, 'INFO', id=self.id)
            stage_type = StageExtractor.get_stage_type(race_page.find('span', attrs={'class': 'blue'}).text,
                                                       stage['race_name'], stage['stage_points_scale'])
            if (stage_type is None) or (stage_type == ''):
                log(f'Trying to fetch stage with no type, link {race_link}', 'WARNING', id=self.id)
                if any([('Stage' in o.text) for o in race_page.find_all('option')]):
                    self.stages_handler(race_page, stage, overwrite)
                else:
                    self.non_stage_handler(race_page, stage, overwrite)
                return cont_pred
            elif stage_type not in STAGES_TYPES:
                raise ValueError(f'Failed to parse race {race_link}, unfamiliar type {stage_type}')
            if stage_type in ["One day race", "Time trial"]:
                self.non_stage_handler(race_page, stage, overwrite)
            else:
                self.stages_handler(race_page, stage, overwrite)
            return cont_pred
        except:
            msg = f'Failed to fetch stage {race}.'
            log(msg, 'ERROR', id=self.id)
            return cont_pred

    def fetch_races(self, stage_last=None, years_range=range(2010, 2023), overwrite=None):
        race_link = None
        continue_last_session_pred = stage_last is None
        races_soup = self.browser.get(RACES_DB_URL).soup
        classes = races_soup.find('select', attrs={'name': 'class'}).find_all('option')
        # categories = races_soup.find('select', attrs={'name': 'category'}).find_all('option')
        categories = races_soup.find('select', attrs={'name': 'category'}).find_all('option')
        for year in years_range:
            for race_class in classes:
                race_class = race_class.text
                if race_class.strip() == '-':
                    continue
                for category in categories:
                    if category.text.strip() == '-':
                        continue
                    try:
                        race_by_year_url = f"{RACES_URL}?class={race_class}&category={category['value']}&year={year}&filter=Filter&s=races-database"
                        race_page = self.browser.get(race_by_year_url)
                        races_table = race_page.soup.find('table', attrs={'class': 'basic'})
                        table_headers = races_table.find("thead").find_all("th")
                        table_headers = [h.text for h in table_headers]
                        table_rows = races_table.find("tbody").find_all("tr")
                        i = 0
                        for row in table_rows:
                            continue_last_session_pred = self.fetch_race(row, year, table_headers,
                                                                         continue_last_session_pred,
                                                                         stage_last, overwrite, race_class)
                    except:
                        msg = f'Failed to parse stage {race_link}.'
                        log(msg, 'ERROR', id=self.id)
                        continue

    def get_result_details_from_row(self, row, result_type, result_link, stage_id, headers_text,
                                    winner_finish_time, time_idx, team_name, stage_date, team_url, data_from_team=None,
                                    team_pcs_id=None):
        if "Teams" == result_type:
            # TODO - fix bug here
            cyclist_id = None
            team_id = self.get_team_id(team_name, stage_date=stage_date, team_pcs_id=team_pcs_id,
                                       team_url=team_url)
            if team_id is None:
                return
        else:
            cyclist = row.select('a[href*="rider"]')[0]
            cyclist_url = f"{PCS_BASE_URL}/{cyclist['href']}"
            cyclists_df = get_df('cyclists')

            if not CyclistTeamsExtractor.is_cyclist_exists(cyclists_df, cyclist_url):
                self.handle_missing_cyclists(cyclist, cyclist_url)
                return
                # extractor = CyclistTeamsExtractor(id=self.id)
                # cyclist_df = extractor.add_cyclist(cyclists_df, cyclist_name, cyclist_url)
                # extractor.fetch_cyclists_and_cyclists_teams_from_cyclists(cyclist_df)
            cyclists_df = get_df('cyclists', index_col='cyclist_id')
            cyclist_id = cyclists_df[cyclists_df['pcs_link'] == cyclist_url].index[0]
            team_id = self.get_team_id(team_name, stage_date=stage_date, cyclist_id=cyclist_id,
                                       team_pcs_id=team_pcs_id, team_url=team_url)
            if team_id is None:
                return

        result_args = (result_type, result_link, stage_id, team_id, cyclist_id)
        if self._is_result_exists(*result_args):
            return
        # results_df = get_df('stages_results')
        path = StageExtractor.get_file_path_with_new_suffix(CSV_PATHS['stages_results'], self.id, 'csv')
        results_df = None
        if os.path.exists(path):
            results_df = pd.read_csv(path)
        result_id = results_df['result_id'].max() + 1 if results_df is not None else 1
        tds = row.find_all('td')
        if data_from_team is not None:
            ranking = data_from_team['ranking']
            uci_points = tds[headers_text.index('UCI points')].text.strip()
            pcs_points = tds[headers_text.index('PCS points')].text.strip()
            time_gap = data_from_team['time_gap']
            finish_time = data_from_team['finish_time']
            additional_gap = row.find('span', attrs={'class': 'blue'})
            if (additional_gap is not None) and ('-' not in additional_gap.text) and ('+-' not in additional_gap.text):
                time_gap_obj = StageExtractor.get_timedelta_from_string(time_gap)
                finish_time_obj = StageExtractor.get_timedelta_from_string(finish_time)
                additional_gap = additional_gap.text.split('+')[1]
                additional_gap_obj = StageExtractor.get_timedelta_from_string(additional_gap)
                time_gap_obj += additional_gap_obj
                finish_time_obj += additional_gap_obj
                time_gap = StageExtractor.get_string_from_timedelta(time_gap_obj)
                finish_time = StageExtractor.get_string_from_timedelta(finish_time_obj)


        else:
            ranking = tds[headers_text.index('Rnk')].text.strip()
            uci_points = tds[headers_text.index('UCI')].text.strip() if result_type != "Teams" else None
            pcs_points = tds[headers_text.index('Pnt')].text.strip() if result_type != "Teams" else None

            if ranking == '1':
                time_gap = '0:00'
                finish_time = winner_finish_time.strip()
            elif ranking in SPECIAL_RANKING_RESULTS.keys():
                time_gap, finish_time = None, None
            else:
                time_gap, finish_time = StageExtractor.get_time_details(winner_finish_time, tds[time_idx],
                                                                        result_type)
                time_gap, finish_time = time_gap, finish_time
        return result_id, team_id, cyclist_id, ranking, pcs_points, uci_points, finish_time, time_gap

    def handle_missing_cyclists(self, cyclist, cyclist_url):
        missing_cyclist = dict(cyclist_name_pcs=cyclist.text, pcs_link=cyclist_url)
        path = StageExtractor.get_file_path_with_new_suffix(MISSING_CYCLISTS_PATH, self.id, 'csv')
        if os.path.exists(path):
            if cyclist_url not in pd.read_csv(path)['pcs_link'].values:
                append_row_to_csv(path, missing_cyclist,
                                  ['cyclist_name_pcs', 'pcs_link'])
        else:
            append_row_to_csv(path, missing_cyclist,
                              ['cyclist_name_pcs', 'pcs_link'])
        msg = f'Missing cyclist {cyclist_url}'
        log(msg, 'WARNING', id=self.id)

    def fetch_TTT_results(self, result_type, result_link, result_pcs_id, stage, headers_text, r_type,
                          winner_finish_time, time_idx, table_rows):
        stage_id = stage['stage_id']
        stage_date = stage['stage_date']
        i = 0
        while i < len(table_rows):
            row = table_rows[i]
            try:
                team_a, team_name, team_url = StageExtractor.get_team_details_from_row(row)
                tds = row.find_all('td')
                ranking = tds[headers_text.index('Pos.')].text.strip()
                if len(team_a) == 0:
                    self.handle_missing_teams_in_results(ranking, result_link, team_url)
                time_gap = tds[headers_text.index('Timegap')].text.strip()
                finish_time = tds[headers_text.index('Time')].text.strip()
                data_from_team = dict(ranking=ranking, time_gap=time_gap,
                                      finish_time=finish_time)
                i += 1
                while (i < len(table_rows)) and (len(table_rows[i].select('a[href*="team"]')) == 0):
                    row = table_rows[i]
                    try:
                        result_tuple = self.get_result_details_from_row(row, result_type, result_link,
                                                                        stage_id, headers_text,
                                                                        winner_finish_time, time_idx, team_name,
                                                                        stage_date,
                                                                        team_url, data_from_team=data_from_team)
                        if result_tuple is None:
                            i += 1
                            continue
                        else:
                            result_id, team_id, cyclist_id, ranking, pcs_points, uci_points, finish_time, time_gap = result_tuple
                        msg = f'race result {result_link}'
                        log(msg, 'INFO', id=self.id)
                        result = {'result_id': result_id, 'result_type': r_type,
                                  'cyclist_id': cyclist_id, 'team_id': team_id,
                                  'stage_id': stage_id, 'race_id': stage['race_id'], 'result_pcs_id': result_pcs_id,
                                  'ranking': ranking, 'uci_points': uci_points, 'pcs_points': pcs_points,
                                  'finish_time': finish_time.strip(), 'time_gap': time_gap.strip(),
                                  'result_link': result_link}
                        path = StageExtractor.get_file_path_with_new_suffix(CSV_PATHS['stages_results'], self.id, 'csv')
                        append_row_to_csv(path, result, CYCLISTS_STAGES_RESULTS_COLS)
                    except:
                        msg = f'Failed to fetch result in stage {stage["stage_id"]}, link {stage["stage_link"]}.'
                        log(msg, 'ERROR', id=self.id)
                    i += 1
            except:
                msg = f'Failed to fetch team result in stage {stage["stage_id"]}, link {stage["stage_link"]}.'
                log(msg, 'ERROR', id=self.id)

    def get_team_id(self, team_name, stage_date=None, cyclist_id=None, team_url=None, team_pcs_id=None):
        year = stage_date.year
        teams_df = get_df('teams', index_col='team_id')
        if cyclist_id is not None:
            cyclists_teams_df = get_df('cyclists_teams')
            cyclist_team = cyclists_teams_df.loc[
                (cyclists_teams_df['cyclist_id'] == cyclist_id) & (cyclists_teams_df['season'] == year)]
            cyclist_team = cyclist_team.loc[(pd.to_datetime(cyclist_team['start_date']) <= stage_date) & (
                    pd.to_datetime(cyclist_team['stop_date']) >= stage_date)]
            if cyclist_team.empty:
                self.handle_missing_cyclist_in_team(cyclist_id, year)
                return
            cyclist_team = cyclist_team.iloc[0]
            team_id = cyclist_team['team_id']
            team = teams_df.loc[team_id]
            if team_name is not None:
                team_name = team_name.strip()
                if (team_name != team['team_name']) and (team_name != unidecode(team['team_name'])):
                    self.handle_incompatible_team_name(team, cyclist_id, team_id, team_name, team_url, year)
        elif team_url is not None:
            team_url_cut_year = team_url.replace('/overview/', '')[:-4]
            team = teams_df.loc[(teams_df['team_name'] == team_name) & (
                teams_df['pcs_link'].str.contains(team_url_cut_year, regex=False))]
            if team.empty:
                self.handle_missing_teams(team_name, team_url)
                return
            team_id = team['season'].idxmax()
        else:
            raise ValueError(f'Cannot extract team id without team or cyclist details')
        team = teams_df.loc[team_id]
        if (team_pcs_id is not None) and (str(team['team_pcs_id']) == 'nan'):
            team_gen_id = team['team_gen_id']
            all_years_team = teams_df.loc[teams_df['team_gen_id'] == team_gen_id]
            for i, r in all_years_team.iterrows():
                teams_df.at[i, 'team_pcs_id'] = team_pcs_id
            teams_df.to_csv(CSV_PATHS['teams'], header=True)
        return team_id

    def handle_missing_teams(self, team_name, team_url):
        path = StageExtractor.get_file_path_with_new_suffix(MISSING_TEAMS_PATH, self.id, 'csv')
        missing_team = dict(team_name=team_name, pcs_link=team_url)
        if os.path.exists(path):
            if team_url not in pd.read_csv(path)['pcs_link'].values:
                append_row_to_csv(path, missing_team,
                                  ['team_name', 'pcs_link'])
        else:
            append_row_to_csv(path, missing_team,
                              ['team_name', 'pcs_link'])
        msg = f'Missing team {team_url}'
        log(msg, 'WARNING', id=self.id)

    def handle_incompatible_team_name(self, team, cyclist_id, team_id, team_name, team_url, year):
        _, team_oldest_pcs_link = CyclistTeamsExtractor(id=self.id).get_oldest_team_link(team_url)
        if team_oldest_pcs_link != team['team_oldest_pcs_link']:
            incompatible_cyclist_team = dict(cyclist_id=cyclist_id, team_id=team_id, season=year,
                                             result_team=team_oldest_pcs_link, data_team=team['team_oldest_pcs_link'])
            path = StageExtractor.get_file_path_with_new_suffix(INCOMPATIBLE_CYCLISTS_TEAMS_PATH, self.id, 'csv')
            if os.path.exists(path):
                df = pd.read_csv(path)
                if df[(df['cyclist_id'] == cyclist_id) & (df['season'] == year)].empty:
                    append_row_to_csv(path, incompatible_cyclist_team,
                                      ['cyclist_id', 'team_id', 'season', 'result_team', 'data_team'])
            else:
                append_row_to_csv(path, incompatible_cyclist_team,
                                  ['cyclist_id', 'team_id', 'season', 'result_team', 'data_team'])
            msg = f"The team of the cyclist (link {team_url}) incompatible with the team of the cyclist in {year} - {team['team_oldest_pcs_link']}"
            log(msg, 'WARNING', id=self.id)

        else:
            incompatible_team_name = dict(team_id=team_id, season=year,
                                          result_team_name=team_name, data_team_name=team["team_name"])
            path = StageExtractor.get_file_path_with_new_suffix(INCOMPATIBLE_TEAMS_NAMES_PATH, self.id, 'csv')
            if os.path.exists(path):
                df = pd.read_csv(path)
                if df[(df['team_id'] == team_id) & (df['season'] == year)].empty:
                    append_row_to_csv(path, incompatible_team_name,
                                      ['team_id', 'season', 'result_team_name', 'data_team_name'])
            else:
                append_row_to_csv(path, incompatible_team_name,
                                  ['team_id', 'season', 'result_team_name', 'data_team_name'])
            msg = f'The name of team {team_id} ({team["team_name"]}) incompatible with the name on PCS - {team_name}'
            log(msg, 'WARNING', id=self.id)

    def handle_missing_cyclist_in_team(self, cyclist_id, year):
        missing_cyclist_team = dict(cyclist_id=cyclist_id, season=year)
        path = StageExtractor.get_file_path_with_new_suffix(MISSING_CYCLISTS_IN_TEAMS_PATH, self.id, 'csv')
        if os.path.exists(path):
            df = pd.read_csv(path)
            if df[(df['cyclist_id'] == cyclist_id) & (df['season'] == year)].empty:
                append_row_to_csv(path, missing_cyclist_team,
                                  ['cyclist_id', 'season'])
        else:
            append_row_to_csv(path, missing_cyclist_team,
                              ['cyclist_id', 'season'])
        msg = f'Cyclist {cyclist_id} is not in any team in {year}'
        log(msg, 'WARNING', id=self.id)

    @staticmethod
    def get_team_details_from_row(row):
        team_a = row.select('a[href*="team"]')
        if len(team_a) > 0:
            team_name = unidecode(team_a[0].text)
            team_url = f"{PCS_BASE_URL}/{team_a[0]['href']}"
            return team_a, team_name, team_url
        else:
            return row.select('a[href*="team"]'), None, None

    def fetch_results(self, stage_soup, stage, result_type=None):
        try:
            result_tabs = stage_soup.find('ul', attrs={'class': 'restabs'})
            if result_tabs is not None:
                result_tabs_text = [a.text for a in result_tabs.find_all('a')]
                if result_type in STAGE_RESULTS_CLASSES.keys():
                    if result_type in result_tabs_text:
                        result_type_idx = result_tabs_text.index(result_type)
                    else:
                        return
                elif result_type in ["Team Time Trial", "Individual Time Trial"]:
                    result_type_idx = result_tabs_text.index('')
                elif result_type == "Prologue":
                    result_type_idx = result_tabs_text.index('Prol.')
                else:
                    raise ValueError(f'Unpredicted result type {result_type}')
                result_a = result_tabs.find_all('li')[result_type_idx].find('a')
                result_link = f"{PCS_BASE_URL}/{result_a['href']}"
                result_pcs_id = result_a['data-id']
                results_div = stage_soup.select('div[class*="result-cont"]')[result_type_idx]
                r_type = STAGE_RESULTS_CLASSES[result_type] if result_type not in TIME_TRIAL_TYPES else result_type
            else:
                result_link = stage['stage_link']
                results_div = stage_soup.find('div', attrs={'class': 'result-cont'})
                result_pcs_id = results_div['data-id']
                r_type = result_type
            results_table = results_div.find('table')
            # Headers
            table_headers = results_table.find("thead").find_all("th")
            headers_text = [t.text for t in table_headers]
            headers_list = STAGE_RESULT_PROPS[r_type] if r_type is not None else STAGE_RESULT_PROPS[stage['stage_type']]
            self.validate_headers(headers_list, table_headers, stage['stage_link'],stage['stage_type'])

            # Records
            table_rows = results_table.find("tbody").find_all("tr")
            time_idx = headers_text.index('Time')
            if len(table_rows) == 0:
                return
            winner_finish_time = self._get_winner_finish_time(table_rows[0], time_idx)
            if (result_type == "Team Time Trial") or (STAGE_RESULT_PROPS["Team Time Trial"]==headers_text):
                self.fetch_TTT_results(result_type, result_link, result_pcs_id, stage, headers_text, r_type,
                                       winner_finish_time, time_idx, table_rows)
            else:
                self.fetch_individual_results(result_type, result_link, result_pcs_id, stage, headers_text, r_type,
                                              winner_finish_time, time_idx, table_rows)

        except Exception as err:
            msg = f'Failed to fetch stage results, in stage {stage["stage_id"]}, link {stage["stage_link"]}.'
            log(msg, 'ERROR', id=self.id)

    @staticmethod
    def _get_winner_finish_time(first_row, time_idx):
        winner_finish_time_td = first_row.contents[time_idx]
        div_time = winner_finish_time_td.find_all('div', attrs={'class': 'hide'})
        if len(div_time) > 0:
            winner_finish_time = div_time[0].text
        else:
            # TODO- bug!!! to fix
            winner_finish_time = winner_finish_time_td.contents[0].text
            if winner_finish_time == '-':
                return None
            try:
                tmp = StageExtractor.get_timedelta_from_string(winner_finish_time)
            except:
                print('BUG!!')

        return winner_finish_time

    def validate_headers(self,headers_list, table_headers, stage_link,stage_type):
        for header in table_headers:
            if (header.text == '') or (('class' in header.attrs) and ('hide' in header['class'])):
                continue
            if header.get_text() not in headers_list:
                self.handle_incompatible_headers(header, stage_link,stage_type)

    def handle_incompatible_headers(self, header, stage_link,stage_type):
        incompatible_header = dict(stage_link=stage_link, header=header, stage_type=stage_type)
        path = StageExtractor.get_file_path_with_new_suffix(INCOMPATIBLE_STAGES_HEADERS_PATH, self.id, 'csv')
        if os.path.exists(path):
            df = pd.read_csv(path)
            if df[df['stage_link'] == stage_link].empty:
                append_row_to_csv(path, incompatible_header,
                                  ['stage_link', 'header', 'stage_type'])
        else:
            append_row_to_csv(path, incompatible_header,
                              ['stage_link', 'header', 'stage_type'])
        msg = f'The cyclist results table does not match to the script - unfamiliar header {header.get_text()}, stage {stage_link}, stage type: {stage_type}'
        log(msg, 'WARNING', id=self.id)

    # @staticmethod
    def _is_result_exists(self, result_type, result_link, stage_id, team_id, cyclist_id):
        # results_df = get_df('stages_results')
        results_df = None
        path = StageExtractor.get_file_path_with_new_suffix(CSV_PATHS['stages_results'], self.id, 'csv')
        if os.path.exists(path):
            results_df = pd.read_csv(path)
        if results_df is None:
            return False
        if result_type is not None:
            r_type = STAGE_RESULTS_CLASSES[result_type] if result_type in STAGE_RESULTS_CLASSES else result_type
            result_exist_pred = (results_df['result_type'] == r_type)
        else:
            result_exist_pred = (results_df['result_type'].isna())
        if cyclist_id is not None:
            result_exist_pred = result_exist_pred & (results_df['cyclist_id'] == cyclist_id)
        else:
            result_exist_pred = result_exist_pred & (results_df['cyclist_id'].isna())
        result_exist_pred = result_exist_pred & (results_df['result_link'] == result_link)
        result_exist_pred = result_exist_pred & (results_df['stage_id'] == stage_id)
        result_exist_pred = result_exist_pred & (results_df['team_id'] == team_id)
        result_df = results_df[result_exist_pred]
        if result_df.empty:
            return False
        return True

    @staticmethod
    def fetch_teams_results(stage_soup, stage):
        results_div = stage_soup.find_all('div', attrs={'class': 'result-cont hide'})[-1]
        results_table = results_div.find('table')

    @staticmethod
    def fetch_one_day_race_results(stage_soup, stage):
        results_div = stage_soup.find('div', attrs={'class': 'result-cont '})
        results_table = results_div.find('table')

    def fetch_race_results(self, stages, stage_last=None, years_range=None):
        cont_pred = stage_last is None
        stages['race_date'] = pd.to_datetime(stages['race_date'])
        stages['stage_date'] = pd.to_datetime(stages['stage_date'])
        stages = stages[stages['race_date'].apply(lambda dt: dt.year in years_range)]
        stages = stages.sort_values('stage_date')
        for idx, stage in stages.iterrows():
            try:
                stage_link = stage['stage_link']
                if (not cont_pred) and stage_link != stage_last:
                    continue
                cont_pred = True
                # race_class = str(stage['classification']).strip()
                # if race_class.lower() in [r_c.lower for r_c in RACES_CLASS_TO_IGNORE]:
                #     continue
                # if race_class.lower() not in [r_c.lower() for r_c in RACE_CLASSES_TO_INCLUDE]:
                #     continue
                stage_type = stage['stage_type']
                stage_soup = self.browser.get(stage['stage_link']).soup
                msg = f"race {stage['stage_link']}"
                log(msg, 'INFO', id=self.id)
                if stage_type in TIME_TRIAL_TYPES:
                    self.fetch_results(stage_soup, stage, stage_type)
                else:
                    diff_types_results = stage_soup.find_all('ul', attrs={'class': 'restabs'})
                    if len(diff_types_results) == 0:
                        self.fetch_results(stage_soup, stage)
                    else:
                        self.fetch_results(stage_soup, stage, 'Stage')
                        diff_types_results = diff_types_results[0].find_all('li')
                        teams_results_ref = diff_types_results[-1].find('a')['href']
                        teams_results_link = f"{PCS_BASE_URL}/{teams_results_ref}"
                        teams_results_soup = self.browser.get(teams_results_link).soup
                        self.fetch_results(teams_results_soup, stage, 'Teams')
            except:
                msg = f'Failed to fetch stage {stage["stage_id"]}, link {stage["stage_link"]}.'
                log(msg, 'ERROR', id=self.id)

    @staticmethod
    def get_time_details(winner_finish_time, time_td, result_type=None):
        if (winner_finish_time is None) or (time_td is None):
            return None, None
        winner_finish_time_timedelta = StageExtractor.get_timedelta_from_string(winner_finish_time)
        if '-' in time_td.text:
            return None, None
        time = time_td.find('div').text
        time_timedelta = StageExtractor.get_timedelta_from_string(time)
        if time_timedelta > winner_finish_time_timedelta:
            gap_timedelta = time_timedelta - winner_finish_time_timedelta
            time_gap = StageExtractor.get_string_from_timedelta(gap_timedelta)
            finish_time = time
        else:
            time_gap = time_td.find('div').text
            gap_timedelta = StageExtractor.get_timedelta_from_string(time_gap)
            finish_time_timedelta = winner_finish_time_timedelta + gap_timedelta
            finish_time = StageExtractor.get_string_from_timedelta(finish_time_timedelta)
        return time_gap.strip(), finish_time.strip()

    @staticmethod
    def get_string_from_timedelta(timedelta_obj):
        hours, remainder = divmod(timedelta_obj.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if timedelta_obj.days > 0:
            hours += timedelta_obj.days * 24
        if hours == 0:
            return f"{str(minutes)}:{str(seconds).zfill(2)}"
        return f"{str(hours)}:{str(minutes).zfill(2)}:{str(seconds).zfill(2)}"

    @staticmethod
    def get_file_path_with_new_suffix(file_path, suffix, file_format):
        return f'{file_path.replace(f".{file_format}","")}_{suffix}.{file_format}'

    @staticmethod
    # BUG in '-' and Team classification
    def get_timedelta_from_string(time_gap):
        gap_splits = time_gap.split(':')
        if len(gap_splits) == 2:
            gap = timedelta(minutes=int(gap_splits[-2]), seconds=int(gap_splits[-1]))
        else:
            gap = timedelta(hours=int(gap_splits[-3]), minutes=int(gap_splits[-2]), seconds=int(gap_splits[-1]))
        return gap

    def fetch_individual_results(self, result_type, result_link, result_pcs_id, stage, headers_text, r_type,
                                 winner_finish_time, time_idx, table_rows):
        stage_id = stage['stage_id']
        stage_date = stage['stage_date']
        i = 0
        for row in table_rows:
            try:
                team_a, team_name, team_url = StageExtractor.get_team_details_from_row(row)
                if len(team_a) == 0:
                    self.handle_missing_teams_in_results(i + 1, result_link, team_url)
                result_tuple = self.get_result_details_from_row(row, result_type, result_link,
                                                                stage_id, headers_text,
                                                                winner_finish_time, time_idx, team_name, stage_date,
                                                                team_url)
                if result_tuple is None:
                    i += 1
                    continue
                else:
                    result_id, team_id, cyclist_id, ranking, pcs_points, uci_points, finish_time, time_gap = result_tuple
                result = {'result_id': result_id, 'result_type': r_type,
                          'cyclist_id': cyclist_id, 'team_id': team_id,
                          'stage_id': stage_id, 'race_id': stage['race_id'], 'result_pcs_id': result_pcs_id,
                          'ranking': ranking, 'uci_points': uci_points, 'pcs_points': pcs_points,
                          'finish_time': finish_time, 'time_gap': time_gap,
                          'result_link': result_link}
                path = StageExtractor.get_file_path_with_new_suffix(CSV_PATHS['stages_results'], self.id, 'csv')
                append_row_to_csv(path, result, CYCLISTS_STAGES_RESULTS_COLS)
            except:
                msg = f'Failed to fetch result in stage {stage["stage_id"]}, link {stage["stage_link"]}.'
                log(msg, 'ERROR', id=self.id)

    def handle_missing_teams_in_results(self, position, result_link, team_url):
        path = StageExtractor.get_file_path_with_new_suffix(MISSING_TEAMS_IN_RESULTS_PATH, self.id, 'csv')
        if os.path.exists(path):
            if team_url not in pd.read_csv(path)['result_link'].values:
                append_row_to_csv(path, {'result_link': result_link, 'position': position},
                                  ['result_link', 'position'])
        else:
            append_row_to_csv(path, {'result_link': result_link, 'position': position},
                              ['result_link', 'position'])
