
# Faz importação das bibliototecas nescessárias para rodar o programa:
from selenium.webdriver.chrome.options import Options # Referente às opções de inicialização do chrome
from selenium.webdriver.common.keys import Keys # referente às teclas (usado para digitar)
from selenium.webdriver.common.by import By # referente aos tipos de filtros em find_element no selenium
from selenium import webdriver # referente aos navegadores
from dbfread import DBF # referente ao arquivo dbf utilizado para filtro do que já foi cadastrado
from os import listdir # referente a função listdir (lista arquivos de um determinado diretório / pasta)
import pandas as pd # manipulador de dados tabulados
import datetime # data e hora
import time # temporizador
import json # arquivos de configuração e mapemanto
import os # sigla para Operational System, representa nosso manipulador de coisas referentes ao sistema operacional, como controle de arquivos, pastas, etc.

# Dicionário de Palavras Chaves:
## Base de Dados: Normalmente é o excel que possui as informações dos pacientes para notificação
## DBF: Arquivo .dfb que é utilizado para fazer filtro inicial dos pacientes que já foram notificados
## Formulário Notificação: refere-se ao formulário onde se é cadastrado as notificaçõs com base na base de dados.

ESCOLARIDADE_MAP = json.load(open('escolaridade_map.json')) # carrega o arquivo de mapeamento de escolaridade onde a chave encontra-se na Base de Dados e o Valor é o que deve ser colocado no Formulário
BAIRRO_MAP = json.load(open('bairro_map.json')) # carrega o arquivo de mapeamento de bairros onde a chave encontra-se na Base de Dados e o Valor é o que deve ser colocado no Formulário
UNIDADE_MAP = json.load(open('unidade_map.json')) # carrega o arquivo de mapeamento de unidades onde a chave encontra-se na Base de Dados e o Valor é o que deve ser colocado no Formulário
# Esses mapeamentos são referentes à erros de na base de dados do excel que precisam ser preenchidos, então eles seguem um padrão de chave e valor onde a chave está dentro do excel e o valor é o que queremos que essa chave se transforma, é como se fosse uma função f que recebe um valor e retorna outro valor f(valor no excel) = valor no site

ano_vigente = datetime.datetime.now().year # obtém o ano vigente
DATA_INICIAL = datetime.datetime(year=ano_vigente, month=1, day=1).strftime("%d/%m/%Y")
DATA_FINAL = datetime.datetime.now().strftime("%d/%m/%Y")
NOTIFICACAO_URL = "https://sinan.saude.gov.br/sinan/secured/consultar/consultarNotificacao.jsf" # URL de Consulta de Notificação do Site Sinan
LOGIN_URL = "http://sinan.saude.gov.br/sinan/login/login.jsf" # URL de Login do Site Sinan
SELECIONAR_AGRAVO_URL = "http://sinan.saude.gov.br/sinan/secured/notificacao/individual/selecionarAgravo.jsf" # URL que dá inicio ao preencheimento do formulário dando a opção de selecionar agravo
USER = input("Digite seu usuário: ") # nome do usuário usado para fazer login no Sinan
PASS = input("Digite a sua senha: ") # senha do usuário usado para fazer login no Sinan

AGRAVO = "A90 - DENGUE" # nome do agravo onde será preeenchido o formulário, esta informação pode mudar para outro agravo como por exemplo "A92.0 - FEBRE DE CHIKUNGUNYA"

def normalizar_data_nascimento(data:str, idade:int):
    """Recebe nascimento em formato %d/%m/%y e idade, e retorna data de nascimento em formato %d/%m/%Y"""
    data_atual = datetime.datetime.now() # objeto de data e hora atuais
    dia, mes, decada_real = data.split("/") # "dia/mes/ano" -> [dia, mes, ano]
    decada_real = int(decada_real)
    ano_nascimento = data_atual.year - idade # ano atual - idade em anos
    decada = ano_nascimento % 100 # dois dígitos finais, por exemplo: 1998 % 100 = 98
    if decada > decada_real:
        ano_nascimento -= 1 # pode haver erro de um ano de diferença, por isso esta verificação
    return f"{dia}/{mes}/{ano_nascimento}"

def limpar_tela(): os.system("cls" if os.name == "nt" else "clear") # função que limpa a tela do console independente do sistema operacional


