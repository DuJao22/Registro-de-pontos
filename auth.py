from flask_login import UserMixin
from flask import current_app
from database import get_db
from app import login_manager

class User(UserMixin):
    def __init__(self, id, nome, cpf, funcao, login, perfil):
        self.id = id
        self.nome = nome
        self.cpf = cpf
        self.funcao = funcao
        self.login = login
        self.perfil = perfil
    
    @staticmethod
    def get(user_id):
        db = get_db()
        user_data = db.execute(
            'SELECT * FROM usuarios WHERE id = ?', (user_id,)
        ).fetchone()
        
        if user_data:
            return User(
                id=user_data['id'],
                nome=user_data['nome'],
                cpf=user_data['cpf'],
                funcao=user_data['funcao'],
                login=user_data['login'],
                perfil=user_data['perfil']
            )
        return None
    
    @staticmethod
    def get_by_login(login):
        db = get_db()
        user_data = db.execute(
            'SELECT * FROM usuarios WHERE login = ?', (login,)
        ).fetchone()
        
        if user_data:
            return User(
                id=user_data['id'],
                nome=user_data['nome'],
                cpf=user_data['cpf'],
                funcao=user_data['funcao'],
                login=user_data['login'],
                perfil=user_data['perfil']
            )
        return None
    
    @staticmethod
    def check_password(login, password):
        from werkzeug.security import check_password_hash
        db = get_db()
        user_data = db.execute(
            'SELECT senha FROM usuarios WHERE login = ?', (login,)
        ).fetchone()
        
        if user_data and check_password_hash(user_data['senha'], password):
            return True
        return False

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)
