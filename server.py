from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PDF_FOLDER'] = 'pedidos_generados'

# Crea carpetas si no existen
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PDF_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/enviar', methods=['POST'])
@app.route('/enviar', methods=['POST'])
@app.route('/enviar', methods=['POST'])
def enviar():
    from werkzeug.utils import secure_filename
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    from PIL import Image

    # --- Datos del formulario ---
    nombre = request.form.get('nombre', 'Sin nombre')
    cantidad = request.form.get('cantidad', '0')
    papel = request.form.get('papel', 'Sin papel')
    observaciones = request.form.get('observaciones', '').strip()
    archivos = request.files.getlist('fotos')

    # --- Guardar fotos subidas ---
    fotos_guardadas = []
    for file in archivos:
        if file and file.filename:
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            fotos_guardadas.append(path)

    # --- Hoja 32x47 cm (VERTICAL) ---
    hoja_w = 32 * cm
    hoja_h = 47 * cm
    columnas = 3
    filas = 3
    espacio_w = 10 * cm
    espacio_h = 15 * cm
    fotos_por_pagina = columnas * filas

    margen_x = (hoja_w - (columnas * espacio_w)) / 2
    margen_y = (hoja_h - (filas * espacio_h)) / 2

    # --- Crear PDF ---
    pdf_name = f'pedido_{nombre.replace(" ", "_")}.pdf'
    pdf_path = os.path.join(app.config['PDF_FOLDER'], pdf_name)
    c = canvas.Canvas(pdf_path, pagesize=(hoja_w, hoja_h))
    c.setTitle(f"Pedido de {nombre}")

    # --- Encabezado ---
    c.setFont("Helvetica", 10)
    c.drawString(1 * cm, hoja_h - 1.0 * cm, f"{nombre} • {papel} • {cantidad} fotos")
    if observaciones:
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(1 * cm, hoja_h - 1.6 * cm, f"Obs: {observaciones[:90]}{'…' if len(observaciones)>90 else ''}")

    #    # --- Colocar fotos ---
    for i, foto in enumerate(fotos_guardadas):
        idx_pagina = i % fotos_por_pagina
        col = idx_pagina % columnas
        fil = idx_pagina // columnas

        x = margen_x + col * espacio_w
        y = hoja_h - margen_y - (fil + 1) * espacio_h

        # Analizar orientación y girar si hace falta
        # Analizar orientación real y rotar solo si es necesario
        try:
            with Image.open(foto) as img:
                # Intentar leer orientación desde EXIF (si existe)
                try:
                    exif = img._getexif()
                    if exif and 274 in exif:  # 274 = etiqueta de orientación
                        orient = exif[274]
                        if orient == 3:
                            img = img.rotate(180, expand=True)
                        elif orient == 6:
                            img = img.rotate(270, expand=True)
                        elif orient == 8:
                            img = img.rotate(90, expand=True)
                except Exception:
                    pass  # Si no hay metadatos EXIF, seguimos normal

                w, h = img.size
                ratio_img = w / h
                ratio_celda = espacio_w / espacio_h

                # Girar solo si conviene para aprovechar el espacio (horizontal muy marcada)
                if ratio_img > 1.2:  # más ancho que alto
                    img = img.rotate(90, expand=True)
                    w, h = img.size
                    ratio_img = w / h

                # Calcular tamaño proporcional dentro de la celda
                if ratio_img > ratio_celda:
                    nuevo_ancho = espacio_w
                    nuevo_alto = espacio_w / ratio_img
                else:
                    nuevo_alto = espacio_h
                    nuevo_ancho = espacio_h * ratio_img

                offset_x = x + (espacio_w - nuevo_ancho) / 2
                offset_y = y + (espacio_h - nuevo_alto) / 2

                temp_path = foto + "_fixed.jpg"
                img.save(temp_path)
                c.drawImage(temp_path, offset_x, offset_y,
                            width=nuevo_ancho, height=nuevo_alto,
                            preserveAspectRatio=True, anchor='sw')

        except Exception as e:
            c.rect(x, y, espacio_w, espacio_h)
            c.drawString(x + 0.3 * cm, y + espacio_h / 2, "Error img")



        # Nueva hoja si se llenó
        if idx_pagina == fotos_por_pagina - 1 and i != len(fotos_guardadas) - 1:
            c.showPage()
            c.setFont("Helvetica", 10)
            c.drawString(1 * cm, hoja_h - 1.0 * cm, f"{nombre} • {papel} • {cantidad} fotos (cont.)")
            if observaciones:
                c.setFont("Helvetica-Oblique", 9)
                c.drawString(1 * cm, hoja_h - 1.6 * cm, f"Obs: {observaciones[:90]}{'…' if len(observaciones)>90 else ''}")

    c.save()

    return f"""
    <h2>✅ Pedido recibido de {nombre}</h2>
    <p>PDF generado en: <b>{pdf_path}</b></p>
    <p>Cantidad declarada: {cantidad} | Papel: {papel}</p>
    <a href="/">⬅ Volver</a>
    """


if __name__ == '__main__':
    # Si Windows pregunta por firewall, permití acceso local.
    app.run(debug=True)