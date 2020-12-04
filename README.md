PROJETO EM CONSTRUÇÃO 

FONTES DE CONSULTA:
	https://www.eunati.com.br/2017/10/gerenciamento-de-configuracao-devops-parte-3.html
	PEP 8 -- Style Guide for Python Code -> https://www.python.org/dev/peps/pep-0008/



EXPLICAÇÃO DO PROJETO 

	*** Objetivo: automatização de resize de tablespaces no Oracle 
	*** Motivo: nos ambientes de GB, é padrão que todas as tablespaces estejam em crescimento automático, sendo monitorado o crescimento dos discos ao invés da utilização das tablespaces. 
	Porém, em ambientes linux tablespaces compostas por small files crescem até 32TB compostas por datafiles de até 32GB de tamanho. 
	Qdo o datafile chega próximo a este tamanho, atualmente a adição de novos datafiles é feita manualmente pelo DBA. 
	Esta atividade leva em torno de 30 minutos e é feita pelo menos 1 vez por semana nos ambientes de GB. 

	*** OBS: Esta atividade seria menos corriqueira se todas as novas tablespaces fosse criadas como BIGFILE. 


PENDENCIAS
	- Usuário de banco de dados q será utilizado para a ação
	- Grants necessários 
	

MELHORIAS QUE PODEM SER IMPLEMENTADAS NO FUTURO 
	- GERENCIAMENTO DE CONFIGURAÇÃO: Configuração dos servidores de banco pode ser mantida como código através de saltstack. Por exemplo, as próprias configurações de OMF  e gerenciamento de tablespaces que são pre requisitos para este projeto. 
	- Inserir o conceito de orientaçao a objetos no script 
	- Verificação de espaço em disco antes da adição de datafiles (é necessário verificar, tb, se é ASM ou FileSystem) 
	- Configurar o script para olhar na dba_free_space em casos onde o datafile estiver em autoextend=off ou não estiver configurado o maxsize unlimited (não cobertas pela DBA_TABLESPACE_USAGE_METRICS ) 
	- Caso a tablespace seja maior que 1 TB, a sugestão é que o threshold seja ajustado para 95%. Porém, isso requer tb ajustes no sistema de monitoramento (No caso de GB, Nagios). 
	- Configurar o script de ajuste para calcular a quantia exata de datafiles a serem adicionadas. 
		  Uma das fórmulas pensadas é baseada no conceito de PA, onde 
		   An=a1+(n-1) * razão 
		  especificando para o nosso caso, a razão sempre vai ser 32 (tamanho máximo do datafile), a1 é sempre 32 (tam. mínimo de uma tablespace) e n é o calculo do tamanho da tablespace adicionando X datafiles. 
		  Assim
		  An=32GB + ( qtd_datafiles -1) * 32GB 
		  
		  An = 32 + ( (select count(*) from dba_data_files where tablespace_name = 'X') -1 ) * 32  
	  



PRE REQUISITOS

	Oracle acima de 11g
	Python 3
	Biblioteca cx Oracle versão 8  
	
	
	cx_Oracle 7.3 was the last version with support for Python 2.
	





