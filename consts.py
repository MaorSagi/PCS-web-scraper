CSV_PATHS = dict(
    cyclists='./data/cyclists.csv',
    teams='./data/teams.csv',
    cyclists_teams='./data/cyclists_teams.csv',
    stages='./data/stages.csv',
    stages_results='./data/stages_results.csv',
)
TIMEOUT = 3
LOG_LEVEL = 'INFO'
DEBUG = LOG_LEVEL
LOG_LEVEL_DICT = {'ERROR': 2, 'WARNING': 1, 'INFO': 0}
MISSING_TEAMS_IN_RESULTS_PATH = 'log/missing_teams_in_results.csv'
MISSING_CYCLISTS_PATH = 'log/missing_cyclists.csv'
MISSING_TEAMS_PATH = 'log/missing_teams.csv'
MISSING_CYCLISTS_IN_TEAMS_PATH = 'log/missing_cyclists_in_teams.csv'

INCOMPATIBLE_TEAMS_NAMES_PATH = 'log/incompatible_team_name.csv'
INCOMPATIBLE_CYCLISTS_TEAMS_PATH = 'log/incompatible_cyclists_teams.csv'
INCOMPATIBLE_STAGES_HEADERS_PATH = 'log/incompatible_stages_headers.csv'

STAGETS_COLS = ['stage_id', 'race_id', 'race_name', 'race_date', 'stage_date', 'stage_name', 'stage_number',
                'stage_type', 'classification', 'nation', 'race_link', 'stage_link', 'race_category',
                'stage_points_scale', 'stage_ranking', 'profile_score', 'parcours_type', 'parcours_type_name',
                'pcs_city_start', 'pcs_city_finish', 'start_time', 'avg_speed_winner', 'distance', 'elevation_gain',
                'elevation_loss', 'elevation_average', 'elevation_maximum', 'elevation_minimum', 'temp_avg',
                'temp_max', 'temp_min', '_1000_to_1500_m', '_1500_to_2000_m', '_2000_to_2500_m',
                '_2500_to_3000_m', '_3000_to_3500_m', 'race_total_distance', 'race_total_elevation_gain'
                ]

CYCLISTS_STAGES_RESULTS_COLS = ['result_id', 'result_type', 'cyclist_id', 'team_id', 'stage_id', 'race_id',
                                'result_pcs_id', 'ranking', 'uci_points', 'pcs_points', 'finish_time', 'time_gap',
                                'result_link']

SPECIAL_RANKING_RESULTS = {'DNF': 'Did not finish', 'DNS': 'Did not start',
                           'OTL': 'Outside time limit', 'DF': 'Did finish, no result',
                           'DSQ': 'Disqualified'}

STAGE_RESULTS_CLASSES = {"Stage": "Stage",
                         "GC": "General classification",
                         "Points": "Points classification",
                         "Youth": "Youth classification",
                         "KOM": "Mountains classification",
                         "Teams": "Teams classification"}

PCS_BASE_URL = "https://www.procyclingstats.com"
RACES_DB_URL = f"{PCS_BASE_URL}/calendar/races-database"
RACES_URL = f"{PCS_BASE_URL}/races.php"
RANKINGS_URL = f'{PCS_BASE_URL}/rankings'
RACE_CLASSES_TO_INCLUDE = ['1.UWT', '2.UWT', '1.Pro', '2.Pro', '1.HC', '2.HC', '1.1', '2.1']
RACE_CLASSES_LEVELS = {
    'HARD': ['1.UWT', '2.UWT'], 'INTERMEDIATE': ['1.Pro', '2.Pro', '1.HC', '2.HC'], 'EASY': ['1.1', '1.2']
}
RACES_CLASS_TO_IGNORE = ['1.Ncup', '2.NCup', 'WC', 'Olympics', 'NC', 'CC', '2.Ncup', 'NCH', 'NE']
SPECIAL_RACE_TYPES = ['General classification', 'Final GC', 'Points classification', 'Youth classification',
                      'Mountains classification', 'Teams classification']

TIME_TRIAL_TYPES = ['Prologue', "Time trial", "Team Time Trial", "Individual Time Trial"]

STAGES_TYPES = ["One day race", "Stage"] + TIME_TRIAL_TYPES

PARCOURS_TYPES = [None, "Flat", "Hills, flat finish", "Hills, uphill finish",
                  "Mountains, flat finish", "Mountains, uphill finish"]
STAGE_RESULT_PROPS = {"One day race": ['Rnk', 'Rider', 'Team', 'UCI', 'Pnt', 'Time'],
                      "Prologue": ["Rnk", "Rider", "Team", "UCI", "Pnt", "Time", "Avg"],  # Short ITT
                      "Individual Time Trial": ["Rnk", "Rider", "Team", "UCI", "Pnt", "Time", "Avg"],
                      "Time trial": ["Rnk", "Rider", "Team", "UCI", "Pnt", "Time", "Avg"],
                      "Stage": ["Rnk", "Rider", "Team", "UCI", "Pnt", "Time"],
                      "Teams classification": ["Rnk", "Prev", "▼▲", "Team", "Class", "Time"],
                      "Team Time Trial": ["Pos.", "Team", "Time", "Timegap", "Speed", "PCS points", "UCI points"]
                      }
