import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import datetime
from datetime import date
import glob
import os
import io
from pandas.plotting import table 
from PIL import Image

#renomear conforme arquivo
carteira= pd.read_csv('carteirames_10.csv', sep=',')
opmes= pd.read_csv('resumo11.csv', sep=',')
#--!!!!

# Verifica se todos as transações são do mesmo mês
mesesdict= {1:'Jan',2:'Fev',3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun', 7:'Jul', 8:'Ago',9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}
from dateutil.parser import parse
month=[]
last= parse(opmes.Pregao.loc[opmes.first_valid_index()], dayfirst=True).month
for date in opmes.Pregao.unique():
    moddate= parse(date.replace('C',''), dayfirst=True)
    assert moddate.month == last , f'{moddate.month} mês {last}'
    last= moddate.month
    month.append(moddate)


# Inicia carteira (talvez seja melhor igualar o mes mas nunca deu problema entao ...)
carteira['Operacao'] = 'C'
carteira['Pregao'] = '01/01/0001'
carteira= carteira[['Pregao', 'Operacao','Ticker', 'Quantidade', 'ValorInvestimento']]

opmes= opmes.drop(['Preco/Acao'], axis= 1)

# calcula valor total das despesas do pregão
despesaslist= []
for pregao in opmes.Pregao.unique():
    opmes1= opmes[opmes.Pregao == pregao].copy()
    bruto= 0
    
    for index, row in opmes1.iterrows():
        ticker = opmes1.Ticker[index]
        if opmes1.Operacao[index] == 'C':
            bruto= bruto + opmes1.ValorOp[index]
        elif opmes1.Operacao[index] == 'V':
            bruto= bruto - opmes1.ValorOp[index]
        else:
            break
       
    liquido1= np.round(abs(row['Liquido'] - abs(bruto)),2) 
    opmes1.loc[:,'Despesas']= liquido1
    despesaslist.append(opmes1)


#recria o dataframe com as despesas calculadas
assert  np.all(opmes['Despesas'].values == pd.concat(despesaslist)['Despesas'].values), 'Values do not match'
opmes= pd.concat(despesaslist)

opmes= opmes.sort_values('Pregao')

# calcula valor individual das despesas
despesaslist= []

for pregao in opmes[opmes.Pregao.duplicated()].Pregao:
    opmes1= opmes[opmes.Pregao == pregao].copy()
    bruto= 0
    
    for index, row in opmes1.iterrows():
        ticker = row['Ticker']
    
### Isso aqui funciona
    #calcula valor correto das despesas
        despesa= np.round_(row['Despesas']*(row['ValorOp'] / opmes1['ValorOp'].sum()),2)
#         print(despesa)
        #calcula valor liquido correto
        if row['Operacao'] == 'C':
          liquido= row['ValorOp'] + despesa

        elif row['Operacao'] == 'V':
          liquido= row['ValorOp'] - despesa

        else:
          break

        despesaslist.append([index, despesa, liquido])

for index, despesa, liquido in despesaslist:
  opmes.loc[index,'Despesas'] = despesa
  opmes.loc[index,'Liquido'] = liquido
  
#plotly
def dataframe_to_img(df, title, path='.'):
    import plotly.figure_factory as ff
    n_rows= len(df.index)
    n_cols= len(df.columns)
    fig =  ff.create_table(df)
    #title
    fig.layout.margin.update({'t':50, 'b':100})
    fig.layout.update({'title': f'{title}'})
    #------
    for i in range(len(fig.layout.annotations)):
        fig.layout.annotations[i].font.size = 22
    fig.update_layout(
        autosize=True,
        width=1200,
        height=n_rows*50 + 100,
    )
    fig.write_image(os.path.join(path,title+'.png'), format= 'png', scale=1) #format= 'pdf' é melhor mas muda a compatibilidade
    return

## matplotlib + pandas
# def dataframe_to_img(df, title, path='.'):
#     plt.figure(figsize=(12, 10))
#     ax = plt.subplot(20,1,1, frame_on=False) # no visible frame
#     ax.set_aspect('auto', anchor= 'N')
#     ax.xaxis.set_visible(False)  # hide the x axis
#     ax.yaxis.set_visible(False)  # hide the y axis
#     dftable= table(ax, df)  # where df is your data frame
#     plt.title(title)
#     plt.savefig(os.path.join(path,title+'.png'), dpi=300)
#     return 

dataframe_to_img(opmes, "Operações no mês", path= './relatorios')

operacoes= opmes[['Operacao', 'Ticker', 'Quantidade', 'Liquido']]

######################
try:
    newcarteiralist= carteira.values.tolist() #quando vazio não declarar a carteira = erro
except:
    newcarteiralist= [] #para carteira vazia 
#####################    

for index, row in opmes.iterrows():
    newcarteiralist.append([opmes.Pregao[index], opmes.Operacao[index], opmes.Ticker[index], opmes.Quantidade[index], opmes.Liquido[index]])
    
newcarteira= pd.DataFrame(newcarteiralist, columns= ['Pregao', 'Operacao','Ticker', 'Quantidade', 'ValorInvestimento'])
newcarteira= newcarteira.sort_values(by='Pregao')

ops= ['C', 'V', 'w']
op_compra= []
op_venda= []

newwallet= []
ir_list= []

for ticker in newcarteira.Ticker.unique():
    venda, compra= [np.float32(0),np.float32(0)], [np.float32(0),np.float32(0)]
    temp= newcarteira[newcarteira.Ticker== ticker]

    for i, row in temp.iterrows():
        if row['Operacao'] == 'C':
            compra= [(compra[0] + row["Quantidade"]), (compra[1] + row["ValorInvestimento"])] # quantidade, liquido
            pmcompra= compra[1]/compra[0]

        if row['Operacao'] == 'V':
            venda= [row["Quantidade"], np.round_(row["ValorInvestimento"],2)]
            pmvenda= venda[1]/venda[0]
            lucprej= venda[0]*(pmvenda - pmcompra)

            newquant= compra[0] - venda[0]
            compra= [newquant, (newquant * pmcompra)]

            op_venda.append([ticker, venda[0], venda[1], np.round_(pmcompra*venda[0],2), np.round_(lucprej,2)])

    if compra[0] > 0:      
        op_compra.append([ticker, compra[0], compra[1]])
newwallet= op_compra
ir_list= op_venda

# Calcula IRRF

irrf_list= []
for op in opmes['Pregao'].unique():
    irrf= opmes[opmes.Pregao == op].IRRF.to_list()[0]
    irrf_list.append(irrf)
irrf_total= np.round_(np.sum(irrf_list),2)
#print(f'{irrf_list}, Total: {irrf_total}')

try:
    calculoir= pd.DataFrame(ir_list, columns= ['Ticker', 'Quantidade', 'ValorVenda','ValorCompra', 'Lucro_Prejuizo'])

    lucroprej= np.round_(calculoir.Lucro_Prejuizo.sum(),2)
    vendames= np.round_(calculoir.ValorVenda.sum(),decimals=2)
    calculoir.loc[calculoir.last_valid_index() + 1]= ['Total', '-', vendames,'-', lucroprej]
    if vendames < 20000:
        calculoir.loc[calculoir.last_valid_index() + 1]= ['IR', '-','-', '<R$20000',  'isento']
    else: 
        calculoir.loc[calculoir.last_valid_index() + 1]= ['IR', '15%', '-','-', np.round_(lucroprej*0.15,2)]
        calculoir.loc[calculoir.last_valid_index() + 1]= ['IRRF', irrf_total, '-', 'IR-IRRF',np.round_(lucroprej*0.15-0.85*irrf_total,2)]
        
    dataframe_to_img(calculoir, "Venda de ativos e cálculo do IR", path= './relatorios')
except:
    print('Nenhuma venda realizada')
    
# carteira2= pd.DataFrame(newwallet, columns= ['Ticker', 'Quantidade', 'ValorInvestimento', 'PrecoMedio'])
carteira2= pd.DataFrame(newwallet, columns= ['Ticker', 'Quantidade', 'ValorInvestimento'])

dataframe_to_img(carteira2, "Carteira Atual", path= './relatorios')

file_name = ( f'irmes_{month[1].month}.csv')
calculoir.to_csv(os.path.join('.','relatorios',file_name), index=False)

file2_name = ( f'carteirames_{month[1].month}.csv')
carteira2.to_csv(os.path.join('.','relatorios',file2_name), index=False)

def convert_img(image_path):
    img= Image.open(image_path)
    conv_img= Image.new('RGB', img.size, (255, 255, 255))
    conv_img.paste(img, mask=img.split()[3])
    return conv_img
    

obj= glob.glob('./relatorios/*.png')
img_list= []

for item in obj:
    print(item)
    img_list.append(convert_img(item))
        
pdf1_filename = "Relatorio.pdf"
img_list[0].save(os.path.join('.','relatorios',pdf1_filename), "PDF" ,resolution=100.0, save_all=True, append_images=img_list[1:])
        