PASSOS SCRIPT ORACLE 


	VERIFICA DB_FILE_DEST CONFIGURADO 
	 -- o valor precisa ser igual a 1 para dar continuidade no fluxo, onde:
	 -- valor zero: indica que o parâmetro não está habilitado;
	 -- valor maior que 1: indica parâmetro diferente em instâncias distintas 
	    Em instâncias Oracle RAC, caso uma das instâncias tenha valor nulo, o script funcionará desde q a instância em questão esteja com o valor habilitado. 
	 *** RETORNO ESPERADO: 1     	 
		 select distinct count(*)  
		 from gv$parameter 
		 where name ='db_create_file_dest' 
		 and value is not null;  





	VERIFICA AUTOEXTEND 
	-- tablespace em autoextend on  
	-- não pode ser tablespace TEMP ou UNDO 
	-- não pode ser bigfile 
	*** RETORNO ESPERADO: ZERO 
		select a.qtd - b.autoext 
		from 
		-- abaixo, num. de datafiles existentes
		( select count(a.file_name)  qtd
			from dba_data_files a, dba_tablespaces b 
			where a.tablespace_name=b.tablespace_name 
			and b.contents='PERMANENT'  
			and b.bigfile='NO') a, 
		-- abaixo, verificando qtos datafiles estao em autoextend=on 
		( select count(a.autoextensible)  autoext
			from dba_data_files a, dba_tablespaces b 
			where a.tablespace_name=b.tablespace_name 
				and b.contents='PERMANENT' 
				and b.bigfile='NO'
				and autoextensible='YES') b ;
	
	
	

	VERIFICA MAXSIZE 
	-- abaixo, verificando se todos estão com maxsize unlimited 
	--  O Oracle limita o número de blocos em um datafile em aproximadamente 4 bilhpões de blocos. 
	-- Ou seja, o tamanho máximo de um datafile depende do parâmetro db_block_size do banco e/ou da tablespace. 
		
		block size   max size
		2k		8GB
		4k		16GB
		8k		32GB 
		
	-- A fórmula para saber o tamanho máximo de um datafile é:
		 	  (4194303 * tamanho_bloco k ) /1024/1024 = tamanho máximo em GB 
	
		-- tamanho máximo do datafile parametrizado no nível do DB (resultado em Gigabytes) s
		select  round (( to_number(value) * 4194303) /1024/1024/1024)  from v$parameter where name = 'db_block_size';	 	  
			 	  
		-- tamanho máximo do datafile verificado na dba_tablespaces 
		select round (( avg(block_size) * 4194303 ) /1024/1024/1024) parametrizado from dba_tablespaces where CONTENTS='PERMANENT'
		
	*** RETORNO ESPERADO: ZERO 
	-- Caso contrário, pode indicar q há tablespaces não configuradas em maxsize unlimited, ou que há tablespaces com db_block_size específicos, saindo do padrão da Área de Growth Business. 
	-- Na área de GB, todos os clientes utilizam db_block_size de 8k, small file 
		select a.valor_medio -  b.parametrizado 
		from 
		( select round (avg(maxbytes/1024/1024/1024)) as valor_medio from dba_data_files) a, 
		( select round (( avg(block_size) * 4194303 ) /1024/1024/1024) parametrizado from dba_tablespaces where CONTENTS='PERMANENT') b ; 
	 

	

	VERIFICA SE HÁ TABLESPACES COM O THRESHOLD INDICADO 
	*** RETORNO ESPERADO: MAIOR QUE ZERO 
	-- caso retorne zero, não há ações a serem tomadas 
		select count(a.tablespace_name) 
		from DBA_TABLESPACE_USAGE_METRICS a, dba_tablespaces b 
		where a.USED_PERCENT > 90 
		and b.contents='PERMANENT'  
		and b.bigfile='NO';

		

	
	VERIFICA QUAL A TABLESPACE DEVERÁ SER AJUSTADA, COLETANDO SEUS DADOS ANTES PARA LOG 
		select  a.tablespace_name, 
			round(a.used_percent) as used_percent,
			count(c.file_name) qtd_datafiles, 
			round(a.tablespace_size*b.block_size/1048576) as tamanho_atual_MB,	
			round(a.used_space*b.block_size/1048576) as usado_MB, -- coluna used_space está em blocos. Por isso a multiplicacao pelo block_size, que está em kb. 
			round(sum(c.maxbytes/1048576)) as tamanho_max_possivel_mb 
		from DBA_TABLESPACE_USAGE_METRICS a, dba_tablespaces b, dba_data_files c
		where a.tablespace_name=b.tablespace_name
		and a.tablespace_name=c.tablespace_name 
		-- abaixo, inteligência da query. Deverá ser ajustada no python. 
		and a.USED_PERCENT > 90
		and b.contents='PERMANENT'  
		and b.bigfile='NO'
		group by a.tablespace_name, round(a.used_space*b.block_size/1048576) , round(a.tablespace_size*b.block_size/1048576), round(a.used_percent) 
		order by 2 desc ;


	AJUSTANDO A TABLESPACE 
	-- isso precisa ser um cursor, pois mais de 1 tablespace poderá precisar de ajuste. 
		select  'alter tablespace ' || 
			(select a.tablespace_name 
				from DBA_TABLESPACE_USAGE_METRICS a, dba_tablespaces b 
				where a.tablespace_name=b.tablespace_name
				and a.USED_PERCENT > 90
				and b.contents='PERMANENT'  
				and b.bigfile='NO') || 
			' add datafile;' 

	
	
	VERIFICANDO TODAS AS TABLESPACES APÓS O AJUSTE. 
	select  a.tablespace_name, 
		round(a.used_percent) as used_percent,
		count(c.file_name) qtd_datafiles, 
		round(a.tablespace_size*b.block_size/1048576) as tamanho_atual_MB,	
		round(a.used_space*b.block_size/1048576) as usado_MB, -- coluna used_space está em blocos. Por isso a multiplicacao pelo block_size, que está em kb. 
		round(sum(c.maxbytes/1048576)) as tamanho_max_possivel_mb 
	from DBA_TABLESPACE_USAGE_METRICS a, dba_tablespaces b, dba_data_files c
	where a.tablespace_name=b.tablespace_name
	and a.tablespace_name=c.tablespace_name 
	-- abaixo, inteligência da query. Ajustar no python. 
	and a.tablespace_name in ('<tablespaces ajustadas>') 
	and b.contents='PERMANENT'  
	and b.bigfile='NO'
	group by a.tablespace_name, round(a.used_space*b.block_size/1048576) , round(a.tablespace_size*b.block_size/1048576), round(a.used_percent) 
	order by 2 desc ;