def obter_base():
    """Função que obtém a base de dados que será utilizada para preencher as notificações
    
    Esta função deve criar um "stats_{DATA_INICIO_EXECUCAO}.json" indicando algumas estatíticas antes e depois de ser aplicado certos filtros nesta base de dados.
    """
    limpar_tela()
    if not os.path.exists("arquivos"):
        os.makedirs("arquivos")
        print("Aviso: Não existia diretório de arquivos, por favor, colque as bases de dados, arquivos dentro do local descrito abaixo:")
        print("\t", os.path.join(os.getcwd(), "arquivos"))
        print("Após ter feito isso, rode o programa novamente.")
        exit(1)

    possiveis_bases = [base for base in listdir("arquivos") if base.split(".")[-1] in ["xlsx", "csv", "xls"]] # cria uma lista de arquivos de base dedados que terminam com .xlsx, .csv ou .xls, ou seja, uma lista de possíveis arquivos
    if len(possiveis_bases) == 0:
        print("Aviso: não existem bases de dados, por favor, colque as bases de dados, arquivos dentro do local descrito abaixo:")
        print(os.path.join(os.getcwd(), "arquivos"))
        print("Após ter feito isso, rode o programa novamente.")
        exit(1)
    
    # o trecho de código abaixo é ferente à escolha do arquivo e como ler esse arquivo dependendo de sua extensão (csv, excel, etc)
    print("Escolha a base de dados desejada:")
    for i, base in enumerate(possiveis_bases, 1):
        print(f"[{i:3}] Base de Dados: {base}")
    base = possiveis_bases[int(input("\n>> ")) - 1]
    print(f"Base de Dados Selecionada: {base}")
    base = f"arquivos/{base}"
    if base.endswith(".csv"):
        base_df = pd.read_csv(base)
    elif base.endswith(".xlsx"):
        base_df = pd.read_excel(base)
    elif base.endswith(".xls"):
        base_df = pd.read_excel(base)
    

    ### O trecho de código abaixo refere-se aos filtros iniciais aplicados sobre os dados ###
    # 1. Remoção de Linhas dulicadas (exatamente iguais a nível de string ('A' é diferente de 'a'))
    colunas_consideradas = ["Nome Paciente", "Data Nascimento", "Nome Mãe"] # define a lista de colunas que serão consideradas para dropar as linhas duplicadas, ou seja, só se é removida uma linha quando essas 3 colunas apresentam duplicidade simultâneamente.
    stats = {} # dicionário de estatísticas antes e depois de aplicar os filtros sobre a base de dados
    stats["Linhas antes do Filtro de Duplicidade (só excel)"] = base_df.shape[0] # define o número de linhas antes do filtro
    base_df = base_df.drop_duplicates(subset=colunas_consideradas) # dropa as linhas duplicadas
    stats["Linhas depois do Filtro de Duplicidade (só excel)"] = base_df.shape[0] # define o número de linhas depois do filtro
    stats["Quantidade de Linhas Duplicadas (só excel)"] = stats["Linhas antes do Filtro de Duplicidade (só excel)"] - base_df.shape[0] # define o número de linhas duplicadas


    # 2. Aplicação de filtro pelo DBF
    possiveis_dbfs = [dbf for dbf in listdir("arquivos") if dbf.endswith(".dbf")] # cria uma lista de arquivos de base de dados que terminam com .dbf
    if len(possiveis_dbfs) == 0:
        print("Aviso: não existem bases de dados que terminam com .dbf, por favor, coloque as bases de dados, arquivos dentro do local descrito abaixo:")
        print("\t", os.path.join(os.getcwd(), "arquivos"))
        print("Após ter feito isso, rode o programa novamente.")
        exit(1)
    # o trecho de código abaixo é referente à escolha do arquivo e como ler esse arquivo dependendo de sua extensão (dbf)
    print("Escolha o DBF desejado:")
    for i, dbf in enumerate(possiveis_dbfs, 1):
        print(f"[{i:3}] DBF: {dbf}")
    dbf = possiveis_dbfs[int(input("\n>> ")) - 1]
    print(f"DBF Selecionado: {dbf}")
    dbf = f"arquivos/{dbf}"
    print("Abrindo DBF para filtro de dados...")
    dbf_df = DBF(dbf, encoding="latin-1") # cria um objeto do tipo DBF
    dbf_df = pd.DataFrame(iter(dbf_df)) # transforma o objeto em DataFrame para podermos aplicar filtros com ferramentas do pandas

    dbf_df["DT_NASC"] = dbf_df["DT_NASC"].apply(lambda linha: None if linha is None else linha.strftime("%d/%m/%Y")) # aplica a função lambda sobre cada uma das linhas de DT_NASC fazendo com que ela retorne None caso a linha seja nula ou transforma em string no formato dia/mes/ano caso a linha não seja nula

    colunas_dbf = ['NM_PACIENT', 'NM_MAE_PAC'] # define a lista de colunas que devem ser consideradas para remover alguma linha da base de dados (nome do paciente e nome da mãe).
    for column in colunas_dbf:
        dbf_df[column] = dbf_df[column].apply(lambda linha: None if linha is None else linha.lower()) # para cada uma das linhas da coluna espeficada por "column" transforme em lowercase (tudo minuscula) caso a linha seja não nula.
    
    total_linhas = base_df.shape[0]
    count = 1
    for i, linha_base in base_df.iterrows():
        print(f"\rAnalisando linha {count} de {total_linhas}...", end="", flush=True)
        count += 1
        # Tradução das Colunas:
        # na base de dados "Nome de Paciente" é o mesmo que "NM_PACIENT" no dbf
        # na base de dados "Nome da Mãe" é o mesmo que "NM_MAE_PAC" no dbf
        # na base de dados "Data Primeiros Sintomas" é o mesmo que "DT_SIN_PRI" no dbf
        # na base de dados "Data Nascimento" é o mesmo que "DT_NASC" no dbf
        idade_base = int(linha_base["Idade"].split()[0].strip()) # tem este split pois na coluna "Idade" na base pode aparecer como "27 anos", por exemplo.
        data_nascimento_base = normalizar_data_nascimento(linha_base["Data Nascimento"], idade_base)
        nome_paciente_base = str(linha_base["Nome Paciente"]).lower() # nome do paciente em letras minúsculas
        nome_mae_base = str(linha_base["Nome Mãe"]).lower() # nome da mae em letras minúsculas
        data_primeiros_sintomas_base = datetime.datetime.strptime(str(linha_base["Data Primeiros Sintomas"]), "%d/%m/%Y") # data de primeiros sintomas (objeto)

        # a variável "resultados" abaixo refere-se à uma pesquisa, um filtro aplicado da seguinte maneira:
        # pesquisa todas as linhas dentro da base DBF onde o nome do paciente é o nome do paciente que estamos tratando agora, e o nome da mae é o nome da mae que estamos tratando agora, e a data de nascimento é a data de nascimento que estamos tratando agora, pegue esses resultados e salve dentro da variável de resultados
        resultados = dbf_df.loc[
            (dbf_df["NM_PACIENT"] == nome_paciente_base) &
            (dbf_df["NM_MAE_PAC"] == nome_mae_base) &
            (dbf_df["DT_NASC"] == data_nascimento_base) 
        ]

        if len(resultados) > 0: # se a quantidade de resultados for meior do que 0
            for j, resultado in resultados.iterrows():
                data_objeto = resultado["DT_SIN_PRI"] # obtém o objeto de data de primeiros sintomas (datetime.date)
                data_primeiros_sintomas_dbf = datetime.datetime(data_objeto.year, data_objeto.month, data_objeto.day) # transforma esse objeto em datetime.datetime ao invés de datetime.date
                if abs((data_primeiros_sintomas_dbf - data_primeiros_sintomas_base).days) <= 15: # se a diferenca entre a data de primeiros sintomas da base e do dbf for menor ou igual à 15 dias, então remove a linha da base de dados
                    base_df = base_df.drop(i) # remoção da linha
                    break # como já foi removido, não precisa verificar mais, então só parar o loop.
    stats["Linhas depois do Filtro de DBF"] = base_df.shape[0]
    stats["Quantidade de Duplicidades (com DBF)"] = stats["Linhas depois do Filtro de Duplicidade (só excel)"] - base_df.shape[0] # define o número de linhas duplicadas
    stats_filename = "stats_{}.json".format(DATA_INICIO_EXECUCAO.strftime("%d-%m-%Y_%H.%M.%S")) # define o nome do arquivo de estatísticas
    if not os.path.exists("stats"):
        os.makedirs("stats")
    stats_path = os.path.join("stats", stats_filename)
    with open(stats_path, "w") as file:
        json.dump(stats, file, indent=4, ensure_ascii=False) # salva as estatísticas
    print() # para acabar com o "end=''"
    return base_df # retorna a base de dados para que possa ser usada como variável global


