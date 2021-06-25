import numpy as np
import pandas as pd
import pdfminer

import os
import glob

from io import StringIO
from bs4 import BeautifulSoup

from urllib.request import urlopen

import locale
locale.setlocale(locale.LC_ALL, 'pt_BR');
 
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams

def convert_pdftohtml(filename):
    output = StringIO()
    with open(filename, 'rb') as fin:
        extract_text_to_fp(fin,output,laparams=LAParams(),output_type='html', 
             codec=None)
        Out_txt=output.getvalue()
        return Out_txt
    

directory= os.path.dirname(os.path.realpath(__file__))

pdflist = glob.glob(os.path.join(directory,'*.pdf'))
        
outputdflist= []
operacoesmeslist=[]
for pdffile in pdflist:
    print(pdffile)
    test= convert_pdftohtml(pdffile)
    soup= BeautifulSoup(test, 'html.parser')
    texto1= soup.text
    
    negocios= []
    n=0
    for line in soup.find_all('div'):
        negocios.append([n, line])
        n+=1
            
    neglist= []
    for index, lines in negocios:
        left, top, width, height= 0,0,0,0
        for info in lines.attrs['style'].split(';'):
            if 'left' in info:
                left= info[len('left: '):-len('px')]
            if 'top' in info:
                top= info[len('top: '):-len('px')]
            if 'width' in info:
                width= info[len('width: '):-len('px')]
            if 'height' in info:
                height= info[len('height: '):-len('px')]
        lines1= lines.text.split('\n')[:-1]
        info1= [int(index), int(left), int(top), int(width), int(height), lines1]
        neglist.append(info1)
    
    negdf= pd.DataFrame(neglist, columns= ['line', 'left', 'top', 'width', 'height', 'text'])
    negdf= negdf[negdf["text"].astype(bool)] #removes empty lists
    negdf['textstr'] = [','.join(map(str, l)) for l in negdf['text']] #converte lista p/ string

    number_lst=[]
    for lines in negdf['textstr'].values:
        try:
            number_lst.append(float(locale.delocalize(lines)))
        except:
            number_lst.append(0)
    negdf['numbers'] = number_lst
    
    #cria df com os valores de interesse baseados na posicao do texto (reconstrue a tabela do pdf)
    #Nota de Negociação BB Investimentos
    try:
        r1= pd.DataFrame()
        r1['Negociação']= negdf[negdf.left== 34].sort_values(by=['top']).textstr.values
        r1['C/V']= negdf[negdf.left.between(90,91, inclusive=True)].sort_values(by=['top']).textstr.values
        r1['Mercado']= negdf[negdf.left== 104].sort_values(by=['top']).textstr.values
        r1['Ticker']= negdf[negdf.left== 210].sort_values(by=['top']).textstr.values
        r1['Quantidade']= negdf[(negdf.top.between(271,525, inclusive=True)) & (negdf.left.between(390,426, inclusive=True))].sort_values(by=['top']).numbers.values.astype('int32') #pode dar problema por causa da linha
        r1['Preço']= negdf[negdf.left.between(450,467, inclusive=True)].sort_values(by=['top']).numbers.values
        r1['ValorOp']= negdf[(negdf.top.between(272,524, inclusive=True)) & (negdf.left.between(528-5,536+5, inclusive=True))].sort_values(by=['top']).numbers.values
        r1.head(25)
    except: # para 2 páginas
        r1= pd.DataFrame()
        r1['Negociação']= negdf[negdf.left== 34].sort_values(by=['top']).textstr.values
        r1['C/V']= negdf[negdf.left.between(90,91, inclusive=True)].sort_values(by=['top']).textstr.values
        r1['Mercado']= negdf[negdf.left== 104].sort_values(by=['top']).textstr.values
        r1['Ticker']= negdf[negdf.left== 210].sort_values(by=['top']).textstr.values
        r1['Quantidade']= negdf[(negdf.top.between(271,716, inclusive=True)) & (negdf.left.between(400,420, inclusive=True))].sort_values(by=['top']).numbers.values.astype('int32') #pode dar pobrema por causa da linha
        r1['Preço']= negdf[negdf.left.between(457,467, inclusive=True)].sort_values(by=['top']).numbers.values
        r1['ValorOp']= negdf[(negdf.top.between(272,716, inclusive=True)) & (negdf.left.between(528-5,536+5, inclusive=True))].sort_values(by=['top']).numbers.values
    ####################################################################################################
    
    #adquire outros valores de interesse (date[0],vliq,despesas)
    date= negdf['textstr'].loc[(negdf.top.between(85,95, inclusive=True)) & (negdf.left.between(510,545, inclusive=True))].values
    #verify if its a date
    correctDate = None
    try:
        dateout= pd.Timestamp(date[0])
        correctDate = True