------------- rascunhos -------------------------

	select a.tablespace_name, 
	round(a.used_space*b.block_size/1048576) as usado_MB, -- coluna used_space está em blocos. Por isso a multiplicacao pelo block_size, que está em kb. 
	round(a.tablespace_size*b.block_size/1048576) as tamanho_MB,
	round(a.used_percent) 
	from DBA_TABLESPACE_USAGE_METRICS a, dba_tablespaces b
	where a.tablespace_name=b.tablespace_name
	-- and a.USED_PERCENT > 90
	and b.contents='PERMANENT'  
	and b.bigfile='NO';
	
	
	
	
----------------------------------------- passo a passo em python ------------------------------------------------------------- 


---------------- VERIFICA DB_FILE_DEST CONFIGURADO (OMF) --------------------------------------------------------------------------------
 -- o valor precisa ser igual a 1 para dar continuidade no fluxo, onde:
 -- valor zero: indica que o parâmetro não está habilitado;
 -- valor maior que 1: indica parâmetro diferente em instâncias distintas 
    Em instâncias Oracle RAC, caso uma das instâncias tenha valor nulo, o script funcionará desde q a instância em questão esteja com o valor habilitado. 
 *** RETORNO ESPERADO: 1   
 *** VARIAVEL RESULTANTE: v_qtd_omf   	 

import cx_Oracle
import db_config

con = cx_Oracle.connect(db_config.user, db_config.pw, db_config.dsn)

cur = con.cursor()
cur.execute("""select distinct count(*) 
		from gv$parameter  
		where name ='db_create_file_dest'   
		and value is not null """)
for t_qtd_omf in cur:  
	v_qtd_omf=int(t_qtd_omf[0])  #t_qtd eh do tipo tupla. Precisa converter para usar o if 
	### print v_qtd_omf  # linha para debug - caso necessario saber o valor de t_qtd_omf 
	if (v_qtd_omf == 1):
		print ('Parametro db_create_file_dest esta corretamente configurado. ') 
	else:
		print ('Parametro db_create_file_dest nao esta correto. Verificar. ') 
    



---------------- VERIFICA AUTOEXTEND ------------------------------------------------------------------------------------------------
-- tablespace em autoextend on  
-- não pode ser tablespace TEMP ou UNDO 
-- não pode ser bigfile 
*** RETORNO ESPERADO: ZERO 
*** VARIAVEL RESULTANTE: v_autoextent 

import cx_Oracle
import db_config

