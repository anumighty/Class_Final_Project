from statistics import mean

import os
import time
import enchant
import pymysql as pymysql

column_names = ['user', 'sentence', 'user_input', 'duration(mins)', 'char_count', 'corr_errs', 'uncorr_errs',
                'wpm', 'acc', 'slowest_digraph', 'slowest_digraph_time(sec)', 'fastest_digraph', 'fastest_digraph_time(sec)']

conn = pymysql.connect(host='mysql.clarksonmsda.org', port=3306, user='ia626',
                       passwd='ia626clarkson', db='ia626', autocommit=True)
cur = conn.cursor(pymysql.cursors.DictCursor)
cur.execute("DROP TABLE IF EXISTS `wahab_keystrokes`;")
sql = '''
    CREATE TABLE IF NOT EXISTS `wahab_keystrokes` (
  `id` int(6) NOT NULL AUTO_INCREMENT,
  `user` varchar(32) NOT NULL,
  `sentence` varchar(512) NOT NULL,
  `user_input` varchar(512) NOT NULL,
  `duration_mins` decimal(12,11) NOT NULL,
  `char_count` varchar(6) NOT NULL,
  `corr_errs` int(4) NOT NULL,
  `uncorr_errs` int(4) NOT NULL,
  `wpm` int(4) NOT NULL,
  `acc` int(4) NOT NULL,
  `slowest_digraph` varchar(16) NOT NULL,
  `slowest_digraph_time_sec` decimal(4,3) NOT NULL,
  `fastest_digraph` varchar(16) NOT NULL,
  `fastest_digraph_time_sec` decimal(4,3) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;'''
cur.execute(sql)

sql = '''INSERT INTO `wahab_keystrokes` (`user`,`sentence`,`user_input`,
`duration_mins`,`char_count`,`corr_errs`,`uncorr_errs`,`wpm`,`acc`,`slowest_digraph`,
`slowest_digraph_time_sec`,`fastest_digraph`,`fastest_digraph_time_sec`)
 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);'''


cur.execute("DROP TABLE IF EXISTS `wahab_summary`;")
sql2 = '''
    CREATE TABLE IF NOT EXISTS `wahab_summary` (
  `id` int(6) NOT NULL AUTO_INCREMENT,
  `user` varchar(32) NOT NULL,
  `total_corr_errs` int(4) NOT NULL,
  `total_uncorr_errs` int(4) NOT NULL,
  `avg_wpm` int(4) NOT NULL,
  `avg_acc` int(4) NOT NULL,
  `overall_slowest_digraph` varchar(16) NOT NULL,
  `overall_slowest_digraph_time_sec` decimal(4,3) NOT NULL,
  `overall_fastest_digraph` varchar(16) NOT NULL,
  `overall_fastest_digraph_time_sec` decimal(4,3) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;'''
cur.execute(sql2)

sql2 = '''INSERT INTO `wahab_summary` (`user`,`total_corr_errs`,`total_uncorr_errs`,`avg_wpm`,`avg_acc`,
`overall_slowest_digraph`,`overall_slowest_digraph_time_sec`,`overall_fastest_digraph`,`overall_fastest_digraph_time_sec`)
 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);'''



def end_of_sentence(id, split_line, input_start, sentence, user_input, corr_errs, slowest_digraph, slowest_digraph_time, fastest_digraph, fastest_digraph_time):
    input_end = int(split_line[6])
    duration = (input_end - input_start) / 60000  # in mins
    char_count = len(sentence)
    input_char_count = len(user_input)
    uncorr_errs = enchant.utils.levenshtein(sentence, user_input)
    wpm = ((input_char_count / 5) - uncorr_errs) / duration
    acc = ((char_count - uncorr_errs - corr_errs) / char_count * 100)
    return (id,sentence,user_input,duration,char_count,corr_errs,uncorr_errs,round(wpm),round(acc),
            slowest_digraph,slowest_digraph_time,fastest_digraph,fastest_digraph_time)


