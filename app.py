from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import os
#import qrcode
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
import io
from PIL import Image as PILImage


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

@app.route('/item/<codigo>')
def item_detail(codigo):
    with sqlite3.connect('inventario.db') as conn:
        item = conn.execute('SELECT * FROM objetos WHERE codigo = ?', (codigo,)).fetchone()
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

@app.route('/responsiva/<codigo>')
def generar_responsiva(codigo):
    with sqlite3.connect('inventario.db') as conn:
        item = conn.execute('SELECT * FROM objetos WHERE codigo = ?', (codigo,)).fetchone()
    
    if not item:
        return "Artículo no encontrado", 404
    
    # Crear PDF en memoria
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                           topMargin=0.5*inch, bottomMargin=0.5*inch,
                           leftMargin=0.75*inch, rightMargin=0.75*inch)
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                fontSize=14, spaceAfter=12, alignment=TA_CENTER)
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'],
                                 fontSize=11, spaceAfter=6, alignment=TA_LEFT)
    justify_style = ParagraphStyle('CustomJustify', parent=styles['Normal'],
                                  fontSize=11, spaceAfter=12, alignment=TA_JUSTIFY)
    
    # Contenido del documento
    story = []
    
    # Encabezado
    story.append(Paragraph("<b>CAMICH LERMA CHAPALA</b>", title_style))
    story.append(Paragraph("Colonia Los Ángeles", normal_style))
    story.append(Spacer(1, 12))
    
    # Fecha actual
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
         'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    hoy = datetime.now()
    fecha_hoy = f"{hoy.day} de {meses[hoy.month-1]} de {hoy.year}"
    story.append(Paragraph(f"Morelia, {fecha_hoy}", normal_style))
    story.append(Spacer(1, 18))
    
    # Párrafo introductorio
    intro_text = """A quien corresponda, por medio de la presente, se hace constar que el 
    equipo que se detalla a continuación ha sido asignado a 
    la persona responsable mencionada:"""
    story.append(Paragraph(intro_text, justify_style))
    story.append(Spacer(1, 12))
    
    # Preparar imagen si existe
    imagen_path = None
    if item[7]:  # Si hay foto
        try:
            imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], item[7])
            # Redimensionar imagen para que no exceda 2.5 pulgadas de alto
            with PILImage.open(imagen_path) as pil_img:
                # Calcular nuevo tamaño manteniendo proporción
                max_height = 3 * inch
                width, height = pil_img.size
                ratio = max_height / height
                new_width = width * ratio
                
                if new_width > 5 * inch:  # Limitar ancho también
                    new_width = 5 * inch
                    ratio = new_width / width
                    max_height = height * ratio
                
                img_for_pdf = Image(imagen_path, width=new_width, height=max_height)
        except:
            imagen_path = None
    
    # Crear tabla principal
    table_data = []
    
    center_style = ParagraphStyle('Center', parent=styles['Normal'],
                             fontSize=11, alignment=TA_CENTER)
    # Primera fila - Código y Equipo
    table_data.append([
        Paragraph(f"<b>{item[1]}</b>", center_style),
        Paragraph(f"<b>Equipo:</b> {item[2].upper()}", normal_style)
    ])
    
    # Segunda fila - Usuario, Departamento e Imagen
    user_dept_text = f"""<b>Usuario:</b><br/>{item[4].upper()}<br/><br/>
    <b>Departamento:</b><br/>{item[5].upper()}<br/><br/><b>Accesorios:</b>"""
    
    if imagen_path and img_for_pdf:
        table_data.append([
            Paragraph(user_dept_text, normal_style),
            img_for_pdf
        ])
    else:
        # Sin imagen
        table_data.append([
            Paragraph(user_dept_text, normal_style),
            Paragraph("Sin imagen", normal_style)
        ])
    
    # Crear y configurar la tabla
    table = Table(table_data, colWidths=[2*inch, 4.5*inch])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (0,0), 'CENTER'), #Centrar primera celda "código"
        ('ALIGN', (1,1), (1,1), 'CENTER'),  # Centrar imagen
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 18))
    
    # Accesorios
    #story.append(Paragraph("<b>Accesorios:</b>", normal_style))
    #story.append(Paragraph("_" * 60, normal_style))
    #story.append(Spacer(1, 18))
    
    # Párrafo de responsabilidades
    responsabilidad_text = """El responsable se compromete a cuidar y mantener el equipo en buen 
    estado, así como a utilizarlo exclusivamente para fines laborales relacionados con el puesto. 
    Cualquier cambio, reasignación de usuario, daño o mal funcionamiento deberá ser reportado 
    inmediatamente al departamento de contabilidad."""
    story.append(Paragraph(responsabilidad_text, justify_style))
    story.append(Spacer(1, 6))
    
    # Validez
    validez_text = """Esta carta tiene validez a partir de la fecha de firma y se mantendrá en 
    los registros de la empresa."""
    story.append(Paragraph(validez_text, justify_style))
    story.append(Spacer(1, 6))
    
    # Despedida
    story.append(Paragraph("Atentamente, dpto. de contabilidad.", normal_style))
    story.append(Spacer(1, 12))
    
    # Firmas
    firma_style = ParagraphStyle(
        'FirmaStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',  # Fuente en negritas
        fontSize=11,
        leftIndent=0,  # Sin indentación izquierda
        spaceAfter=12,  # Espacio después de cada párrafo
    )

    # Crear los párrafos directamente
    firma_paragraphs = [
        Paragraph("<b>Nombre y Apellido (usuario):</b>", firma_style),
        Paragraph("<b>Firma:</b>", firma_style),
        Paragraph("<b>Cargo:</b>", firma_style),
        Paragraph("<b>Fecha:</b>", firma_style),
    ]

    # Agregar los párrafos a tu story
    for paragraph in firma_paragraphs:
        story.append(paragraph)
        # Opcionalmente agregar espacio extra entre elementos
        story.append(Spacer(1, 0.1*inch))


        # Generar PDF
    doc.build(story)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=False,
        download_name=f'Responsiva_{codigo}.pdf',
        mimetype='application/pdf'
    )


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
    #app.run(host='0.0.0.0', port=5000, debug=False)
    #from waitress import serve
    #port = int(os.environ.get('PORT', 10000))
    #serve(app, host='0.0.0.0', port=port)