def login():
    """Função de login, abre a página de login, verifica se já está logado, caso contrário faz login"""
    navegador.get(LOGIN_URL) # carrega a página de login
    navegador.find_element(By.ID, "form:username").send_keys(USER) # encontra o elemento de id "form:username" e envia o texto da variável "USER"
    navegador.find_element(By.ID, "form:password").send_keys(PASS) # encontra o elemento de id "form:password" e envia o texto da variável "PASS"
    navegador.find_element(By.XPATH, '/html/body/div[4]/form/fieldset/div[4]/input').click() # encontra o botão de submissão do formulário de login e senha e clica nele para fazer login.
    # TODO: Fazer um sistema de verificação se já está logado, por enquanto assume-se que essa função só será chamada uma única vez (no início)


def wf(by:str, value:str, try_click:bool=True, return_element:bool=True):
    """Função que representa um sistema de verificação de elemento com base em while
    
    PseudoSintaxe: 
        enquanto não conseguir fazer algo com o elemento, tente novamente até que consigar fazer algo com ele
        esse "algo com o elemento" pode ser simplesmente o encontrar (find_element) como o clicar (click)
    """
    while True: # repita infinitamente o seguinte:
        try: # tente fazer algo com o elemento
            if try_click: # se é pra clicar
                navegador.find_element(by, value).click() # tente encontrar o elemento e clique nele com os parametros especificados
            else: # caso contrário, só tente encontrar o elemento
                navegador.find_element(by, value)
        except: # caso algumas das ações acima dê erro, então tente novamente
            continue # continue para a próxima iteração do laço while
        else: # caso tenha feito a ação e nada de errado aconteceu, não estourou nenhum erro, então:
            if return_element: # se deve retornar o elemento encontrado, então
                return navegador.find_element(by, value) # retorna o elemento
            else:
                return # caso contrário retorne nada, mas deve ser retornado para parar o while.



