#script ajusta_oracle_tablespaces.py 
 
import cx_Oracle
import db_config

con = cx_Oracle.connect(db_config.user, db_config.pw, db_config.dsn)


# variavel de controle 
v_executa=True 

#definicao do threshold
v_threshold=2
while (v_executa==True):
	cur = con.cursor()
	cur.execute(""" select count(a.tablespace_name) 
			from DBA_TABLESPACE_USAGE_METRICS a, dba_tablespaces b 
			where a.USED_PERCENT > :v_1 
			and b.contents='PERMANENT'  
			and b.bigfile='NO' 
			 """,
			 v_1=v_threshold)
	for t_metrics in cur:  
		v_executa=False
		v_metrics=int(t_metrics[0])  #t_qtd eh do tipo tupla. Precisa converter para usar o if 
		### print v_metrics  # linha para debug - caso necessario saber o valor de v_metrics 
		if (v_metrics == 0):
			print ('OK: Todas as tablespaces estao abaixo do threshold. Nada para ajustar. ') 
		# 	v_executa=False 
		else:
			print ('Atencao: Ha {} tablespaces que serao ajustadas.'.format (v_metrics))



