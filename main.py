from CyclistTeamsExtractor import CyclistTeamsExtractor
from StageExtractor import StageExtractor
from StatExtractor import StatExtractor
from utils import *

if __name__ == '__main__':
    args = setting_up()
    command = args['command']
    start_year = args['start_year']
    end_year = args['end_year']
    overwrite = args['overwrite']
    if (start_year is not None) and (end_year is not None):
        years_range = range(start_year, end_year)
    elif start_year is not None:
        years_range = range(start_year, 2100)
    elif end_year is not None:
        years_range = range(1900, end_year)
    else:
        years_range = None

    # TODO impl without skip missing in stages results - meaning fix+debug cyclists teams while team is missing

    if command == 'extract_cyclists_teams_from_teams':
        extractor = CyclistTeamsExtractor(id=args['id'])
        teams_df = get_df('teams')
        extractor.fetch_cyclists_and_cyclists_teams_from_teams(teams_df, args['last_session'])

    elif command == 'extract_cyclists_teams_from_cyclists':
        extractor = CyclistTeamsExtractor(id=args['id'])
        cyclists_df = get_df('cyclists')
        extractor.fetch_cyclists_and_cyclists_teams_from_cyclists(cyclists_df, args['last_session'])

    elif command == 'extract_stages':
        # exmple : -c extract_stages -o 1 -d 1
        extractor = StageExtractor(id=args['id'])
        if years_range:
            extractor.fetch_races(args['last_session'], years_range, overwrite)
        else:
            extractor.fetch_races(args['last_session'], overwrite=overwrite)

    elif command == 'extract_stages_from_teams':
        # exmple : -c extract_stages_from_teams -o 1 -d 1
        extractor = StageExtractor(id=args['id'])
        teams_df = get_df('teams')
        extractor.fetch_races_from_teams_program(teams_df, args['last_session'], overwrite=overwrite)

    elif command == 'extract_stages_from_stages':
        # exmple : -c extract_stages_from_stages -o 1 -d 1
        extractor = StageExtractor(id=args['id'])
        if years_range:
            extractor.fetch_races_from_stages(years_range=years_range,link_last=args['last_session'], overwrite=overwrite)
        else:
            extractor.fetch_races_from_stages(link_last=args['last_session'], overwrite=overwrite)

    elif command == 'extract_stages_from_missing_stages':
        # exmple : -c extract_stages_from_stages -o 1 -d 1
        extractor = StageExtractor(id=args['id'])
        if years_range:
            extractor.fetch_races_from_missing_stages(years_range=years_range,link_last=args['last_session'], overwrite=overwrite)
        else:
            extractor.fetch_races_from_missing_stages(link_last=args['last_session'], overwrite=overwrite)


    elif command == 'extract_stages_results':
        # exmple : -c extract_stages_results -ls https://www.procyclingstats.com/race/rund-um-koln/2007
        extractor = StageExtractor(id=args['id'])
        skip_missing = args['skip_missing']
        stages_df = get_df('stages')
        if years_range:
            extractor.fetch_race_results(stages_df, stage_last=args['last_session'], years_range=years_range)
        else:
            extractor.fetch_race_results(stages_df, stage_last=args['last_session'])

    elif command == 'extract_stats':
        # exmple : -c extract_stats -ls https://www.procyclingstats.com/...
        extractor = StatExtractor(id=args['id'])
        cyclists_df = get_df('cyclists')
        if years_range:
            extractor.fetch_speciality_stats(cyclists_df, cyclist_last=args['last_session'],years_range=years_range)
        else:
            extractor.fetch_speciality_stats(cyclists_df,cyclist_last=args['last_session'])
