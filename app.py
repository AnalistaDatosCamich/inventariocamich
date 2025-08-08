from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import sqlite3
import os
#import qrcode
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/images'

# Inicializar base de datos
def init_db():
    with sqlite3.connect('inventario.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS "objetos" (
            "id"	INTEGER UNIQUE,
            "codigo"	TEXT NOT NULL UNIQUE,
            "descripcion"	TEXT,
            "identificador"	TEXT,
            "usuario"	TEXT,
            "departamento"	TEXT,
            "notas"	TEXT,
            "foto_location"	TEXT,
            PRIMARY KEY("id" AUTOINCREMENT)
        )''')

        conn.execute('''CREATE TABLE IF NOT EXISTS "prefijos" (
            "id"	INTEGER PRIMARY KEY AUTOINCREMENT,
            "prefijo"	TEXT NOT NULL UNIQUE,
            "descripcion"	TEXT
        )''')

        # Insertar algunos prefijos por defecto si no existen
        conn.execute('''INSERT OR IGNORE INTO prefijos (prefijo, descripcion) VALUES 
                       ('MON', 'Monitores'),
                       ('NEV', 'Neveras'), 
                       ('ESC', 'Escritorios')''')

@app.route('/')
def index():
    with sqlite3.connect('inventario.db') as conn:
        items = conn.execute('SELECT * FROM objetos ORDER BY codigo').fetchall()
    return render_template('index.html', items=items)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    item_data = None
    item_id = request.args.get("id")

    if request.method == 'POST':
        #codigo = request.form['codigo']
        descripcion = request.form['descripcion']
        usuario = request.form['usuario']
        departamento = request.form['departamento']
        item_id = request.form.get("id")
        identificador = request.form['identificador']
        notas = request.form['notas']
        
        foto_file = request.files['foto']
        if foto_file and foto_file.filename != '':
            foto_filename = secure_filename(foto_file.filename)
            foto_path = os.path.join(app.config['UPLOAD_FOLDER'], foto_filename)
            foto_file.save(foto_path)
        else:
            foto_filename = None
                    
        with sqlite3.connect('inventario.db') as conn:
            if item_id:  # UPDATE
                if foto_filename:  # Si hay nueva foto
                    conn.execute('''UPDATE objetos SET  descripcion=?, identificador=?, usuario=?, departamento=?, notas=?, foto_location=? WHERE id=?''',
                                (descripcion, identificador, usuario, departamento, notas, foto_filename, item_id))
                else:  # Si no hay nueva foto, mantener la anterior
                    conn.execute('''UPDATE objetos SET  descripcion=?, identificador=?, usuario=?, departamento=?, notas=? WHERE id=?''',
                                (descripcion, identificador, usuario, departamento, notas, item_id))
            else:  # INSERT
                prefijo = request.form['prefijo']  # Cambiamos 'codigo' por 'prefijo'
                # Buscar el último número para este prefijo
                cursor = conn.execute('''SELECT codigo FROM objetos 
                                    WHERE codigo LIKE ? 
                                    ORDER BY codigo DESC LIMIT 1''', (prefijo + '%',))
                ultimo_codigo = cursor.fetchone()
                
                if ultimo_codigo:
                    # Extraer el número del último código
                    ultimo_numero = int(ultimo_codigo[0][len(prefijo):])
                    nuevo_numero = ultimo_numero + 1
                else:
                    nuevo_numero = 1
                
                codigo = f"{prefijo}{nuevo_numero:03d}"  # Formato 001, 002, etc.

                if not foto_filename:
                    foto_filename = "camich.png"
                conn.execute('''INSERT INTO objetos (codigo, descripcion, identificador, usuario, departamento, notas, foto_location)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (codigo, descripcion, identificador, usuario, departamento, notas, foto_filename))
            

                
        return redirect(url_for('admin'))

    if item_id:
        with sqlite3.connect('inventario.db') as conn:
            cursor = conn.execute('SELECT * FROM objetos WHERE id=?', (item_id,))
            item_data = cursor.fetchone()

    with sqlite3.connect('inventario.db') as conn:
        items = conn.execute('SELECT * FROM objetos ORDER BY codigo').fetchall()

    #códigos disponibles
    with sqlite3.connect('inventario.db') as conn:
        prefijos_disponibles = conn.execute('SELECT prefijo, descripcion FROM prefijos ORDER BY prefijo').fetchall()

    return render_template('admin.html', items=items, item=item_data, prefijos = prefijos_disponibles)



@app.route('/delete/<int:item_id>')
def delete(item_id):
    with sqlite3.connect('inventario.db') as conn:
        conn.execute('DELETE FROM objetos WHERE id = ?', (item_id,))
    return redirect(url_for('admin'))

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    with sqlite3.connect('inventario.db') as conn:
        item = conn.execute('SELECT * FROM objetos WHERE id = ?', (item_id,)).fetchone()
    if item:
        return render_template('item.html', item=item)
    return "Artículo no encontrado", 404

def create_qr(item):
    import qrcode
    codigo = item[1]
    descripcion = item[2]
    usuario = item[3]
    departamento = item[4]
    qr_data = f"Código: {codigo} Descripción: {descripcion} Usuario: {usuario} Dpto: {departamento}"
    qr_img = qrcode.make(qr_data)
    return qr_img

@app.route('/admin_prefijos', methods=['GET', 'POST'])
def admin_prefijos():
    if request.method == 'POST':
        prefijo = request.form['prefijo'].upper()
        descripcion = request.form['descripcion']
        
        with sqlite3.connect('inventario.db') as conn:
            try:
                conn.execute('INSERT INTO prefijos (prefijo, descripcion) VALUES (?, ?)', 
                           (prefijo, descripcion))
            except sqlite3.IntegrityError:
                pass  # Prefijo ya existe
    
    with sqlite3.connect('inventario.db') as conn:
        prefijos = conn.execute('SELECT * FROM prefijos ORDER BY prefijo').fetchall()
    
    return render_template('admin_prefijos.html', prefijos=prefijos)

@app.route('/delete_prefijo/<int:prefijo_id>')
def delete_prefijo(prefijo_id):
    with sqlite3.connect('inventario.db') as conn:
        conn.execute('DELETE FROM prefijos WHERE id = ?', (prefijo_id,))
    return redirect(url_for('admin_prefijos'))

"""def save_foto(item):
    foto_file = request.files['foto']
        if foto_file and foto_file.filename != '':
            foto_filename = secure_filename(foto_file.filename)
            foto_path = os.path.join(app.config['UPLOAD_FOLDER'], foto_filename)
            foto_file.save(foto_path)
        else:
            foto_filename = None"""

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
    #app.run(host='0.0.0.0', port=5000, debug=False)
