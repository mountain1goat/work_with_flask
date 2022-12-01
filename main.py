from flask import Flask, request, redirect, jsonify, make_response
from flask_jwt_extended import create_access_token, JWTManager, get_jwt_identity, jwt_required
import sqlite3, uuid, hashlib, random
from werkzeug.security import generate_password_hash, check_password_hash

connect = sqlite3.connect('slinks.db', check_same_thread=False)
cursor = connect.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS "users" (
    id INTEGER NOT NULL, 
    login TEXT NOT NULL, 
    password TEXT NOT NULL,
    PRIMARY KEY ("id" AUTOINCREMENT)
    )"""
    )
connect.commit()

cursor.execute("""CREATE TABLE IF NOT EXISTS "links" (
    id INTEGER NOT NULL,
    login TEXT NOT NULL,
    full_link TEXT NOT NULL, 
    short_link TEXT NOT NULL,
    access TEXT NOT NULL,
    PRIMARY KEY ("id" AUTOINCREMENT)
    )"""
    )
connect.commit()

def registr (cursor,connect, login, password) :
    sql = "INSERT INTO users (login, password) VALUES (:login, :password)"
    cursor.execute(sql, {'login': login, 'password': password})
    connect.commit()
    return True

def signin (cursor, connect, login, password) :
    sql = "SELECT users.* FROM users WHERE login= :login AND password= :password"
    result = cursor.execute(sql, {'login': login, 'password': password}).fetchone()
    connect.commit()
    return result

def isUser (cursor, connect, login) :
    sql = "SELECT users.* FROM users WHERE login= :login"
    result = cursor.execute(sql, {'login': login}).fetchone()
    connect.commit()
    return result

def getLink (cursor,connect, shlink) :
    result = cursor.execute("SELECT links.* FROM links WHERE  short_link=:shlink", {'shlink': shlink}).fetchone()
    connect.commit()
    return result

def allLinksOfUser (cursor,connect, login) :
    sql = "SELECT links.short_link FROM links WHERE login= :login"
    result = cursor.execute(sql, {'login': login}).fetchall()
    connect.commit()
    return result

def addLinks (cursor,connect, login, full_link, short_link, access) :
    sql = "INSERT INTO links (login, full_link, short_link, access) VALUES (:login, :full_link, :short_link, :access)"
    cursor.execute(sql, {'login':login, 'full_link':full_link, 'short_link':short_link, 'access':access})
    connect.commit()

def delLinks (cursor,connect, short_link, login) :
    sql = "DELETE FROM links WHERE login=:login AND short_link=:short_link"
    cursor.execute(sql, {'short_link': short_link, 'login': login})
    connect.commit()

def changeAccLinks (cursor, connect, shlink, access, login) :
    sql = "UPDATE links SET access=:access WHERE short_link=:shlink AND login=:login"
    cursor.execute(sql, {'shlink': shlink, 'access': access, 'login': login})
    connect.commit()

def changeShLinks (cursor,connect, oldshort, newshort, login) :
    sql = "UPDATE links SET short_link=:newshort WHERE short_link=:oldshort AND login=:login"
    cursor.execute(sql, {'oldshort': oldshort, 'newshort': newshort, 'login': login})
    connect.commit()

# access = ['public', 'protected', 'private']

# ---------------------------------------------------------------------------------------
# работа с пользователем

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'jwt-secret-string'
jwt = JWTManager(app)

# регистрация
@app.route("/reg", methods = ['POST'])
def reg():
    login = str(request.json.get("login", None))
    password = str(request.json.get("password", None))
    if signin(cursor, connect, login, password) != None:
        return make_response("User cannot be registered! User with this login already exists")
    else:
        registr(cursor, connect, login, generate_password_hash(password))
        return make_response("User is registered!")

# вход - установление токена
@app.route("/auth", methods = ['POST'])
def auth():
    login = str(request.json.get("login", None))
    password = str(request.json.get("password", None))
    user = isUser(cursor, connect, login)
    if check_password_hash(user[2], password):
        token = create_access_token(identity=login)
        return make_response(f"{login} is logged in. token - {token}")
    else:
        return make_response("check your login and password!")


# ----------------------------------------------------------------------------
# просмотр ссылок

# возврат полной ссылки  (зарегистрированному пользователю)
@app.route("/getlinkuser", methods=['POST'])
@jwt_required()
def get_link_user():
    login = str(get_jwt_identity())
    shlink = str(request.json.get("short_link", None))
    user = isUser(cursor, connect, login)
    link = getLink(cursor, connect, shlink)
    if user != None:
        if user[1] == link[1] and link[4] == 'private':
            if link != None:
                return make_response(f"full link - \n {link[2]}")
            else:
                return make_response("there is no such link")
        else:
            if link != None:
                return make_response(f"full link - \n {link[2]}")
            else:
                return make_response("there is no such link or it is not available to you")
    else:
        return make_response("you are not in the database")

# возврат полной ссылки  (незарегистрированному пользователю)
@app.route("/getlink", methods=['POST'])
def get_link():
    shlink = str(request.json.get("short_link", None))
    link = getLink(cursor, connect, shlink)
    if link != None and link[4] == 'public':
        return make_response(f"full link - \n {link[2]}")
    else:
        return make_response("there is no such link or it is not available to you")


# возврат моих ссылок
@app.route("/getyourlinks", methods=['POST'])
@jwt_required()
def get_your_links():
    login = str(get_jwt_identity())
    links = allLinksOfUser(cursor, connect, login)
    if links != []:
        return make_response(f"all your links \n {links}")
    else:
        return make_response("you haven't links")



# ---------------------------------------------------------------------------------------------------------------------
# работа с ссылками


# добавление ссылки
@app.route("/add_link", methods=['POST'])
@jwt_required()
def add_link():
    login = str(get_jwt_identity())
    # print(login)
    full_link = str(request.json.get("full_link", None))
    short_link = hashlib.md5(full_link.encode()).hexdigest()[:random.randint(8,12)]
    access = 'public'
    addLinks(cursor, connect, login, full_link, short_link, access)
    return make_response(f'you have successfully saved the link! short link is {short_link}')

# удаление ссылки
@app.route("/dellink", methods=['POST'])
@jwt_required()
def del_link():
    login = str(get_jwt_identity())
    shlink = str(request.json.get("short_link", None))
    delLinks(cursor, connect, shlink, login)
    return make_response('you have successfully deleted the link!')

# изменение сокращенной ссылки (псевдоним)
@app.route("/changeshortlink", methods=['POST'])
@jwt_required()
def change_short_link():
    login = str(get_jwt_identity())
    oldshlink = str(request.json.get("old_short_link", None))
    newshlink = str(request.json.get("new_short_link", None))
    changeShLinks(cursor, connect, oldshlink, newshlink, login)
    return make_response('you have successfully change the link!')

# изменение доступа
@app.route("/changeaccesslink", methods=['POST'])
@jwt_required()
def change_access_link():
    login = str(get_jwt_identity())
    shlink = str(request.json.get("short_link", None))
    access = str(request.json.get("access", None))
    changeAccLinks(cursor, connect, shlink, access, login)
    return make_response('you have successfully change the link access!')

# print('good')
app.run()
