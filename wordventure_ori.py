import pandas as pd
import sqlite3
from typing import Final

conn = sqlite3.connect('vocabulary.db')

TOKEN: Final = ''
BOT_USERNAME: Final = '@jsthlmnbot'

level_list = ['A1', 'A2', 'B1', 'B2', 'C1']
level = input('Choose level: ')
vocab_count = int(input('How many vocabs you want?: '))
if level in level_list:
    sql = f'select * from vocabulary;'
    vocab_df = pd.read_sql_query(sql, conn)

    vocab_df = vocab_df[vocab_df['level'] == f'{level}']

    print(vocab_df[['input']].sample(n=vocab_count))
else:
    print(f'You entered wrong level. Please choose one of this {level_list}')

conn.close()