con = cx_Oracle.connect(db_config.user, db_config.pw, db_config.dsn)

cur = con.cursor()
cur.execute("""select a.qtd - b.autoext 
		from 
		/* abaixo, num. de datafiles existentes */ 
		( select count(a.file_name)  qtd
			from dba_data_files a, dba_tablespaces b 
			where a.tablespace_name=b.tablespace_name 
			and b.contents='PERMANENT'  
			and b.bigfile='NO') a, 
		/* abaixo, verificando qtos datafiles estao em autoextend=on */
		( select count(a.autoextensible)  autoext
			from dba_data_files a, dba_tablespaces b 
			where a.tablespace_name=b.tablespace_name 
				and b.contents='PERMANENT' 
				and b.bigfile='NO'
				and autoextensible='YES') b  """)
for t_autoextent in cur:  
	v_autoextent=int(t_autoextent[0])  #t_qtd eh do tipo tupla. Precisa converter para usar o if 
	### print v_autoextent  # linha para debug - caso necessario saber o valor de v_qtd 
	if (v_autoextent == 0):
		print ('Todos os datafiles estao com autoextend on. ') 
	else:
		print ('Verificar: ha datafiles com autoextend off. ') 
		

	 
	 
	 
---------------- VERIFICA MAXSIZE ------------------------------------------------------------------------------------------------
-- abaixo, verificando se todos estão com maxsize unlimited 
--  O Oracle limita o número de blocos em um datafile em aproximadamente 4 bilhpões de blocos. 
-- Ou seja, o tamanho máximo de um datafile depende do parâmetro db_block_size do banco e/ou da tablespace. 
	
	block size   max size
	2k		8GB
	4k		16GB
	8k		32GB 
	
-- A fórmula para saber o tamanho máximo de um datafile é:
	 	  (4194303 * tamanho_bloco k ) /1024/1024 = tamanho máximo em GB 

	-- tamanho máximo do datafile parametrizado no nível do DB (resultado em Gigabytes) s
	select  round (( to_number(value) * 4194303) /1024/1024/1024)  from v$parameter where name = 'db_block_size';	 	  
		 	  
	-- tamanho máximo do datafile verificado na dba_tablespaces 
	select round (( avg(block_size) * 4194303 ) /1024/1024/1024) parametrizado from dba_tablespaces where CONTENTS='PERMANENT'
	
*** RETORNO ESPERADO: ZERO 
**** VARIAVEL RESULTANTE: v_maxsize 
-- Caso contrário, pode indicar q há tablespaces não configuradas em maxsize unlimited, ou que há tablespaces com db_block_size específicos, saindo do padrão da Área de Growth Business. 
-- Na área de GB, todos os clientes utilizam db_block_size de 8k, small file 


import cx_Oracle
import db_config

con = cx_Oracle.connect(db_config.user, db_config.pw, db_config.dsn)

cur = con.cursor()
cur.execute(""" select a.valor_medio -  b.parametrizado 
		from 
			(select round (avg(maxbytes/1024/1024/1024)) as valor_medio 
				from dba_data_files) a, 
			(select round (( avg(block_size) * 4194303 ) /1024/1024/1024) parametrizado 
				from dba_tablespaces 
				where CONTENTS='PERMANENT') b 
		 """)
for t_maxsize in cur:  
	v_maxsize=int(t_maxsize[0])  #t_qtd eh do tipo tupla. Precisa converter para usar o if 
	print v_maxsize  # linha para debug - caso necessario saber o valor de v_maxsize 
	if (v_maxsize == 0):
		print ('esta correto: eh 0') 

 
 
 
---------------- VERIFICA SE HÁ TABLESPACES COM O THRESHOLD INDICADO ------------------------------------------------------------------------------------------------ 
*** RETORNO ESPERADO: MAIOR QUE ZERO
*** VARIAVEL DE RETORNO: v_metrics 
-- caso retorne zero, não há ações a serem tomadas 
		
import cx_Oracle
import db_config

con = cx_Oracle.connect(db_config.user, db_config.pw, db_config.dsn)

