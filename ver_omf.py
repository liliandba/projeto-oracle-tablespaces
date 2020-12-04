# ver_omf.py

import cx_Oracle


connection = cx_Oracle.connect("lilian", "lilian123", "localhost/XE")

cursor = connection.cursor()
cursor.execute("""
        select distinct count(*)  
	from gv$parameter 
	where name ='db_create_file_dest' 
	and value is not null
        """)
for v_qtd_parameter in cursor:
    print("Qtd de parametros :", v_qtd_parameter)