def preencher_notificacao(linha):
    """Preenche uma notificação com base nos dados presentes dentro da variável linha e verifica se tudo ta certo"""
    # O processo de preencher uma notificação com os dados especificados nesta linha em específico consista em 4 passos principais
    # 1. Verificar se o usuário está logado
    # 2. verifica se o número de notificação já foi ao Sistama do Sinan, caso sim, pula
    # 3. Caso o número de notificação ainda não tenha sido cadastrado no perído especificado, então deve preeencher o forumlário de notificação de boa
    # 4. Após o bot terminar de preeencher o formulário com os dados presentes dentro de "linha" e que ele ACHA que adicionou tudo certinho é hora de verificar por ele mesmo, ou seja, volta para o passo 2 e verifica se o número de notificação foi realmente colocando dentro do sistema do Sinan, caso tenha sido colocado, congrulations, tudo certo e nada errado, caso contrário, aí vemos o que fazer, se fazemos o bot tentar novamente ou fazer com que ele pule, salve isso no log e boa
    
    log = {
        coluna: '' for coluna in log_colunas
    } # inicializa o dicionário de log contendo as colunas já especificadas ({"coluna_nome": ""})

    ####################################################################################################################
    ### Trecho de código referente ao passo 1 ###
    # Verifica se o usuário está logado:
    # login() 
    # vai ficar comentado pois o bot é rápido o suficiente para resetar a sessão por si mesmo, portanto não precisa fazer re-login.
    

    ####################################################################################################################
    ### Trecho do Código Referente ao passo 2 ###
    # Verifica se o número de notificação já foi ao Sistama do Sinan, caso sim, pula
    # Não carece fazer mais esta verificação pois o bot ao preecnher o formulário já verifica se o número de notificação já foi cadastrado, e pula caso tenha sido.

    tempo_inicio = time.time() # data atual em segundos

    ####################################################################################################################
    ### Trecho do Código Referente ao passo 3 ###
    while True: # execute infinitamente o código abaixo:
        try: # tente fazer o seguinte:
            navegador.get(SELECIONAR_AGRAVO_URL) # abra o link de selecionar agravo
            navegador.find_element(By.XPATH, '/html/body/div[4]/form/p/input[1]').click() # tente encontrar o botão de selecionar agravo e clica nele
        except: # caso a ação de clicar não seja possível, ou seja, dê erro
            continue # continue o loop para que repita o processo novamente
        else: # caso contrário, ou seja, deu tudo certo, clicou no agravo correspondente
            break # então pare o loop
    # O loop while acima eu fiz questão de documentar para que entendas o que a função "wf" faz, a partir daqui será usado a sintaxe da função "wf"

    ## -> Verifica se o formulário de preeencher notificação já apareceu
    wf('xpath', '//*[@id="form:panelNotificacao"]', try_click=False, return_element=False) # encontre o elemento por "xpath" que possua o valor especificado, não tente clicar nele e nem retorne o elemento.

    ## -> Preeche o número de Notificação
    valor = linha["Nº"] # obtém o valor da coluna "Nº"
    print(f"Preenchendo: {'Número da Notificação':35} : {valor}") # imprime o número de notificação
    wf('xpath', '//*[@id="form:nuNotificacao"]', try_click=False).send_keys(valor) # encontre o elemento por "xpath" que possua o valor especificado, não tente clicar nele e retorne o elemento para ser usado como variável para send_keys enviar o valor
    log['Nº'] = valor # salva o número de notificação no dicionário de log

    ## -> Preenche agravo da Doença
    valor = AGRAVO # definido no início do script
    print(f"Preenchendo: {'Agravo da doença':35} : {valor}") # imprime o agravo
    wf('xpath', '//*[@id="form:richagravocomboboxField"]').send_keys(valor) # encontre o elemento por "xpath" que possua o valor especificado, não tente clicar nele e retorne o elemento para ser usado como variável para send_keys enviar o valor
    wf('xpath', '//*[@id="form:richagravolist"]/span', return_element=False) # encontre o elemento por "xpath" que possua o valor especificado, tente clicar nele e não retorne o elemento. (esse caso aqui são os selectBox)


    ## -> Preenche data de Notificação
    valor = linha["Data Notificação"] # obtém o valor da coluna "Data Notificação"
    valor = valor.replace("/", "") # substitui "/" por "" (ou seja, remove os "/")
    print(f"Preenchendo: {'Data Notificação':35} : {valor}") # imprime a data de notificação
    wf('xpath', '//*[@id="form:dtNotificacaoInputDate"]').send_keys(valor) # encontre o elemento por "xpath" que possua o valor especificado, tente clicar nele e retorne o elemento para ser usado como variável para send_keys enviar o valor
    wf('xpath', '//*[@id="form:panelNotificacao"]', return_element=False) # encontre o elemento por "xpath" que possua o valor especificado, tente clicar nele e não retorne o elemento. (Neste caso aqui, estamos clicando em "painelNotificacao" para que o foco saia da data de notificação para que o SITE Sinan rode seu script que verifica se já foi cadastrado e mostre aquele popUP inicial)
    log['Data Notificação'] = valor # salva a data de notificação no dicionário de log

    ## -> Verifica se a Notificação já foi cadastrada de acordo com um possível popUP que pode ter sido mostrado agora
    print("Verificando se a notificação já foi cadastrada...")
    try: navegador.find_element('xpath', '//*[@id="form:panelNotificacao"]').click() # tente clicar num campo aleatório, caso isso de erro
    except:
        print("###### Notificação já cadastrada #######")
        log["Status"] += "Notificação já cadastrada\n" # então quer dizer que já foi cadastrada
        log["Tempo de Preenchimento"] = time.time() - tempo_inicio
        return log
    # caso contrário continue

    # Preenche Unidade Saúde
    valor = linha['Unidade Saúde (ou outra fonte notificadora)'].split()[0] # obtém o valor da coluna "Unidade Saúde (ou outra fonte notificadora)" e pega seu primeiro elemento (0)
    # "0019402 - IMPERIAL HOSPITAL DE CARIDADE" -> ['0019402', 'IMPERIAL', 'HOSPITAL', 'DE', 'CARIDADE']
    # '0019402' -> se isso daqui não for um número, então pergunte qual é o número desse CNES
    try: # tente
        int(valor) # converter para inteiro (se isso daqui for um texto, vaiu ndar erro e entra no except)
    except: # este é o excpet :D
        chave_da_unidade_map = " ".join(linha['Unidade Saúde (ou outra fonte notificadora)'].split()[1:]).upper()
        if chave_da_unidade_map not in UNIDADE_MAP: # se a chave não ta dentro do dicionário
            log["Status"] += f"Unidade Saúde ({chave_da_unidade_map}) não ta dentro do unidade_map.json.\n" # avise no log
            log["Tempo de Preenchimento"] = time.time() - tempo_inicio
            return log # e pare o preecnhimento retornando o log para salvar.
        valor = UNIDADE_MAP[chave_da_unidade_map] # pega o valor da chave que é o número do CNES
        if valor == '0000000':
            log["Status"] += f"Erro na unidade notificadora ({chave_da_unidade_map}) CNES vazio.\n" # avise no log
            log["Tempo de Preenchimento"] = time.time() - tempo_inicio
            return log

    print(f"Preenchendo: {'Unidade Saúde':35} : {valor}")
    wf('xpath', '//*[@id="form:notificacao_unidadeSaude_coCnes"]', try_click=False).send_keys(valor) # encontre o elemento por "xpath" que possua o valor especificado, não tente clicar nele e retorne o elemento para ser usado como variável para send_keys enviar o valor
    log['Unidade Saúde (ou outra fonte notificadora)'] = valor # salva a Unidade Saúde (ou outra fonte notificadora) no dicionário de log

    # Preenche Data Primeiros Sintomas
    valor = linha["Data Primeiros Sintomas"].replace('/', '') # 08/08/2006 => 08082006
    print(f"Preenchendo: {'Data Primeiros Sintomas':35} : {valor}")
    wf('xpath', '//*[@id="form:nuNotificacao"]', return_element=False) # encontre o elemento por "xpath" que possua o valor especificado, tente clicar nele e não retorne o elemento
    element = wf('xpath', '//*[@id="form:dtPrimeirosSintomasInputDate"]') # encontre o elemento por "xpath"
    for _ in range(len(valor)*2): # len(" / / ") = 5 * 2 = 10
        element.send_keys(Keys.BACKSPACE) # apague o que tiver lá dentro
    element.send_keys(valor) # envie o valor
    wf("xpath", '//*[@id="form:panelNotificacao"]', return_element=False) # e mude o foco para outro elemento
    log['Data Primeiros Sintomas'] = valor # salva a Data Primeiros Sintomas no dicionário de log


    # Preenche Nome do Paciente
    valor = linha['Nome Paciente'] # obtém o valor da coluna "Nome Paciente"
    print(f"Preenchendo: {'Nome Paciente':35} : {valor}")
    old_valor = wf('xpath', '//*[@id="form:notificacao_nomePaciente"]').get_attribute('value') # obtém o que tiver de valor dentro da tag "input"
    for _ in range(len(old_valor)*2):
        wf('xpath', '//*[@id="form:notificacao_nomePaciente"]', try_click=False).send_keys(Keys.BACKSPACE) # apague tudo que tiver lá dentro
    wf('xpath', '//*[@id="form:notificacao_nomePaciente"]', try_click=False).send_keys(valor)
    log['Nome Paciente'] = valor


    # Preenche Data de Nascimento
    valor = linha['Data Nascimento']
    idade = int(linha["Idade"].lower().strip("anos").strip("ano").strip("meses").strip("mes").strip())
    valor = normalizar_data_nascimento(data=valor, idade=idade).replace("/", "")
    print(f"Preenchendo: {'Data Nascimento':35} : {valor}")
    element = wf('xpath', '//*[@id="form:dtNascimentoInputDate"]')
    old_valor = element.get_attribute('value')
    for _ in range(len(old_valor)*2):
        element.send_keys(Keys.BACKSPACE)
    element.send_keys(valor)
    wf("xpath", '//*[@id="form:panelNotificacao"]', return_element=False)
    log['Data Nascimento'] = valor

    # Preenche Sexo
    valor = str(linha['Sexo']).strip()
    print(f"Preenchendo: {'Sexo':35} : {valor}")
    wf('xpath', '//*[@id="form:nuNotificacao"]', return_element=False)
    wf('xpath', '//*[@id="form:notificacao_paciente_sexo"]', return_element=False)
    options = navegador.find_elements('xpath', '//*[@id="form:notificacao_paciente_sexo"]/option')
    for option in options:
        if option.text.strip().lower() == valor.lower():
            option.click()
            break
    log['Sexo'] = valor
    
    
    # Preenche Paciente Gestante
    print(f"Preenchendo: {'Paciente Gestante':35} : {valor == 'Feminino'}")
    if valor == 'Feminino':
        wf('xpath', '//*[@id="form:notificacao_paciente_gestante"]', return_element=False)
        options = navegador.find_elements('xpath', '//*[@id="form:notificacao_paciente_gestante"]/option')
        for option in options:
            # option.text -> "-"
            # "Selecione" -> ["Selecione"]
            # "2 - 2º Semestre" -> ["2 ", " 2º Semestre"] 
            # => " 2º Semestre" => "2º Semestre" => "2º semestre"
            if option.text.endswith("Não"):
                option.click()
                break
    log['Paciente Gestante'] = "Não" 


    # Preecnhe Paciente Raça
    # "( 3 ) Parda" -> ['(', '3', ')', 'Parda'] -> "Parda" -> "parda"
    valor = linha["Raça/Cor"].split()[-1].lower().strip()
    print(f"Preenchendo: {'Raça/Cor':35} : {valor}")
    wf('xpath', '//*[@id="form:notificacao_paciente_raca"]', return_element=False)
    for option in navegador.find_elements('xpath', '//*[@id="form:notificacao_paciente_raca"]/option'):
        if option.text.split()[-1].lower().strip() == valor:
            option.click()
            break
    log["Raça/Cor"] = valor
    
    # Preenche Escolaridade
    valor = ESCOLARIDADE_MAP[str(linha["Escolaridade"])]
    print(f"Preenchendo: {'Escolaridade':35} : {valor}")
    if idade >= 7:
        wf('xpath', '//*[@id="form:notificacao_paciente_escolaridade"]', return_element=False)
        options = navegador.find_elements('xpath', '//*[@id="form:notificacao_paciente_escolaridade"]/option')
        for option in options:
            if option.text.strip() == valor:
                option.click()
                break
    log['Escolaridade'] = valor
    

    # Preecnhe Nome Mãe
    valor = str(linha["Nome Mãe"]).strip()
    print(f"Preenchendo: {'Nome Mãe':35} : {valor}")
    if valor != "nan":
        wf('xpath', '//*[@id="form:notificacao_nome_mae"]', try_click=False).send_keys(valor)
    log['Nome Mãe'] = valor
    

    # Preenche Paciente endereco Municipio Uf Id
    valor = linha['UF Residência']
    print(f"Preenchendo: {'UF Residência':35} : {valor}")
    wf('xpath', '//*[@id="form:notificacao_paciente_endereco_municipio_uf_id"]',  return_element=False)
    options = navegador.find_elements('xpath', '//*[@id="form:notificacao_paciente_endereco_municipio_uf_id"]/option')
    for option in options:
        if option.text.strip() == valor:
            option.click()
            break
    wf("xpath", '//*[@id="form:nuNotificacao"]', return_element=False)
    log['UF Residência'] = valor


    # Preecnhe Paciente Endereço Muncípio ID
    valor = linha["Município Residência"].split()[1]
    print(f"Preenchendo: {'Município Residência':35} : {valor}")
    wf('xpath', '//*[@id="form:notificacao_paciente_endereco_municipio_id"]').send_keys(valor)
    wf("xpath", '//*[@id="form:nuNotificacao"]', return_element=False)
    log['Município Residência'] = valor


    # Preenche Bairro
    if valor == '420504': # valor aqui é cod_monicípio (e este if é pra filtrar por florianópolis)
        valor = BAIRRO_MAP[linha['Bairro']] if linha['Bairro'] in BAIRRO_MAP else linha['Bairro']
    else:
        valor = linha['Bairro']
    print(f"Preenchendo: {'Bairro':35} : {valor}")

    # caso bairro venha vazio, ignore, NAO IDENTIFICADO
    if str(valor).lower().strip() not in ['nan', '', 'nao identificaddo']:
        wf('xpath', '//*[@id="form:notificacao_paciente_endereco_bairro_noBairrocomboboxField"]').send_keys(valor)
        options = navegador.find_elements('xpath', '//*[@id="form:notificacao_paciente_endereco_bairro_noBairrolist"]/span')
        if options:
            options[0].click()
    log['Bairro'] = valor
    
    # Preeenche Logradouro
    valor = linha["Logradouro"].split(',', maxsplit=1)[0]
    print(f"Preenchendo: {'Logradouro':35} : {valor}")
    wf('xpath', '//*[@id="form:notificacao_paciente_endereco_noLogradouro"]').send_keys(valor)
    log['Logradouro'] = valor

    # Preenche Número da Casa
    valor = str(linha["Número"]).split('.')[0]
    print(f"Preenchendo: {'Número da Casa':35} : {valor}")
    if valor.lower() not in ['nan', '00', '0']:
        wf('xpath', '//*[@id="form:notificacao_paciente_endereco_numeroCasa"]').send_keys(valor)
    log['Número'] = valor
    

    # Preenche Complemento
    valor = str(linha["Complemento"])
    print(f"Preenchendo: {'Complemento':35} : {valor}")
    if valor.lower() not in ['nan', '']:
        wf('xpath', '//*[@id="form:notificacao_paciente_endereco_complemento"]').send_keys(valor)
    log['Complemento'] = valor
    

    # Preenche ponto de Referencia
    # valor = f"{linha['Ponto de Referência']}/{linha['Telefone 2']}".replace("nan", '').replace('NaN', '').replace('Nan', '').strip('/').strip()
    valor = str(linha['Telefone 2']).strip().lower().strip('nan') # retirado textos desse campo
    print(f"Preenchendo: {'Ponto de Referência':35} : {valor}")
    if valor != '':
        wf('xpath', '//*[@id="form:notificacao_paciente_endereco_pontoReferencia"]').send_keys(valor)
    log['Ponto de Referência'] = valor
    

    # Preenche CEP
    valor = str(linha['CEP']).replace(".", '').replace('-', '')
    print(f"Preenchendo: {'CEP':35} : {valor}")
    old_valor = wf('xpath', '//*[@id="form:notificacao_paciente_endereco_cep"]').get_attribute('value')
    for _ in range(len(old_valor)*2):
        wf('xpath', '//*[@id="form:notificacao_paciente_endereco_cep"]', try_click=False).send_keys(Keys.BACKSPACE)
    wf('xpath', '//*[@id="form:notificacao_paciente_endereco_cep"]', try_click=False).send_keys(valor)
    log['CEP'] = valor


    # Preeecnhe Telefone
    valor = str(linha["Telefone 1"]).lower()
    print(f"Preenchendo: {'Telefone 1':35} : {valor}")
    # tirando todos os espaços
    while ' ' in valor: # wnautno tiver espaço dentro do valor
        valor = valor.replace(' ', '') # substitua todas as ocorrencias de espaço por vazio ('')
    valor = valor.replace("(", "").replace(")", "") # remove os caracterres "(" e ")"
    valor = valor.replace("-", "") # remover os "-"
    valor = valor.replace("+", "") # remover os "+" (e talvez tirar os 55 da frente se houver usando .lstrip('55'))
    if valor not in ['nan', ''] and len(valor) >= 10:
        wf('xpath', '//*[@id="form:notificacao_paciente_telefone"]').send_keys(valor)
    elif len(valor) < 10 and valor not in ['nan', '']:
        log["Status"] += f"O telefone {valor} não possui pelo menos 10 caracteres!\n"
    log['Telefone 1'] = valor
    

    # Preenche Zona
    valor = '1 - urbana'
    print(f"Preenchendo: {'Zona':35} : {valor}")
    wf('xpath', '//*[@id="form:notificacao_paciente_endereco_zona"]', return_element=False)
    options = navegador.find_elements('xpath', '//*[@id="form:notificacao_paciente_endereco_zona"]/option')
    for option in options:
        if option.text.strip().lower() == valor:
            option.click()
            break
    log['Zona'] = valor

    # Agora precisa clicar em OK e fazer algumas verificações
    print("Clicando em 'Ok' para submissão de dados...")
    wf('xpath', '//*[@id="form:botaoOk"]', return_element=False)
    log["Tempo de Preenchimento"] = time.time() - tempo_inicio

    start_time = time.time()
    MAX_TIME = 15 # em segundos
    # O trecho abaixo verifica todos os possíveis popUps que o site pode apresentar
    while True:
        if time.time() - start_time > MAX_TIME:
            log["Status"] += f"O tempo para verificar todas as possíveis respostas do site ao clicar em 'Ok' excedeu o tempo limite de {MAX_TIME} segundos!\n"
            break
        # após clicar em ok, pode ser que aparece esse popUP falando que a notificação foi cadastrada e não precisa de investigação
        try:
            navegador.find_element('xpath', '//*[@id="form:modalNotificacaoCadastradaSemInvestigacaoContentTable"]/tbody/tr/td/center/input[2]').click() # isso daqui tenta clicar em "Ok" nesse popUP
        except: ...
        else:
            log['Status'] += "Apareceu popUP falando que a notificação foi cadastrada e não precisa de investigação!\n"
            break

        # de tempos em tempos aparece esse popUP especial, não lembro o que seria, mas aparece e nós tratamos :D
        try:
            navegador.find_element('xpath', '//*[@id="form:btnNovaNotificacao"]').click() # clica em ok nesse popUP especial
        except: ...
        else:
            log['Status'] += "Apareceu popUP especial falando que a notificação foi cadastrada e simplesmente mostrava um botão para fazer nova notificação.\n"
            break

        # outro popUp possível é o de possível duplo, abaixo está o tratamento dele:
        try:
            navegador.find_element('xpath', '//*[@id="form:btnSalvarPossivelDup"]').click() # clica em ok nesse popUP
        except: ...
        else:
            log['Status'] += "Apareceu popUP falando que a notificação foi cadastrada e que pode ser uma possível duplicação.\n"
            break
        
        # no site tem uma tag com id = "erros" onde geralmente é mostrado algumas mensagens de erro / sucesso após clicar em "OK"
        try: # tente
             mensagem_site = navegador.find_element("xpath", '//*[@id="erros"]').text.strip() # se tiver
        except: ...
        else:
            if mensagem_site:
                log["Status"] += "Mensagem do Site: {}\n".format(mensagem_site)
                break

    ####################################################################################################################
    ### Trecho do Código Referente ao passo 4 ###
    tempo_inicio = time.time()
    print("Verificando se foi cadastrado realmente... (consulta por Nº da Notificação)", end="")
    navegador.get(NOTIFICACAO_URL) # carrega a página de consulta

    tag_data = wf("xpath", '//*[@id="form:consulta_dataInicialInputDate"]') # obtém o campo de data inicial
    for _ in range(len(tag_data.get_attribute("value"))*2): # limpa o que tiver dentro
        tag_data.send_keys(Keys.BACKSPACE) # apague tudo que tiver lá dentro
    tag_data.send_keys(DATA_INICIAL.replace("/", "")) # e envia a data inicial

    tag_data = wf("xpath", '//*[@id="form:consulta_dataFinalInputDate"]') # obtém o campo de data final
    for _ in range(len(tag_data.get_attribute("value"))*2): # limpa oq tiver dentro
        tag_data.send_keys(Keys.BACKSPACE) # apague tudo que tiver lá dentro
    tag_data.send_keys(DATA_FINAL.replace("/", "")) # e envia a data final

    wf("xpath", '//*[@id="form:richagravocomboboxField"]', return_element=False)
    opcoes = navegador.find_elements("xpath", '//*[@id="form:richagravocomboboxField"]/option')
    valor = AGRAVO # definido no início do script
    wf('xpath', '//*[@id="form:richagravocomboboxField"]').send_keys(valor) # encontre o elemento por "xpath" que possua o valor especificado, não tente clicar nele e retorne o elemento para ser usado como variável para send_keys enviar o valor
    wf('xpath', '//*[@id="form:richagravolist"]/span', return_element=False) # encontre o elemento por "xpath" que possua o valor especificado, tente clicar nele e não retorne o elemento. (esse caso aqui são os selectBox)
    
    time.sleep(1)
    opcoes = navegador.find_elements("xpath", '//*[@id="form:tipoUf"]/option') # obtém as opções de UF - Notificação ou Residência
    for opcao in opcoes:
        if opcao.text.strip() == "Notificação ou Residência":
            opcao.click() # e clica nela
            break
    time.sleep(1)
    campos = navegador.find_elements("xpath", '//*[@id="form:consulta_tipoCampo"]/option') # obtém as opções de campo
    for campo in campos:
        if campo.text.strip() == "Número da Notificação": # seleciona o campo de número da notificação
            campo.click() # e clica nela
            break
    time.sleep(1)
    wf("xpath", '//*[@id="form:consulta_dsTextoPesquisa"]').send_keys(linha["Nº"]) # envia o critério de seleção
    time.sleep(1)
    wf("xpath", '//*[@id="form:btnAdicionarCriterio"]', return_element=False) # clica no botão de "adicionar" critério de seleção
    time.sleep(1)
    wf("xpath", '//*[@id="form:btnPesquisar"]', return_element=False) # clica no botão de "pesquisar"
    # agora verifica se ao pesquisar apareceu algum resultado
    while True:
        try:
            navegador.find_element("xpath", '//*[@id="form:panelFiltroUtilzado"]').click()
        except:
            continue
        else:
            time.sleep(0.5)
            break
    try:
        navegador.find_element("xpath", '//*[@id="form:panelResultadoPesquisa"]')
    except:
        print("Não foi cadastrado! (Resultado salvo em log)")
        log["Status"] += 'Análise Final: Consulta de Nº da Notificação feita e NÃO houve resultados!\n'
        # return preencher_notificacao(linha)
        # log = preencher_notificacao(linha)
    else:
        print("Foi foi cadastrado! (Resultado salvo em log)")
        log["Status"] += 'Análise Final: Consulta de Nº da Notificação feita e houve resultados!\n'
    
    log["Status"] = "; ".join(log["Status"].splitlines())
    log["Tempo de Consulta"] = time.time() - tempo_inicio
    return log
    

