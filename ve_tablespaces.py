# ve_tablespaces.py

import cx_Oracle

connection = cx_Oracle.connect("lilian", "lilian123", "localhost/XE")

cursor = connection.cursor()
cursor.execute("""
	select tablespace_name, tablespace_size, used_percent 
	from DBA_TABLESPACE_USAGE_METRICS
         """)
for tbsname, tbssize,tbsusedpercent in cursor:
    print("Tablespace:", tbsname, ", Size:", tbssize, ", Used Percent:",tbsusedpercent)  
