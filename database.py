import sqlite3
import os
from flask import g, current_app

DATABASE = 'timetracking.db'

def get_db():
    """Get database connection."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database with tables."""
    db = get_db()
    
    # Create users table
    db.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT UNIQUE NOT NULL,
            funcao TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL CHECK (perfil IN ('admin', 'colaborador')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create punches table
    db.execute('''
        CREATE TABLE IF NOT EXISTS pontos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data DATE NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('entrada', 'saida_almoco', 'volta_almoco', 'saida_final')),
            hora TIME NOT NULL,
            observacao TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Create admin user if not exists
    admin_exists = db.execute(
        'SELECT COUNT(*) as count FROM usuarios WHERE perfil = "admin"'
    ).fetchone()
    
    if admin_exists['count'] == 0:
        from werkzeug.security import generate_password_hash
        db.execute('''
            INSERT INTO usuarios (nome, cpf, funcao, login, senha, perfil)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Administrador', '00000000000', 'Administrador', 'admin', 
              generate_password_hash('admin123'), 'admin'))
    
    db.commit()

# Register teardown handler
from app import app
@app.teardown_appcontext
def close_db_handler(error):
    close_db(error)
