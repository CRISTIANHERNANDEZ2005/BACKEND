from io import BytesIO
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from tienda.models import Pedido, DetallePedido
import logging

logger = logging.getLogger(__name__)

def generar_pdf_pedido(pedido: Pedido):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, f"Detalle del Pedido #{pedido.id}")
    y -= 30
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Cliente: {pedido.usuario.nombre} {pedido.usuario.apellido} ({pedido.usuario.numero})")
    y -= 20
    p.drawString(50, y, f"Fecha: {pedido.fecha}")
    y -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Producto")
    p.drawString(250, y, "Cantidad")
    p.drawString(350, y, "Precio")
    p.drawString(450, y, "Subtotal")
    y -= 20
    p.setFont("Helvetica", 11)
    total = 0
    for detalle in DetallePedido.objects.filter(pedido=pedido):
        if y < 100:
            p.showPage()
            y = height - 50
        p.drawString(50, y, detalle.producto.nombre)
        p.drawString(250, y, str(detalle.cantidad))
        p.drawString(350, y, f"${detalle.precio:.2f}")
        subtotal = detalle.precio * detalle.cantidad
        p.drawString(450, y, f"${subtotal:.2f}")
        total += subtotal
        y -= 20
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(350, y, "TOTAL:")
    p.drawString(450, y, f"${total:.2f}")
    p.showPage()
    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    logger.info(f"PDF generado para pedido #{pedido.id}")
    return pdf