def preencher_notificacoes():
    global DATA_INICIO_EXECUCAO # define como variável global o termo "DATA_INICIO_EXECUCAO"
    global log_df # define como variável global o termo "log_df"
    global base_df # define como variável global o termo "base_df"
    global log_colunas # define como variável global o termo "log_colunas"
    # Nota: ser global, significa que estas variáveis após serem criadas aqui podem ser utilizadas fora do escopo da função mesmo após esta função tiver terminado.
    DATA_INICIO_EXECUCAO = datetime.datetime.now()
    
    base_df = obter_base()
    log_filename = "log_{}.xlsx".format(DATA_INICIO_EXECUCAO.strftime("%Y-%m-%d_%H.%M.%S")) # define o nome do arquivo de log
    if not os.path.exists("logs"):
        os.makedirs("logs")
    log_path = f"logs/{log_filename}"
    log_colunas = list(base_df.columns)
    log_colunas.extend(["Zona", "Tempo de Preenchimento", "Tempo de Consulta", "Status"]) # extende a lista colocando mais algumas colunas que não estaõ dentro de base_df mas que são nescessárias.
    log_df = pd.DataFrame(columns=log_colunas) # define um dataframe vazio somente definido suas colunas 
    login() # chama a função que faz login no Sinan e libera o webdriver (navegador)
    count = 0
    for i, linha in base_df.iterrows(): # para cada linha da base de dados que já está filtrada, faça o que tiver abaixo:
        print(f"Iniciando preenchimento de formulário {count} de {len(base_df)}...")
        count += 1
        dict_log = preencher_notificacao(linha) # chama a função que preenche a notificação com os dados contidos dentro de "linha", essa função deve retornar um dicionário de log que vai conter as colunas especificadas nas log_colunas
        log_df.loc[len(log_df)] = dict_log # adiciona o dicionário de log na última linha do dataframe
        log_df.to_excel(log_path, index=False) # salva o dataframe atual no arquivo de log (se ele não existe, é criado, caso ele já exista, sobreescreve atualizando-o
        dict_log = None # limpa o dicionário de log
        print("\n-------------------------------------\n")


def painel():
    """Um pequeno painel de controle para o Programa"""
    print(
        f"Informações:\n"
        f"Nome do Usuário: {USER}\n"
        f"Agravo Selecionado: {AGRAVO}\n"
        f"Data Inicial | Data Final: {DATA_INICIAL} | {DATA_FINAL}\n"
    )

    opts = [
        "Preencher Notificações",
        "Sair"
    ]
    for i, opt in enumerate(opts, 1):
        print(f"{i}: {opt}")
    opt = int(input("Digite a opção desejada: "))
    if opt == 1:
        preencher_notificacoes()
    else:
        exit(0)

if __name__ == "__main__":
    limpar_tela()
    navegador = webdriver.Chrome()
    while True:
        painel()