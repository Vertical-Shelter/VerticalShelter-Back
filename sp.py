from app.settings import firestore_db
from app.Partenaires.model  import *
from app.Season_Pass.model import *
from app.Season_Pass.Quetes.models import *
from app.gameDesign.gameObject import *

def createPartenaire(filename):
    #read the csv file
    with open(filename, 'r', encoding="utf-8") as file:
        data = file.read()
    #split the data into rows
    rows = data.split('\n')
    #get the column names
    columns = rows[0].split(';')
    print(len(rows[1:]))
    for row in rows[1:]:
        #split the row into values
        values = row.split(';')
        #create a dictionary of the row
        row_dict = dict(zip(columns, values))
        #add the row to the firestore
        partner = Partner(**row_dict)
        firestore_db.collection('partners').add(partner.dict())
        
def createRecompenses(filename, sp_id):
    with open(filename, 'r', encoding="utf-8") as file:
        data = file.read()
    #split the data into rows
    rows = data.split('\n')
    #get the column names
    columns = rows[0].split(';')
    levels = []
    levels_numero = []
    for row in rows[1:]:
        #split the row into values
        values = row.split(';')
        #decode the values
        #create a dictionary of the row
        row_dict = dict(zip(columns, values))

        if ('numero' in row_dict and row_dict['numero'] == "0"):
            continue
        print(row_dict)
        #add the row to the firestore
        product = Product(**row_dict)

        # get brand n  ame from the row
        brand_name = row_dict['brand_name']
        stream = firestore_db.collection('partners').where('name', '==', brand_name).stream()
        stream = list(stream)
        if len(stream) == 0:
            continue
        
        ref = stream[0].reference
        products = ref.collection('products').stream()
        productExists = False
        for _product in products:
            if _product.to_dict()['name'] == product.name and _product.to_dict()['promotion'] == product.promotion:
                ref_p = _product.reference
                productExists = True
                break
        if not productExists:
            ref_p = ref.collection('products').document()
            ref_p.set(product.dict())
        if (row_dict['numero'] == "0"):
            print('continue')
            continue
        level = Level(**row_dict)
            #check if numero is in the levels
        if level.numero in levels_numero:
            #get the index of the level
            index = levels_numero.index(level.numero)
            if row_dict['isPremium'] == 'VRAI' :
                levels[index].recompense_P = ref_p
            else:
                levels[index].recompense_G = ref_p
        else :
            if row_dict['isPremium'] == 'VRAI' :
                level.recompense_P = ref_p
            else:
                level.recompense_G = ref_p
            levels_numero.append(level.numero)
            levels.append(level)
    for level in levels:
        level_id = firestore_db.collection('season_pass').document(sp_id).collection('level').document().id
        firestore_db.collection('season_pass').document(sp_id).collection('level').document(level_id).set(level.dict())

def createQuete(filename, sp_id, queteType):
    with open(filename, 'r',encoding="utf-8") as file:
        data = file.read()
    #split the data into rows
    rows = data.split('\n')
    #get the column names
    columns = rows[0].split(';')
    for row in rows[1:]:
        #split the row into values
        values = row.split(';')
        #create a dictionary of the row
        row_dict = dict(zip(columns, values))
        print(row_dict)
        #add the row to the firestore
        quete = Quete(**row_dict)

        print(quete.dict())       
        # get brand name from the row
        
        quete_id = firestore_db.collection('season_pass').document(sp_id).collection(queteType).add(quete.dict())

def createBanieres(filename):
    with open(filename, 'r',encoding="utf-8") as file:
        data = file.read()

    rows = data.split('\n')
    columns = rows[0].split(';')
    for row in rows[1:]:
        #split the row into values
        values = row.split(';')
        #create a dictionary of the row
        row_dict = dict(zip(columns, values))
        print(row_dict)
        #add the row to the firestore
        row_dict['is_active'] = row_dict['is_active'] != 'True'
        baniere = Baniere(**row_dict)
        firestore_db.collection('baniere').add(baniere.dict())
        print(baniere.dict())

def createAvatar(filename):
    with open(filename, 'r',encoding="utf-8") as file:
        data = file.read()

    rows = data.split('\n')
    columns = rows[0].split(';')
    for row in rows[1:]:
        #split the row into values
        values = row.split(';')
        #create a dictionary of the row
        row_dict = dict(zip(columns, values))
        print(row_dict)
        #add the row to the firestore
        avatar = Avatar(**row_dict)
        firestore_db.collection('avatar').add(avatar.dict())

createRecompenses('./Manip/SP/product2.csv', '2VtfUH8rmdfdULj52th3')
createQuete('./Manip/SP/queteQuo.csv', '2VtfUH8rmdfdULj52th3', 'quetes_quotidienne')
createQuete('./Manip/SP/queteUnique.csv', '2VtfUH8rmdfdULj52th3', 'quetes_unique')
createQuete('./Manip/SP/queteHebdo.csv', '2VtfUH8rmdfdULj52th3', 'quetes_hebdo')