cur = con.cursor()
cur.execute(""" select count(a.tablespace_name) 
		from DBA_TABLESPACE_USAGE_METRICS a, dba_tablespaces b 
		where a.USED_PERCENT > 50 
		and b.contents='PERMANENT'  
		and b.bigfile='NO' 
		 """)
for t_metrics in cur:  
	v_metrics=int(t_metrics[0])  #t_qtd eh do tipo tupla. Precisa converter para usar o if 
	print v_metrics  # linha para debug - caso necessario saber o valor de v_metrics 
	
	if (v_metrics == 0):
		print ('nao ha o que ajustar. ') 
	else:
		print ('Ha {} tablespaces para ajustar'.format (v_metrics))
					
					
					
					
					
					
---------------- VERIFICA QUAL A TABLESPACE DEVERÁ SER AJUSTADA, COLETANDO SEUS DADOS ANTES PARA LOG -------------------------------------------------------------------------------- 
	
import cx_Oracle
import db_config

con = cx_Oracle.connect(db_config.user, db_config.pw, db_config.dsn)

cur = con.cursor()
cur.execute("""
		select  a.tablespace_name tbs_name, 
				round(a.used_percent) used_percent,
				count(c.file_name) qtd_datafiles, 
				round(a.tablespace_size*b.block_size/1048576) tamanho_atual_MB,	
				/* abaixo, coluna used_space está em blocos. Por isso a multiplicacao pelo block_size, que está em kb. */ 
				round(a.used_space*b.block_size/1048576) usado_MB, 
				round(sum(c.maxbytes/1048576)) tamanho_max_possivel_mb 
			from 	DBA_TABLESPACE_USAGE_METRICS a, 
				dba_tablespaces b, 
				dba_data_files c
			where a.tablespace_name=b.tablespace_name
			and a.tablespace_name=c.tablespace_name 
			/* abaixo, inteligência da query. Podera ser ajustada no python. */
			and a.USED_PERCENT > 90
			and b.contents='PERMANENT'  
			and b.bigfile='NO'
			group by a.tablespace_name, 
				round(a.used_space*b.block_size/1048576) , 
				round(a.tablespace_size*b.block_size/1048576), 
				round(a.used_percent) 
			order by 2 desc 
	   """)
	   
for t_tbs_name, t_used_percent, t_qtd_datafiles, t_tamanho_atual_MB, t_usado_MB, t_tamanho_max_possivel_mb in cur:
    print(" --------------------- ")
    print("Tablespace: {}".format(t_tbs_name))
    print("Uso: {} % ".format( t_used_percent))
    print("Quantia de Datafiles: {}".format(t_qtd_datafiles))
    print("Tamanho fisico atual: {} MB".format (t_tamanho_atual_MB))
    print("Utilizacao Logica atual: {} MB".format (t_usado_MB))
    print("Tamanho maximo fisico possivel: {} MB".format (t_tamanho_max_possivel_mb)) 
    
				
				
----------------  AJUSTANDO A TABLESPACE  -------------------------------------------------------------------------------- 
import cx_Oracle
import db_config

con = cx_Oracle.connect(db_config.user, db_config.pw, db_config.dsn)

cur = con.cursor()
cur.execute("""
		select  a.tablespace_name tbs_name, 1 -- este 1 eh gambiarra para format do nome da tablespace saindo da tupla. 
			from 	DBA_TABLESPACE_USAGE_METRICS a, 
				dba_tablespaces b
			where a.tablespace_name=b.tablespace_name
			/* abaixo, inteligência da query. Podera ser ajustada no python. */
			and a.USED_PERCENT > 90
			and b.contents='PERMANENT'  
			and b.bigfile='NO'
	   """)
	   
for t_tbs_name , t_gambiarra in cur:
    v_sql= ("alter tablespace  {} add datafile ".format(t_tbs_name))
    print (v_sql) 
    cur.execute (v_sql) 
   
      


	INVESTIGAR ERRO:  ELE ADICIONA APENAS 1 DATAFILE. depois, retorna o erro abaixo: 
		Traceback (most recent call last):
		  File "<stdin>", line 2, in <module>
		cx_Oracle.InterfaceError: not a query

			
							