#         print(date[0], date1)
    except ValueError:
        correctDate = False
        print('This string isnt a valid date')
        
    vliq= negdf['textstr'].loc[(negdf.top.between(212-1,212+1, inclusive=True)) & (negdf.left.between(389-5,389+5, inclusive=True))].values.item()
    vliq= float(locale.delocalize(vliq))
    #despesas
    try: #para 1 pagina
        vbrut= negdf.loc[(negdf.top.between(589-1,589+1, inclusive=True)) & (negdf.left.between(530-5,530+5, inclusive=True))]['text'].values.item()[0]
        vbrut= float(locale.delocalize(vbrut))
        
        irrf= negdf[(negdf.top.between(721-5,721+5, inclusive=True)) & (negdf.left.between(544-25,544+5, inclusive=True))].sort_values(by=['top']).text.values[0][0]
        irrf= float(locale.delocalize(irrf))
    
    except: #para 2 paginas
        vbrut= negdf.loc[(negdf.top.between(1480-5,1481+5, inclusive=True)) & (negdf.left.between(530-5,530+5, inclusive=True))]['text'].values.item()[0]
        vbrut= float(locale.delocalize(vbrut))
    
        irrf= negdf[(negdf.top.between(1612-5,1612+5, inclusive=True)) & (negdf.left.between(544-25,544+5, inclusive=True))].sort_values(by=['top']).text.values[0][0]
        irrf= float(locale.delocalize(irrf))
    
    despesas= np.round_(abs(vbrut - vliq), decimals= 2)
    
    #gera df de saída
    outputdf= r1
    outputdf['Pregao']= date[0]
    outputdf['Liquido']= vliq
    outputdf['Despesas']= despesas
    outputdf['IRRF']= irrf
    #troca nomes pelo ticker
    TickersDict= pd.read_csv('TickersDict.csv')
    tickerdict= {}
    for index, row in TickersDict.iterrows():
        tickerdict[row['InvName']]= row['Ticker']
        tickerdict[row['B3Name']]= row['Ticker']
        tickerdict[row['nosName']]= row['Ticker']
        tickerdict[row['Ticker']]= row['Ticker']

    outputdf.Ticker= outputdf.Ticker.str.replace(" ", "").replace(tickerdict)
    #####
    #edições ao pdf de saída para concordancia
    outputdf= outputdf.drop(['Negociação','Mercado'],axis=1)
    outputdf= outputdf[["Pregao", "C/V", "Ticker", "Quantidade", "Preço", "ValorOp", "Liquido", "Despesas", "IRRF"]]
    outputdf.columns= ["Pregao","Operacao","Ticker","Quantidade","Preco/Acao","ValorOp","Liquido","Despesas", "IRRF"]
    outputdflist.append(outputdf)
    
    #RESUMO DO DIA
    #merge tickers to reduce rounding errors
    #CUIDADO COM DAY TRADE
    for ticker in outputdf.Ticker.unique():
        outputdf_t= outputdf[outputdf['Ticker'] == ticker]

        pregao= outputdf_t.Pregao.tolist()[0] #pega primeiro item
        cv= outputdf_t['Operacao'].tolist()[0] #pega primeiro item
        liquido= outputdf_t['Liquido'].tolist()[0] #pega primeiro item
        despesas= outputdf_t['Despesas'].tolist()[0] #pega primeiro item
        irrf= outputdf_t['IRRF'].tolist()[0] #pega primeiro item
        
        quant= outputdf_t.Quantidade.sum()
        valorop= outputdf_t.ValorOp.sum()
        precomedio= valorop / quant

        operacoesmeslist.append([pregao, cv, ticker, quant, precomedio, valorop, liquido, despesas, irrf])

        if ('C' in pd.Series(outputdf_t['Operacao']).tolist()) & ('V' in pd.Series(outputdf_t['Operacao']).tolist()):
            raise Exception('DayTrade', pregao)


resumo_operacoesmes= pd.DataFrame(operacoesmeslist, columns= ["Pregao","Operacao","Ticker","Quantidade","Preco/Acao","ValorOp","Liquido","Despesas", "IRRF"])
resumo_operacoesmes.to_csv('resumomensal.csv', index= False)