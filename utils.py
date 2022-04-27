import argparse
import os
import random
import re
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from unidecode import unidecode
import pandas as pd

from consts import *


debug = DEBUG

def check_int(sting):
    return re.match(r"[-+]?\d+(\.0*)?$", sting) is not None


def check_float(sting):
    return re.match(r'^-?\d+(?:\.\d+)$', sting) is not None


def append_row_to_csv(file_path, row, columns=None):
    if columns == None:
        columns = list(row.keys())
    df = pd.DataFrame([row], columns=columns)
    file_exists = os.path.exists(file_path)
    if not file_exists:
        df.to_csv(file_path, header=True, index=False)
    else:
        df.to_csv(file_path, mode='a', header=False, index=False)


def generate_id(gen_ids):
    while True:
        generated_id = random.randint(1000, 99999)
        if generated_id not in gen_ids:
            break
    gen_ids.add(generated_id)
    return generated_id


def setting_up():
    global debug

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--command', type=str)
    parser.add_argument('-id', '--id', type=str)
    parser.add_argument('-ls', '--last-session', type=str)
    parser.add_argument('-sy', '--start-year', type=int)
    parser.add_argument('-ey', '--end-year', type=int)
    parser.add_argument('-sk', '--skip-missing', type=int)
    parser.add_argument('-o', '--overwrite', type=int)
    parser.add_argument('-d', '--debug', type=str)

    args = parser.parse_args()
    id = args.command
    if args.id:
        id = f"{id}_{args.id}"

    args_dict = dict(
        command=args.command,
        last_session=args.last_session,
        start_year=args.start_year,
        end_year=args.end_year,
        skip_missing=args.skip_missing,
        id=id,
        overwrite=args.overwrite
    )
    if args.debug:
        if debug in LOG_LEVEL_DICT.keys():
            debug = args.debug
        else:
            debug = LOG_LEVEL

    if args.command is None:
        raise ValueError('Cannot run the job without a command')

    log(f'', id=id)
    log(f'', id=id)
    log(f'====================================================================', id=id)
    log(f'{args_dict}', id=id)
    log(f'', id=id)
    log(f'', id=id)

    return args_dict


def log(msg, type='INFO', id=''):
    global debug
    Path('./log/').mkdir(parents=True, exist_ok=True)
    type = type.upper()
    if LOG_LEVEL_DICT[type] >= LOG_LEVEL_DICT[LOG_LEVEL]:
        if type == 'ERROR':
            msg += f' ERROR DETAILS: {traceback.format_exc()}'
        msg = f'{type}\t{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\t{msg}\n'
        with open(f'./log/{type}_{id}.log', 'a+') as f:
            f.write(unidecode(msg))
        if debug and (LOG_LEVEL_DICT[type] >= LOG_LEVEL_DICT[debug]):
            print(f'{msg}'.replace("\n", ""))


def timeout_wrapper(func):
    def wrap(self, msg, *args, **kwargs):
        trials = 0
        while trials < TIMEOUT:
            try:
                result = func(self, *args, **kwargs)
                return result
            except:
                trials += 1
                if trials == TIMEOUT:
                    log(msg, 'ERROR')

    return wrap


def get_df(table_name, index_col=None):
    if os.path.exists(CSV_PATHS[table_name]):
        return pd.read_csv(CSV_PATHS[table_name], index_col=index_col)