def preprocess_data(in_path):
    files = os.listdir(in_path)
    all_data, summary = [], []
    special_keys = {'32':'SPACE','80':'P','8':'BKSP'}
    for file in files:
        if file == 'metadata_participants.txt' or file == 'readme.txt': continue
        user_data = []
        overall_s_digraph, overall_f_digraph, overall_s_digraph_time, overall_f_digraph_time = 'none', 'none', -1, 100
        all_corr_errs,all_uncorr_errs,all_wpm,all_acc = [],[],[],[]
        with open(raw_path + str(file)) as f:
            lines = f.readlines()
            for l in range(1, len(lines)):
                try:
                    split_line = lines[l].split('\t')
                    try:
                        split_line_prev = lines[l - 1].split('\t')
                        if split_line[1] != split_line_prev[1]:
                            # First character in sentence
                            id = split_line[0]
                            sentence = split_line[2]
                            user_input = split_line[3]
                            input_start = int(split_line[5])
                            corr_errs = 0
                            slowest_digraph, fastest_digraph, slowest_digraph_time, fastest_digraph_time = 'Empty', 'Empty', -1, 100
                    except Exception as e:
                        # First character for the user
                        id = split_line[0]
                        sentence = split_line[2]
                        user_input = split_line[3]
                        input_start = int(split_line[5])
                        corr_errs = 0
                        slowest_digraph, fastest_digraph, slowest_digraph_time, fastest_digraph_time = 'Empty', 'Empty', -1, 100
                    try:
                        split_line_next = lines[l + 1].split('\t')
                    except Exception as e:
                        # last character in user's file
                        df_adder = end_of_sentence(id, split_line, input_start, sentence, user_input, corr_errs, slowest_digraph, slowest_digraph_time, fastest_digraph, fastest_digraph_time)
                        user_data.append(df_adder)
                        #Get user's summary
                        for i in user_data:
                            all_corr_errs.append(i[5])
                            all_uncorr_errs.append(i[6])
                            all_wpm.append(i[7])
                            all_acc.append(i[8])
                        summary.append((id,sum(all_corr_errs),sum(all_uncorr_errs),round(mean(all_wpm)),round(mean(all_acc)),
                                        overall_s_digraph,overall_s_digraph_time,overall_f_digraph,overall_f_digraph_time))
                        all_data = all_data+user_data
                        if len(all_data) > 500:
                            cur.executemany(sql, all_data)
                            conn.commit()
                            all_data = []

                        if len(summary) > 500:
                            cur.executemany(sql2, summary)
                            conn.commit()
                            summary = []

                    if split_line[1] != split_line_next[1]:
                        # last character in sentence
                        df_adder = end_of_sentence(id, split_line, input_start, sentence, user_input, corr_errs, slowest_digraph, slowest_digraph_time, fastest_digraph, fastest_digraph_time)
                        user_data.append(df_adder)

                    elif split_line[1] == split_line_next[1]:
                        if split_line[-2] == 'BKSP' or split_line[-2] == '\x08': # Error found
                            corr_errs += 1
                        # Get fastest & slowest Down-Up digraphs
                        digraph_time = abs((int(float(split_line_next[6])) - int(float(split_line[5])))/1000) # In seconds

                        key1, key1_ascii = split_line[-2], split_line[-1].replace('\n','')
                        key2, key2_ascii = split_line_next[-2], split_line_next[-1].replace('\n','')
                        # Fixing some special keys
                        if key1_ascii in special_keys:
                            key1 = special_keys[key1_ascii]
                        if key2_ascii in special_keys:
                            key2 = special_keys[key2_ascii]
                        if key1.strip() == '':
                            key1 = chr(int(key1_ascii))
                        if key2.strip() == '':
                            key2 = chr(int(key2_ascii))

                        digraph = (key1+key2).strip()
                        if digraph_time < fastest_digraph_time and len(digraph)>=2:
                            fastest_digraph_time = digraph_time
                            fastest_digraph = digraph
                            if fastest_digraph_time < overall_f_digraph_time:
                                overall_f_digraph_time = fastest_digraph_time
                                overall_f_digraph = digraph

                        if digraph_time > slowest_digraph_time and len(digraph)>=2:
                            slowest_digraph_time = digraph_time
                            slowest_digraph = digraph
                            if slowest_digraph_time > overall_s_digraph_time:
                                overall_s_digraph_time = slowest_digraph_time
                                overall_s_digraph = digraph

                except Exception as e:
                    print('row skipped', e, file, split_line_prev, split_line, split_line_next)
                    continue

    # Push remaining data to DB
    if len(all_data) > 0:
        cur.executemany(sql, all_data)
        conn.commit()
    if len(summary) > 0:
        cur.executemany(sql2, summary)
        conn.commit()
    return ''

###################################################################################################################
start_time = time.time()

raw_path = 'C:/Users/Account/Desktop/RESEARCH/NEXT RESEARCH/Aalto Analysis/Aalto Dataset/files/'

preprocess = True
if preprocess:
    df = preprocess_data(raw_path)
print(time.time() - start_time)


