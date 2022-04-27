from datetime import date
from Extractor import Extractor
from utils import *


class CyclistTeamsExtractor(Extractor):
    def __init__(self, id=id):
        super().__init__(id=id)

    def get_season_details(self, season, season_period_info, cyclist_url, team_url):
        start_date = date(season, 1, 1)
        stop_date = date(season, 12, 31)
        cyclist_status = 'rider'
        try:
            if 'as from' in season_period_info:
                scripted_date = str(season) + '-' + season_period_info.strip('() ')[
                                                    -2:] + '-' + season_period_info.strip(
                    '() ')[-5:-3]
                start_date = scripted_date
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

            if 'trainee' in season_period_info:
                cyclist_status = 'trainee'
            elif 'until' in season_period_info:
                scripted_date = str(season) + '-' + season_period_info.strip('() ')[
                                                    -2:] + '-' + season_period_info.strip(
                    '() ')[-5:-3]
                stop_date = scripted_date
                stop_date = datetime.strptime(stop_date, "%Y-%m-%d").date()
        except:
            msg = f'Failed to parse season details ,cyclist {cyclist_url},team {team_url}.'
            log(msg, 'ERROR', id=self.id)
            start_date = date(season, 1, 1)
            stop_date = date(season, 12, 31)
            cyclist_status = 'rider'
        return start_date, stop_date, cyclist_status

    def add_missing_team_records(self, team_by_years, team_url_min_year, start_year=None,
                                 csv_path=f'./data/teams_extra.csv'):
        teams_df = get_df('teams')
        while True:
            team_gen_id = random.randint(1000, 99999)
            if team_gen_id not in teams_df['team_gen_id'].values:
                break
        teams_to_add = []
        team_to_add_id = (teams_df['team_id'].max() + 1) if len(teams_df['team_id']) > 0 else 1
        for i in range(len(team_by_years)):
            team = team_by_years[i]
            team_year_txt = team.text.split('|')[0].strip()
            team_year = int(team_year_txt) if check_int(team_year_txt) else None
            if (start_year is not None) and (team_year < start_year):
                continue
            if team_to_add_id in teams_df['team_id'].values:
                raise ValueError(f'Used team id - team_id={team_to_add_id}')
            teams_df = None
            team_to_add_desc_text = team.get_text().split('|')
            team_to_add_name = team_to_add_desc_text[1].strip()
            team_to_add_season = int(team_to_add_desc_text[0].strip())
            url_team_to_add = PCS_BASE_URL + team["value"]
            team_to_add_page = self.browser.get(url_team_to_add)
            team_to_add_class = None
            team_classification = team_to_add_page.soup.find("h1").getText().split(
                team_to_add_name)
            team_classification = team_classification[1] if len(team_classification) > 1 else ''
            parent_idx_open = team_classification.find("(")
            parent_idx_close = team_classification.find(")")
            if (parent_idx_open != -1) and (parent_idx_close != -1):
                team_to_add_class = team_classification[parent_idx_open + 1:parent_idx_close]
            teams_to_add.append(
                [team_to_add_id, team_to_add_season, team_gen_id, team_to_add_name,
                 team_to_add_class, team_url_min_year, url_team_to_add])
            team_to_add_id += 1
        df = pd.DataFrame(teams_to_add,
                          columns=['team_id', 'season', 'team_gen_id', 'team_name',
                                   'team_class',
                                   'team_oldest_pcs_link', 'pcs_link'])
        team_grouped = df.groupby(['team_name', 'team_class']).groups
        for group_key in team_grouped:
            indices_to_drop = team_grouped[group_key][:-1]
            df = df.drop(indices_to_drop)
        df.to_csv(csv_path, mode='a', index=False, header=False)

    def fetch_cyclists_and_cyclists_teams_from_cyclists(self, cyclists_df, cyclist_last=None):
        continue_last_session_pred = cyclist_last is None
        for idx, cyclist in cyclists_df.iterrows():
            try:
                team_url, season = None, None
                cyclist_id = cyclist['cyclist_id']
                cyclist_url = cyclist['pcs_link']
                if (not continue_last_session_pred) and cyclist_url != cyclist_last:
                    continue
                continue_last_session_pred = True
                msg = f'cyclist {cyclist_id}, {cyclist_url}'
                log(msg, id=self.id)
                cyclist_page = self.browser.get(cyclist_url)
                cyclist_teams = cyclist_page.soup.find("ul", attrs={
                    "class": "list rdr-teams moblist"})
                if cyclist_teams:
                    cyclist_teams = cyclist_teams.find_all("li")
                else:
                    headlines = cyclist_page.soup.find_all('h3')
                    for h in headlines:
                        if h.get_text().lower() == 'teams':
                            cyclist_teams = h.parent.parent.find('ul').find_all('li')
                            break

                for cyclist_team in cyclist_teams:
                    try:
                        cyclist_team_txt = cyclist_team.get_text()
                        if ('retire' in cyclist_team_txt) or ('suspended' in cyclist_team_txt):
                            continue
                        ct_details = cyclist_team.contents
                        season = int(ct_details[0].get_text()) if (len(ct_details) > 0) and (
                                ct_details[0]['class'][0] == 'season') else None
                        if (season is None) or ct_details[1].find('a')['href'] == 'team/':
                            continue
                        team_url = f"{PCS_BASE_URL}/{ct_details[1].find('a')['href']}" if (
                                                                                                  len(ct_details) > 1) and (
                                                                                                  ct_details[
                                                                                                      1][
                                                                                                      'class'][
                                                                                                      0] == 'name') else None

                        team_by_years, team_url_min_year = self.get_oldest_team_link(team_url)
                        teams_df = get_df('teams')
                        team_during_seasons = teams_df.loc[teams_df['team_oldest_pcs_link'] == team_url_min_year]
                        if team_during_seasons.empty:
                            log(f'Team {team_url_min_year} does not exists in db', 'WARNING')
                            team_year_txt = team_by_years[-1].text.split('|')[0].strip()
                            team_year = int(team_year_txt) if check_int(team_year_txt) else None
                            curr_year = datetime.now().year
                            last_year = curr_year - 1
                            if team_year in [curr_year, last_year]:
                                self.add_missing_team_records(team_by_years, team_url_min_year)
                        elif len(team_during_seasons.groupby('team_gen_id').groups) > 1:
                            raise ValueError(f'duplicate team record - team={team_url_min_year}')
                        teams_df = get_df('teams')
                        team_during_seasons = teams_df.loc[teams_df['team_oldest_pcs_link'] == team_url_min_year]
                        teams_df = None
                        team_seasons = team_during_seasons.loc[team_during_seasons['season'] <= season]['season']
                        if team_seasons.empty:
                            log(f'team not updated, missing seasons - team={team_url_min_year}', 'WARNING')
                            # TODO: test this method, there must be a bug while the name of the group (if changed or the same,
                            # the exists records should be integrated in the function
                            start_year = team_during_seasons['season'].max()
                            self.add_missing_team_records(team_by_years, team_url_min_year, start_year=start_year)
                        team_id_idx = team_seasons.idxmax()
                        team_id = team_during_seasons.loc[team_id_idx]['team_id']
                        msg = f'team {team_id}, {team_url}'
                        log(msg, id=self.id)
                        season_period_info = ct_details[3].get_text() if (len(ct_details) > 3) else None
                        start_date, stop_date, cyclist_status = self.get_season_details(season, season_period_info,
                                                                                        cyclist_url,
                                                                                        team_url)
                        cyclists_teams = get_df('cyclists_teams')
                        if cyclists_teams.loc[
                            (cyclists_teams['cyclist_id'] == cyclist_id) & (
                                    cyclists_teams['team_id'] == team_id) & (
                                    cyclists_teams['season'] == season)].empty:
                            df = pd.DataFrame(
                                [[cyclist_id, team_id, season, cyclist_status, start_date, stop_date]],
                                columns=['cyclist_id', 'team_id', 'season', 'cyclist_status',
                                         'start_date', 'stop_date'])
                            df.to_csv(f'./data/cyclists_teams.csv', mode='a', index=False, header=False)
                        cyclists_teams = None
                    except:
                        msg = f'Failed to parse cyclist in team - {cyclist_url}, team {team_url}, {season}.'
                        log(msg, 'ERROR', id=self.id)
                        continue
            except:
                msg = f'Failed to parse cyclist - {cyclist_url}.'
                log(msg, 'ERROR', id=self.id)
                continue

    def get_oldest_team_link(self, team_url):
        team_page = self.browser.get(team_url)
        team_by_years = team_page.soup.find_all("option")
        team_url_min_year = f"{PCS_BASE_URL}/{team_by_years[-1].attrs['value']}".split("/overview/")[0]
        return team_by_years, team_url_min_year

    @staticmethod
    def is_cyclist_exists(cyclists_df, cyclist_url):
        return cyclist_url in list(cyclists_df['pcs_link'].values)

    def add_cyclist(self, cyclists_df, cyclist_name_pcs, cyclist_url):
        cyclist_page = self.browser.get(cyclist_url)
        cyclist_name, date_of_birth, nation, pcs_height, pcs_weight = \
            self.redirect_cyclist_page_and_extract_details(cyclist_url, cyclist_page)
        cyclist_id = cyclists_df['cyclist_id'].max() + 1
        df = pd.DataFrame([[cyclist_id, cyclist_name, date_of_birth, nation, pcs_weight,
                            pcs_height, cyclist_url, cyclist_name_pcs]],
                          columns=['cyclist_id', 'full_name', 'date_of_birth', 'nation',
                                   'pcs_weight',
                                   'pcs_height', 'pcs_link', 'cyclist_name_pcs'])
        df.to_csv(CSV_PATHS['cyclists'], mode='a', index=False, header=False)
        return df

    def fetch_cyclists_and_cyclists_teams_from_teams(self, teams_df, team_last=None):
        continue_last_session_pred = team_last is None
        for link, team in teams_df.groupby('team_oldest_pcs_link'):
            if (not continue_last_session_pred) and link != team_last:
                continue
            continue_last_session_pred = True
            team_page = self.browser.get(link)
            team_by_years = team_page.soup.find_all("option")
            for team_by_year in team_by_years:
                team_desc_text = team_by_year.get_text().split('|')
                season = int(team_desc_text[0].strip())
                team_url = f"{PCS_BASE_URL}/{team_by_year.attrs['value']}".split("/overview/")[0]
                msg = f'team {team_url}'
                log(msg, id=self.id)
                team_page = self.browser.get(team_url)
                sessions_cyclists_info = team_page.soup.find('div', attrs={'class': 'fs11 clr999'})
                team_cyclists = sessions_cyclists_info.parent.parent.find_all('li') if sessions_cyclists_info else []
                for cyclist in team_cyclists:
                    try:
                        try:
                            c_details = cyclist.contents
                            cyclist_url = f"{PCS_BASE_URL}/{c_details[1].contents[2].attrs['href']}"
                            msg = f'cyclist {cyclist_url}'
                            log(msg, id=self.id)
                            cyclist_name_pcs = c_details[1].contents[2].get_text()
                            cyclists_df = get_df('cyclists')
                            if not CyclistTeamsExtractor.is_cyclist_exists(cyclists_df, cyclist_url):
                                self.add_cyclist(cyclists_df, cyclist_name_pcs, cyclist_url)
                            cyclists_df = get_df('cyclists')
                            cyclist_df = cyclists_df[cyclists_df['pcs_link'] == cyclist_url]
                            if len(cyclist_df) > 1:
                                raise ValueError(f'Duplicate cyclist record - cyclist={cyclist_url}')
                            # TODO - to remove later?
                            col_dict = {'date_of_birth': 'Date of birth:',
                                        'nation': 'Nationality:', 'pcs_weight': 'Weight:', 'pcs_height': 'Height:'}
                            cyclist_row = cyclist_df.iloc[0]
                            cyclist_idx = cyclist_df.index[0]
                            cyclist_id = cyclist_row['cyclist_id']
                            if (cyclist_name_pcs is not None) and (str(cyclist_row['cyclist_name_pcs']) == 'nan'):
                                cyclists_df = get_df('cyclists')
                                cyclists_df.at[cyclist_idx, 'cyclist_name_pcs'] = cyclist_name_pcs
                                cyclists_df.to_csv('./data/cyclists.csv', index=False, header=True)
                            visited = False
                            for col in cyclist_df.columns:
                                if str(cyclist_row[col]) == 'nan':
                                    cyclist_page = self.browser.get(cyclist_url)
                                    if (col in col_dict) and (col_dict[col] in cyclist_page.soup.get_text()):
                                        if (col_dict[col] == 'Date of birth:') and (
                                                'Date of birth: -' in cyclist_page.soup.get_text()):
                                            continue
                                        if not visited:
                                            cyclist_name, date_of_birth, nation, pcs_height, pcs_weight = \
                                                self.redirect_cyclist_page_and_extract_details(cyclist_url,
                                                                                               cyclist_page)
                                        new_val = eval(col)
                                        if new_val:
                                            visited = True
                                            cyclists_df.at[cyclist_idx, col] = eval(col)
                            if visited:
                                cyclists_df.to_csv('./data/cyclists.csv', index=False, header=True)
                            cyclists_df = None
                        except:
                            msg = f'Failed to parse cyclist {cyclist_url}, team {team_url}, season {season}.'
                            log(msg, 'ERROR', id=self.id)
                            continue
                        team_seasons = team.loc[(team['season'] <= season)]['season']
                        if team_seasons.empty:
                            raise ValueError('should not happend, iterate over teams dataframe')
                        team_id_idx = team_seasons.idxmax()
                        team_record = teams_df.loc[team_id_idx]
                        team_id = team_record['team_id']
                        team_url_min_year = PCS_BASE_URL + team_by_years[-1].attrs['value'].split("/overview/")[0]
                        if team_record['team_oldest_pcs_link'] not in team_url_min_year:
                            raise ValueError('Team selected not match the current cyclist team')
                        cyclists_teams = get_df('cyclists_teams')
                        if cyclists_teams.loc[
                            (cyclists_teams['cyclist_id'] == cyclist_id) & (
                                    cyclists_teams['team_id'] == team_id) & (
                                    cyclists_teams['season'] == season)].empty:
                            start_date, stop_date, cyclist_status = self.get_season_details(season,
                                                                                            c_details[2].get_text(),
                                                                                            cyclist_url, team_url)
                            df = pd.DataFrame(
                                [[cyclist_id, team_id, season, cyclist_status, start_date, stop_date]],
                                columns=['cyclist_id', 'team_id', 'season', 'cyclist_status',
                                         'start_date', 'stop_date'])
                            df.to_csv(f'./data/cyclists_teams.csv', mode='a', index=False, header=False)
                            cyclists_teams = None
                    except:
                        msg = f'Failed to parse cyclist in team - {cyclist_url}, team {team_url},{team_record["team_name"]}, {season}.'
                        log(msg, 'ERROR', id=self.id)
                        continue

    def redirect_cyclist_page_and_extract_details(self, cyclist_url, cyclist_page):
        cyclist_name = cyclist_page.soup.find("h1").getText().replace('  ', ' ')
        c_details = cyclist_page.soup.find("div", attrs={'class': 'rdr-info-cont'}).find(
            'b')
        date_of_birth, nation, pcs_weight, pcs_height = None, None, None, None
        while (c_details is not None):
            try:
                if c_details.get_text() == 'Date of birth:':
                    c_details = c_details.next_sibling
                    day = int(c_details) if (c_details and check_int(str(c_details).strip())) else None
                    c_details = c_details.next_sibling.next_sibling if day else c_details
                    birth_year_month = c_details.split()[0:2] if day else None
                    date_of_birth = datetime.strptime(
                        f'{birth_year_month[1].strip()}-{birth_year_month[0].strip()}-{day}',
                        '%Y-%B-%d').date() if (birth_year_month and day) else None
                elif 'Passed away' in c_details.get_text():
                    if 'Passed away in' in c_details.get_text():
                        c_details = c_details.contents[0].next_sibling.next_sibling if c_details.contents[
                            0].next_sibling else c_details.next_sibling
                    else:
                        c_details = c_details.contents[0].next_sibling.next_sibling.next_sibling if c_details.contents[
                            0].next_sibling else c_details.next_sibling

                elif c_details.get_text() == 'Nationality:':
                    c_details = c_details.next_sibling.next_sibling.next_sibling
                    nation = c_details.get_text() if c_details else None
                elif c_details.get_text() == 'Place of birth:':
                    break
                elif hasattr(c_details, 'contents') and (len(c_details.contents) > 1):
                    str_arr = c_details.contents[1].split() if isinstance(
                        c_details.contents[1],
                        str) else None
                    if str_arr is None:
                        break
                    if c_details.contents[0].get_text() == 'Weight:':
                        pcs_weight = int(str_arr[0]) if (
                                len(str_arr) > 0 and check_int(str_arr[0])) else None
                        if pcs_weight == None:
                            pcs_weight = float(str_arr[0]) if (
                                    len(str_arr) > 0 and check_float(str_arr[0])) else None
                        c_details = c_details.contents[2] if len(
                            c_details.contents[2]) > 2 else None
                        continue
                    elif c_details.contents[0].get_text() == 'Height:':
                        pcs_height = float(str_arr[0]) if (
                                len(str_arr) > 0 and check_float(str_arr[0])) else None
                        break
            except:
                msg = f'Failed to extract cyclist details for cyclist {cyclist_url}.'
                log(msg, 'ERROR', id=self.id)
                c_details = c_details.next_sibling if c_details else None
                continue
            c_details = c_details.next_sibling if c_details else None
        return cyclist_name, date_of_birth, nation, pcs_height, pcs_weight
