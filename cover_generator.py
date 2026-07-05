from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import urllib.request, tempfile

W = 12.391 * inch
H = 9.25 * inch
SPINE = 0.135 * inch
FRONT_X = 6.135 * inch

c = canvas.Canvas('cookbook_cover.pdf', pagesize=(W, H))

# Background
c.setFillColor(colors.HexColor('#ea580c'))
c.rect(0, 0, W, H, fill=1, stroke=0)

# Food image
try:
    req = urllib.request.Request(
        'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&q=90',
        headers={'User-Agent': 'Mozilla/5.0'})
    data = urllib.request.urlopen(req, timeout=10).read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    tmp.write(data); tmp.close()
    img = ImageReader(tmp.name)
    c.drawImage(img, FRONT_X, H*0.35, W-FRONT_X, H*0.65,
                preserveAspectRatio=False, mask='auto')
except:
    pass

# Dark overlay
c.setFillColor(colors.HexColor('#1f2937'))
c.setFillAlpha(0.4)
c.rect(FRONT_X, H*0.35, W-FRONT_X, H*0.65, fill=1, stroke=0)
c.setFillAlpha(1)

# Front title
c.setFillColor(colors.white)
c.setFont('Helvetica-Bold', 32)
c.drawCentredString(FRONT_X + (W-FRONT_X)/2, H*0.82, 'The Complete')
c.drawCentredString(FRONT_X + (W-FRONT_X)/2, H*0.74, 'Home Kitchen')
c.setFont('Helvetica-Oblique', 14)
c.setFillColor(colors.HexColor('#fed7aa'))
c.drawCentredString(FRONT_X + (W-FRONT_X)/2, H*0.66, '12 Chapters of Delicious Recipes')

# Decorative lines
c.setStrokeColor(colors.HexColor('#fed7aa'))
c.setLineWidth(1.5)
c.line(FRONT_X+0.5*inch, H*0.70, W-0.5*inch, H*0.70)
c.line(FRONT_X+0.5*inch, H*0.62, W-0.5*inch, H*0.62)

# Author
c.setFont('Helvetica', 11)
c.setFillColor(colors.white)
c.drawCentredString(FRONT_X + (W-FRONT_X)/2, H*0.08, 'OpenClaw Press')

# Spine
c.setFillColor(colors.HexColor('#c2410c'))
c.rect(FRONT_X-SPINE, 0, SPINE, H, fill=1, stroke=0)
c.setFillColor(colors.white)
c.saveState()
c.translate(FRONT_X-SPINE/2, H/2)
c.rotate(90)
c.setFont('Helvetica-Bold', 9)
c.drawCentredString(0, 0, 'The Complete Home Kitchen  |  OpenClaw Press')
c.restoreState()

# Back cover
c.setFillColor(colors.HexColor('#9a3412'))
c.rect(0, 0, FRONT_X-SPINE, H, fill=1, stroke=0)
c.setFillColor(colors.white)
c.setFont('Helvetica-Bold', 18)
c.drawCentredString((FRONT_X-SPINE)/2, H*0.85, 'What You Will Find Inside:')
c.setFont('Helvetica', 12)
items = [
    '12 Delicious Recipes',
    'Step-by-Step Instructions',
    'Professional Food Photos',
    'Nutrition Facts Per Recipe',
    'Weekly Meal Planner',
    'Grocery Shopping Lists',
    'Chef Tips and Tricks',
    'Space for Your Own Recipes',
]
y = H*0.75
for item in items:
    c.drawString(0.6*inch, y, 'v  ' + item)
    y -= 0.4*inch
c.setFont('Helvetica-Oblique', 11)
c.setFillColor(colors.HexColor('#fed7aa'))
c.drawCentredString((FRONT_X-SPINE)/2, H*0.1, 'Transform your home cooking today!')

c.save()
print('Done: cookbook_cover.pdf')