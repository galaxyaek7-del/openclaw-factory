#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Factory v9 - Ultimate Book Generator
Types: journal, planner, habit, gratitude, fitness, tracker,
       healthy_eating, budget, mindfulness, cookbook
"""

import os, sys, json, re, time, traceback, urllib.request, urllib.error, tempfile
from datetime import datetime

# When spawned as a child process (e.g. by server.js) without a real console,
# Python's stdin/stdout can silently fall back to the OS locale codepage
# instead of UTF-8, corrupting Arabic text on both the way in and the way out.
# Force UTF-8 explicitly so this script behaves the same regardless of caller.
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
except ImportError:
    print(json.dumps({"success": False, "error": "pip install reportlab"}))
    sys.exit(1)

# Optional: reuse niche_validator_v2.py's competition threshold/logic for the
# Quality Gate. It depends on bs4 and calls sys.exit(1) if bs4 is missing, so
# the import is guarded — an absent optional dependency must never crash book
# generation (Constitution: fault tolerance).
try:
    import niche_validator_v2 as NICHE_VALIDATOR
except (Exception, SystemExit):
    NICHE_VALIDATOR = None

# Optional: cover_designer_v2.py's Pillow-rendered 70/20/10 cover, used
# instead of the vector-drawn safe_cover() below when available. It is a
# standalone tool (Pillow only, no reportlab) — guarding the import means a
# missing Pillow install degrades to the old cover instead of crashing.
try:
    import cover_designer_v2 as COVER_DESIGNER_V2
except Exception:
    COVER_DESIGNER_V2 = None

# Optional: inspectors.py's Dual-Inspector Quality System (CONSTITUTION.md
# §17) — the master gate every generated product must pass before it's
# considered publishable. Guarded the same way: an absent/broken inspection
# system must not crash generation, but per its own "fail closed" design it
# also must never be silently treated as approval — see its call site below.
try:
    import inspectors as INSPECTORS
except Exception:
    INSPECTORS = None

# Optional: profit_oracle.py — used here only for Smart Publishing's
# value-based repricing (see _resolve_price() below), not for scoring niches
# before they're chosen (that's Scout's/HUNT's job upstream of this file).
try:
    import profit_oracle as PROFIT_ORACLE
except Exception:
    PROFIT_ORACLE = None

PAGE_W = 6 * inch
PAGE_H = 9 * inch
MARGIN = 0.6 * inch

THEMES = {
    "blue":   colors.HexColor("#2563eb"),
    "green":  colors.HexColor("#16a34a"),
    "purple": colors.HexColor("#7c3aed"),
    "rose":   colors.HexColor("#e11d48"),
    "amber":  colors.HexColor("#d97706"),
    "teal":   colors.HexColor("#0d9488"),
    "orange": colors.HexColor("#ea580c"),
    "indigo": colors.HexColor("#4338ca"),
}
LIGHT = colors.HexColor("#9ca3af")
DARK  = colors.HexColor("#1f2937")
GRAY  = colors.HexColor("#d1d5db")
WHITE = colors.white

FOOD_IMAGES = [
    "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=1200&q=90",
    "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=1200&q=90",
    "https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=1200&q=90",
    "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=1200&q=90",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1200&q=90",
    "https://images.unsplash.com/photo-1490474418585-ba9bad8fd0ea?w=1200&q=90",
    "https://images.unsplash.com/photo-1547592180-85f173990554?w=1200&q=90",
    "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=1200&q=90",
    "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=1200&q=90",
    "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=1200&q=90",
    "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=1200&q=90",
    "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?w=1200&q=90",
]

COOKBOOK_RECIPES = [
    {
        "name": "Grilled Lemon Herb Chicken",
        "category": "Main Course",
        "time": "30 min",
        "prep": "10 min",
        "servings": "4",
        "calories": "320 cal",
        "difficulty": "Easy",
        "image_index": 0,
        "ingredients": [
            "4 chicken breasts (boneless, skinless)",
            "3 tbsp olive oil",
            "3 cloves garlic (minced)",
            "1 lemon (zested and juiced)",
            "2 tsp dried oregano",
            "1 tsp dried thyme",
            "1 tsp paprika",
            "Salt and black pepper to taste",
            "Fresh parsley for garnish",
        ],
        "steps": [
            "In a bowl, mix olive oil, garlic, lemon zest, lemon juice, oregano, thyme, and paprika.",
            "Season chicken breasts with salt and pepper on both sides.",
            "Pour marinade over chicken and let rest for at least 15 minutes.",
            "Preheat grill or grill pan to medium-high heat.",
            "Grill chicken 6-7 minutes per side until internal temp reaches 165°F.",
            "Let rest 5 minutes before slicing.",
            "Garnish with fresh parsley and lemon slices. Serve hot.",
        ],
        "tips": "For juicier chicken, marinate overnight in the refrigerator.",
        "nutrition": {"protein":"42g", "carbs":"2g", "fat":"14g", "fiber":"0g"},
    },
    {
        "name": "Mediterranean Quinoa Salad",
        "category": "Salad",
        "time": "25 min",
        "prep": "15 min",
        "servings": "4",
        "calories": "380 cal",
        "difficulty": "Easy",
        "image_index": 1,
        "ingredients": [
            "1.5 cups quinoa (uncooked)",
            "1 English cucumber (diced)",
            "2 cups cherry tomatoes (halved)",
            "1/2 red onion (finely diced)",
            "1 cup Kalamata olives",
            "200g feta cheese (crumbled)",
            "1/4 cup fresh mint leaves",
            "1/4 cup fresh parsley",
            "3 tbsp extra virgin olive oil",
            "2 tbsp red wine vinegar",
            "1 lemon (juiced)",
            "Salt and pepper to taste",
        ],
        "steps": [
            "Rinse quinoa under cold water. Cook in 3 cups of water with a pinch of salt.",
            "Bring to boil, reduce heat, cover and simmer 15 minutes until water absorbed.",
            "Fluff quinoa with a fork and spread on a tray to cool completely.",
            "In a large bowl, combine cucumber, tomatoes, red onion, and olives.",
            "Whisk together olive oil, red wine vinegar, and lemon juice for dressing.",
            "Add cooled quinoa to vegetables and pour dressing over.",
            "Toss gently, then top with feta cheese and fresh herbs. Serve chilled.",
        ],
        "tips": "This salad keeps well in the fridge for up to 3 days.",
        "nutrition": {"protein":"14g", "carbs":"48g", "fat":"18g", "fiber":"6g"},
    },
    {
        "name": "Creamy Tomato Basil Pasta",
        "category": "Pasta",
        "time": "25 min",
        "prep": "5 min",
        "servings": "4",
        "calories": "450 cal",
        "difficulty": "Easy",
        "image_index": 2,
        "ingredients": [
            "400g pasta (penne or rigatoni)",
            "2 cans (800g) crushed tomatoes",
            "1 cup heavy cream",
            "1 medium onion (finely diced)",
            "4 cloves garlic (minced)",
            "2 tbsp olive oil",
            "1 tsp sugar",
            "1 tsp dried Italian herbs",
            "Large handful fresh basil leaves",
            "Salt and black pepper",
            "Parmesan cheese for serving",
        ],
        "steps": [
            "Cook pasta in salted boiling water according to package directions. Reserve 1 cup pasta water.",
            "In a large pan, heat olive oil over medium heat.",
            "Saute onion until softened (5 min), then add garlic and cook 1 minute more.",
            "Add crushed tomatoes, sugar, Italian herbs, salt and pepper.",
            "Simmer sauce on low heat for 10 minutes, stirring occasionally.",
            "Stir in heavy cream and cook 3 more minutes until sauce thickens.",
            "Add drained pasta to sauce, toss well. Add pasta water if needed.",
            "Remove from heat, stir in fresh basil. Serve with Parmesan.",
        ],
        "tips": "Use San Marzano tomatoes for the best flavor.",
        "nutrition": {"protein":"16g", "carbs":"62g", "fat":"18g", "fiber":"5g"},
    },
    {
        "name": "Honey Garlic Salmon",
        "category": "Seafood",
        "time": "20 min",
        "prep": "5 min",
        "servings": "4",
        "calories": "390 cal",
        "difficulty": "Easy",
        "image_index": 3,
        "ingredients": [
            "4 salmon fillets (150g each)",
            "3 tbsp honey",
            "3 cloves garlic (minced)",
            "2 tbsp soy sauce",
            "1 tbsp butter",
            "1 tbsp olive oil",
            "1 tsp red pepper flakes (optional)",
            "1 lemon (sliced)",
            "Fresh dill or parsley",
            "Salt and pepper",
        ],
        "steps": [
            "Pat salmon dry with paper towels. Season with salt and pepper.",
            "Mix honey, garlic, and soy sauce in a small bowl. Set aside.",
            "Heat olive oil and butter in an oven-safe skillet over medium-high heat.",
            "Place salmon skin-side up and cook 3-4 minutes until golden.",
            "Flip salmon and pour honey garlic sauce over fillets.",
            "Cook another 3-4 minutes, basting with sauce frequently.",
            "Serve immediately with lemon slices and fresh herbs.",
        ],
        "tips": "Do not overcook salmon — it should flake easily but stay moist.",
        "nutrition": {"protein":"36g", "carbs":"14g", "fat":"18g", "fiber":"0g"},
    },
    {
        "name": "Classic Beef Stir-Fry",
        "category": "Main Course",
        "time": "20 min",
        "prep": "10 min",
        "servings": "4",
        "calories": "420 cal",
        "difficulty": "Medium",
        "image_index": 4,
        "ingredients": [
            "500g beef sirloin (thinly sliced)",
            "2 cups broccoli florets",
            "1 red bell pepper (sliced)",
            "1 yellow bell pepper (sliced)",
            "1 carrot (julienned)",
            "3 cloves garlic (minced)",
            "1 tbsp ginger (grated)",
            "3 tbsp soy sauce",
            "2 tbsp oyster sauce",
            "1 tbsp sesame oil",
            "2 tbsp vegetable oil",
            "1 tsp cornstarch",
            "Sesame seeds for garnish",
        ],
        "steps": [
            "Mix soy sauce, oyster sauce, sesame oil, and cornstarch. Marinate beef 10 min.",
            "Heat 1 tbsp oil in a wok over high heat until smoking.",
            "Stir-fry beef in batches 2-3 minutes until browned. Remove and set aside.",
            "Add remaining oil, stir-fry garlic and ginger 30 seconds.",
            "Add carrots and broccoli, stir-fry 3-4 minutes.",
            "Add bell peppers and cook 2 more minutes until crisp-tender.",
            "Return beef to wok, toss everything together and heat through.",
            "Serve immediately over steamed rice, garnished with sesame seeds.",
        ],
        "tips": "Slice beef against the grain for maximum tenderness.",
        "nutrition": {"protein":"38g", "carbs":"16g", "fat":"20g", "fiber":"4g"},
    },
    {
        "name": "Avocado Toast with Poached Eggs",
        "category": "Breakfast",
        "time": "15 min",
        "prep": "5 min",
        "servings": "2",
        "calories": "380 cal",
        "difficulty": "Medium",
        "image_index": 5,
        "ingredients": [
            "4 slices sourdough bread (thick cut)",
            "2 ripe avocados",
            "4 large eggs",
            "1 lemon (juiced)",
            "1/4 tsp red pepper flakes",
            "2 tbsp white vinegar",
            "Flaky sea salt",
            "Black pepper",
            "Fresh microgreens or arugula",
            "Everything bagel seasoning (optional)",
        ],
        "steps": [
            "Toast bread until golden and crispy on both sides.",
            "Halve and pit avocados. Scoop flesh into a bowl.",
            "Mash avocado with lemon juice, salt, and pepper until creamy.",
            "Bring a pot of water to a gentle simmer. Add white vinegar.",
            "Crack each egg into a small cup. Create a gentle whirlpool in water.",
            "Slide eggs one at a time into water. Poach 3-4 minutes for runny yolk.",
            "Spread avocado generously on toast. Top with poached egg.",
            "Season with flaky salt, pepper flakes, and microgreens.",
        ],
        "tips": "Use the freshest eggs possible for best poaching results.",
        "nutrition": {"protein":"18g", "carbs":"32g", "fat":"24g", "fiber":"8g"},
    },
    {
        "name": "Moroccan Chickpea Tagine",
        "category": "Vegetarian",
        "time": "45 min",
        "prep": "10 min",
        "servings": "6",
        "calories": "310 cal",
        "difficulty": "Medium",
        "image_index": 6,
        "ingredients": [
            "2 cans (800g) chickpeas (drained)",
            "1 can (400g) crushed tomatoes",
            "1 large onion (diced)",
            "3 cloves garlic (minced)",
            "2 carrots (diced)",
            "1 zucchini (diced)",
            "2 tsp ground cumin",
            "2 tsp ground coriander",
            "1 tsp turmeric",
            "1 tsp cinnamon",
            "1/2 tsp cayenne pepper",
            "2 tbsp olive oil",
            "Fresh cilantro",
            "Couscous or flatbread to serve",
        ],
        "steps": [
            "Heat olive oil in a large pot over medium heat.",
            "Saute onion 5 minutes until soft. Add garlic and cook 1 minute.",
            "Add all spices and stir for 30 seconds until fragrant.",
            "Add carrots and cook 3 minutes, stirring frequently.",
            "Add chickpeas, crushed tomatoes, and 1 cup water.",
            "Bring to a boil, then reduce heat and simmer 20 minutes.",
            "Add zucchini and cook 10 more minutes until tender.",
            "Adjust seasoning. Garnish with fresh cilantro. Serve with couscous.",
        ],
        "tips": "This dish tastes even better the next day as flavors deepen.",
        "nutrition": {"protein":"14g", "carbs":"42g", "fat":"8g", "fiber":"12g"},
    },
    {
        "name": "Classic French Omelette",
        "category": "Breakfast",
        "time": "10 min",
        "prep": "3 min",
        "servings": "1",
        "calories": "280 cal",
        "difficulty": "Medium",
        "image_index": 7,
        "ingredients": [
            "3 large eggs",
            "1 tbsp unsalted butter",
            "2 tbsp gruyere cheese (grated)",
            "1 tbsp fresh chives (chopped)",
            "1 tbsp fresh parsley (chopped)",
            "Salt and white pepper",
        ],
        "steps": [
            "Crack eggs into a bowl, season with salt and white pepper.",
            "Beat vigorously with a fork until yolks and whites fully combined.",
            "Heat butter in a non-stick pan over medium-high heat.",
            "When butter foams but before it browns, pour in eggs.",
            "Stir constantly with a fork while shaking pan back and forth.",
            "When eggs are just barely set, stop stirring. Add cheese and herbs.",
            "Fold omelette in thirds and slide onto a warm plate.",
            "Serve immediately with a green salad.",
        ],
        "tips": "The key is constant movement and not overcooking the eggs.",
        "nutrition": {"protein":"22g", "carbs":"1g", "fat":"22g", "fiber":"0g"},
    },
    {
        "name": "Thai Green Curry",
        "category": "Main Course",
        "time": "35 min",
        "prep": "10 min",
        "servings": "4",
        "calories": "480 cal",
        "difficulty": "Medium",
        "image_index": 8,
        "ingredients": [
            "500g chicken thighs (or tofu for vegan)",
            "400ml coconut milk (full fat)",
            "3 tbsp green curry paste",
            "2 cups mixed vegetables (zucchini, peppers, peas)",
            "2 kaffir lime leaves",
            "1 lemongrass stalk (bruised)",
            "2 tbsp fish sauce (or soy sauce)",
            "1 tbsp palm sugar (or brown sugar)",
            "Fresh Thai basil leaves",
            "Jasmine rice to serve",
            "Lime wedges",
        ],
        "steps": [
            "Heat 3 tbsp of coconut milk in a wok over medium-high heat.",
            "Add curry paste and fry 2-3 minutes until fragrant.",
            "Add chicken, stir to coat with paste. Cook 4-5 minutes.",
            "Pour in remaining coconut milk. Add lemongrass and lime leaves.",
            "Bring to a simmer, add vegetables and cook 8-10 minutes.",
            "Season with fish sauce and sugar. Taste and adjust.",
            "Remove lemongrass and lime leaves. Stir in Thai basil.",
            "Serve over jasmine rice with lime wedges.",
        ],
        "tips": "Use full-fat coconut milk for the richest, creamiest curry.",
        "nutrition": {"protein":"32g", "carbs":"18g", "fat":"30g", "fiber":"3g"},
    },
    {
        "name": "Chocolate Lava Cake",
        "category": "Dessert",
        "time": "25 min",
        "prep": "10 min",
        "servings": "4",
        "calories": "420 cal",
        "difficulty": "Medium",
        "image_index": 9,
        "ingredients": [
            "200g dark chocolate (70% cocoa)",
            "150g unsalted butter",
            "4 large eggs",
            "4 egg yolks",
            "80g caster sugar",
            "60g all-purpose flour",
            "Pinch of salt",
            "Butter and cocoa for ramekins",
            "Vanilla ice cream to serve",
            "Powdered sugar for dusting",
        ],
        "steps": [
            "Preheat oven to 200°C (400°F). Butter 4 ramekins and dust with cocoa.",
            "Melt chocolate and butter together over a bain-marie. Stir until smooth.",
            "In a bowl, whisk eggs, yolks, and sugar until pale and thick (3 min).",
            "Fold the chocolate mixture gently into the egg mixture.",
            "Sift in flour and salt. Fold until just combined — do not overmix.",
            "Divide batter evenly among prepared ramekins.",
            "Bake exactly 12 minutes until edges are set but center still jiggles.",
            "Run a knife around the edge, invert onto plates. Dust with powdered sugar.",
        ],
        "tips": "You can prepare these up to 24 hours ahead and refrigerate before baking.",
        "nutrition": {"protein":"10g", "carbs":"38g", "fat":"28g", "fiber":"3g"},
    },
    {
        "name": "Caesar Salad with Homemade Dressing",
        "category": "Salad",
        "time": "20 min",
        "prep": "15 min",
        "servings": "4",
        "calories": "320 cal",
        "difficulty": "Easy",
        "image_index": 10,
        "ingredients": [
            "2 heads romaine lettuce (torn)",
            "100g Parmesan cheese (shaved)",
            "2 cups homemade croutons",
            "2 egg yolks",
            "4 anchovy fillets (minced)",
            "3 cloves garlic (minced)",
            "2 tbsp Dijon mustard",
            "2 tbsp Worcestershire sauce",
            "3 tbsp lemon juice",
            "120ml olive oil",
            "Salt and black pepper",
        ],
        "steps": [
            "Make dressing: Whisk egg yolks, anchovies, garlic, and mustard together.",
            "Add Worcestershire sauce and lemon juice. Whisk to combine.",
            "Slowly drizzle in olive oil while whisking constantly until emulsified.",
            "Season dressing with salt and lots of black pepper.",
            "Make croutons: Cube bread, toss with olive oil, garlic, salt. Bake at 190°C for 10 min.",
            "Wash and dry romaine leaves thoroughly. Tear into bite-size pieces.",
            "Toss lettuce with dressing until every leaf is coated.",
            "Add croutons and half the Parmesan. Toss gently. Top with remaining Parmesan.",
        ],
        "tips": "For food safety, use pasteurized eggs in the dressing.",
        "nutrition": {"protein":"12g", "carbs":"18g", "fat":"24g", "fiber":"4g"},
    },
    {
        "name": "Homemade Margherita Pizza",
        "category": "Pizza",
        "time": "30 min",
        "prep": "20 min",
        "servings": "4",
        "calories": "520 cal",
        "difficulty": "Medium",
        "image_index": 11,
        "ingredients": [
            "500g pizza dough (store-bought or homemade)",
            "200ml tomato passata",
            "250g fresh mozzarella (torn)",
            "Large handful fresh basil leaves",
            "3 tbsp olive oil",
            "2 cloves garlic (minced)",
            "1 tsp dried oregano",
            "Salt and black pepper",
            "Semolina or flour for dusting",
            "Parmesan for finishing (optional)",
        ],
        "steps": [
            "Preheat oven to its highest setting (250°C+). Place pizza stone or baking tray inside.",
            "Mix passata with garlic, oregano, 1 tbsp olive oil, salt and pepper.",
            "Divide dough into 2 balls. On floured surface, stretch each to a thin round.",
            "Transfer dough to a piece of parchment paper.",
            "Spread tomato sauce leaving a 1cm border for the crust.",
            "Scatter torn mozzarella evenly over sauce.",
            "Carefully slide pizza (on parchment) onto hot stone or tray.",
            "Bake 8-10 minutes until crust is golden and cheese is bubbling.",
            "Remove from oven, top with fresh basil and drizzle of olive oil.",
        ],
        "tips": "The hotter the oven, the better the pizza — preheat for at least 30 minutes.",
        "nutrition": {"protein":"22g", "carbs":"58g", "fat":"20g", "fiber":"3g"},
    },
]

COOKBOOK_CHAPTERS = [
    ("Breakfast & Brunch", "🌅", [5, 7]),
    ("Salads & Light Meals", "🥗", [1, 10]),
    ("Pasta & Rice", "🍝", [2]),
    ("Meat & Poultry", "🍗", [0, 4]),
    ("Seafood", "🐟", [3]),
    ("Vegetarian", "🌿", [6]),
    ("International Cuisine", "🌍", [8]),
    ("Pizza & Bread", "🍕", [11]),
    ("Desserts", "🍫", [9]),
]


def get_image(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as r:
            data = r.read()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        tmp.write(data); tmp.close()
        return ImageReader(tmp.name)
    except:
        return None


def theme_color(name):
    return THEMES.get((name or "orange").lower(), THEMES["orange"])


def _page_header(c, accent, label, right_text=""):
    c.setFillColor(accent)
    c.rect(0, PAGE_H - MARGIN - 0.15*inch, PAGE_W, 0.35*inch, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN, PAGE_H - MARGIN, label)
    if right_text:
        c.setFont("Helvetica", 9)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN, right_text)
    c.setStrokeColor(GRAY)
    c.setLineWidth(0.5)
    c.line(MARGIN, 0.6*inch, PAGE_W - MARGIN, 0.6*inch)


def _wrap_text(c, text, x, y, max_width, font, size, color=None, line_height=None):
    if color: c.setFillColor(color)
    if line_height is None: line_height = size * 1.4
    c.setFont(font, size)
    words = str(text).split()
    line = ""
    lines = []
    for w in words:
        test = (line + " " + w).strip()
        if c.stringWidth(test, font, size) <= max_width:
            line = test
        else:
            if line: lines.append(line)
            line = w
    if line: lines.append(line)
    for l in lines:
        c.drawString(x, y, l)
        y -= line_height
    return y


# ══════════════════════════════════════════
#  COOKBOOK PAGES
# ══════════════════════════════════════════

def draw_cookbook_cover(c, title, subtitle, accent, author):
    # Full background
    c.setFillColor(DARK)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Top image area
    img = get_image(FOOD_IMAGES[4])
    if img:
        c.drawImage(img, 0, PAGE_H*0.4, PAGE_W, PAGE_H*0.6,
                    preserveAspectRatio=False, mask='auto')
    else:
        c.setFillColor(accent)
        c.rect(0, PAGE_H*0.4, PAGE_W, PAGE_H*0.6, fill=1, stroke=0)

    # Gradient overlay
    c.setFillColor(DARK)
    c.setFillAlpha(0.5)
    c.rect(0, PAGE_H*0.4, PAGE_W, PAGE_H*0.6, fill=1, stroke=0)
    c.setFillAlpha(1)

    # Bottom accent bar
    c.setFillColor(accent)
    c.rect(0, 0, PAGE_W, PAGE_H*0.45, fill=1, stroke=0)

    # Decorative line
    c.setStrokeColor(WHITE)
    c.setLineWidth(1)
    c.setStrokeAlpha(0.3)
    c.line(MARGIN, PAGE_H*0.45 + 0.15*inch, PAGE_W - MARGIN, PAGE_H*0.45 + 0.15*inch)
    c.setStrokeAlpha(1)

    # Title
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 28)
    words = title.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if c.stringWidth(test, "Helvetica-Bold", 28) <= PAGE_W - inch:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    y = PAGE_H*0.38
    for line in lines:
        c.drawCentredString(PAGE_W/2, y, line)
        y -= 0.44*inch

    # Subtitle
    if subtitle:
        c.setFillColor(colors.HexColor("#fef3c7"))
        c.setFont("Helvetica-Oblique", 13)
        c.drawCentredString(PAGE_W/2, PAGE_H*0.38 - len(lines)*0.44*inch - 0.15*inch, subtitle)

    # Recipe count badge
    c.setFillColor(WHITE)
    c.setFillAlpha(0.15)
    c.roundRect(PAGE_W/2 - 0.8*inch, PAGE_H*0.18, 1.6*inch, 0.45*inch, 8, fill=1, stroke=0)
    c.setFillAlpha(1)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(PAGE_W/2, PAGE_H*0.18 + 0.18*inch, f"{len(COOKBOOK_RECIPES)} Delicious Recipes")

    # Author
    if author:
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(PAGE_W/2, 1.1*inch, author)

    # Year
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#fef3c7"))
    c.drawCentredString(PAGE_W/2, 0.8*inch, str(datetime.now().year))
    c.showPage()


def page_toc(c, accent):
    _page_header(c, accent, "TABLE OF CONTENTS")
    top = PAGE_H - MARGIN - 0.6*inch
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(PAGE_W/2, top, "What's Inside")
    y = top - 0.5*inch
    for i, (chapter, icon, _) in enumerate(COOKBOOK_CHAPTERS):
        c.setFillColor(accent)
        c.setFillAlpha(0.1)
        c.roundRect(MARGIN, y - 0.22*inch, PAGE_W - 2*MARGIN, 0.36*inch, 5, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(MARGIN + 0.1*inch, y, f"{icon}  {chapter}")
        c.setFillColor(LIGHT)
        c.setFont("Helvetica", 10)
        c.drawRightString(PAGE_W - MARGIN - 0.1*inch, y, f"Page {i*10 + 5}")
        c.setStrokeColor(GRAY)
        c.setLineWidth(0.3)
        y -= 0.5*inch
    c.showPage()


def page_chapter_divider(c, accent, chapter_name, icon, chapter_num):
    # Full page chapter divider
    c.setFillColor(accent)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Subtle pattern
    c.setStrokeColor(WHITE)
    c.setStrokeAlpha(0.05)
    c.setLineWidth(0.5)
    for y in range(0, int(PAGE_H), 20):
        c.line(0, y, PAGE_W, y)
    c.setStrokeAlpha(1)

    # Chapter number
    c.setFillColor(WHITE)
    c.setFillAlpha(0.1)
    c.setFont("Helvetica-Bold", 120)
    c.drawCentredString(PAGE_W/2, PAGE_H/2, str(chapter_num))
    c.setFillAlpha(1)

    # Icon
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 48)
    c.drawCentredString(PAGE_W/2, PAGE_H/2 + 0.8*inch, icon)

    # Chapter title
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(PAGE_W/2, PAGE_H/2 - 0.3*inch, chapter_name)

    # Decorative lines
    c.setStrokeColor(WHITE)
    c.setStrokeAlpha(0.4)
    c.setLineWidth(1)
    c.line(MARGIN + 0.5*inch, PAGE_H/2 - 0.7*inch, PAGE_W - MARGIN - 0.5*inch, PAGE_H/2 - 0.7*inch)
    c.setStrokeAlpha(1)

    c.showPage()


def page_recipe_full(c, accent, recipe, page_num):
    _page_header(c, accent, recipe["category"].upper(), recipe["difficulty"])
    top = PAGE_H - MARGIN - 0.6*inch

    # Recipe title
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 16)
    y = _wrap_text(c, recipe["name"], MARGIN, top, PAGE_W - 2*MARGIN, "Helvetica-Bold", 16, DARK, 0.28*inch)
    y -= 0.15*inch

    # Meta badges
    meta = [
        ("⏱", "Prep", recipe["prep"]),
        ("🍳", "Cook", recipe["time"]),
        ("👥", "Serves", recipe["servings"]),
        ("🔥", "Cal", recipe["calories"]),
    ]
    badge_w = (PAGE_W - 2*MARGIN) / len(meta)
    for i, (icon, label, val) in enumerate(meta):
        bx = MARGIN + i * badge_w
        c.setFillColor(accent)
        c.setFillAlpha(0.12)
        c.roundRect(bx + 2, y - 0.38*inch, badge_w - 4, 0.42*inch, 6, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(bx + badge_w/2, y - 0.1*inch, label)
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(bx + badge_w/2, y - 0.26*inch, val)
    y -= 0.55*inch

    # Image
    img = get_image(FOOD_IMAGES[recipe.get("image_index", 0) % len(FOOD_IMAGES)])
    img_h = 1.8*inch
    if img:
        c.drawImage(img, MARGIN, y - img_h, PAGE_W - 2*MARGIN, img_h,
                    preserveAspectRatio=True, mask='auto')
    else:
        c.setFillColor(colors.HexColor("#f3f4f6"))
        c.roundRect(MARGIN, y - img_h, PAGE_W - 2*MARGIN, img_h, 8, fill=1, stroke=0)
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(PAGE_W/2, y - img_h/2, "🍽️")
    y -= img_h + 0.15*inch

    # Two columns: ingredients | steps
    col_w = (PAGE_W - 2*MARGIN - 0.2*inch) / 2
    left_x = MARGIN
    right_x = MARGIN + col_w + 0.2*inch

    # INGREDIENTS
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left_x, y, "INGREDIENTS")
    c.setStrokeColor(accent)
    c.setLineWidth(1)
    c.line(left_x, y - 3, left_x + col_w, y - 3)
    iy = y - 0.22*inch
    for ing in recipe["ingredients"]:
        c.setFillColor(accent)
        c.circle(left_x + 0.06*inch, iy - 0.04*inch, 0.04*inch, fill=1)
        c.setFillColor(DARK)
        c.setFont("Helvetica", 7.5)
        words = ing.split()
        line = ""
        first = True
        for w in words:
            test = (line + " " + w).strip()
            if c.stringWidth(test, "Helvetica", 7.5) <= col_w - 0.18*inch:
                line = test
            else:
                xoff = left_x + 0.14*inch
                c.drawString(xoff, iy - 0.04*inch if first else iy, line)
                iy -= 0.18*inch
                line = w; first = False
        if line:
            c.drawString(left_x + 0.14*inch, iy - 0.04*inch if first else iy, line)
            iy -= 0.22*inch

    # INSTRUCTIONS
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(right_x, y, "INSTRUCTIONS")
    c.setStrokeColor(accent)
    c.line(right_x, y - 3, right_x + col_w, y - 3)
    sy = y - 0.22*inch
    for i, step in enumerate(recipe["steps"], 1):
        # Step number circle
        c.setFillColor(accent)
        c.circle(right_x + 0.1*inch, sy - 0.04*inch, 0.1*inch, fill=1)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 6)
        c.drawCentredString(right_x + 0.1*inch, sy - 0.07*inch, str(i))
        # Step text
        c.setFillColor(DARK)
        c.setFont("Helvetica", 7)
        words = step.split()
        line = ""; tx = right_x + 0.24*inch
        for w in words:
            test = (line + " " + w).strip()
            if c.stringWidth(test, "Helvetica", 7) <= col_w - 0.28*inch:
                line = test
            else:
                c.drawString(tx, sy - 0.04*inch, line)
                sy -= 0.17*inch
                line = w; tx = right_x + 0.24*inch
        if line:
            c.drawString(tx, sy - 0.04*inch, line)
            sy -= 0.22*inch
        if sy < iy: iy = sy

    # Chef's tip
    final_y = min(iy, sy) - 0.1*inch
    if final_y > 0.7*inch:
        c.setFillColor(colors.HexColor("#fef3c7"))
        c.roundRect(MARGIN, final_y - 0.35*inch, PAGE_W - 2*MARGIN, 0.38*inch, 6, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#92400e"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(MARGIN + 0.1*inch, final_y - 0.1*inch, f"👨‍🍳 Chef's Tip: {recipe['tips'][:80]}")

    # Page number
    c.setFillColor(LIGHT)
    c.setFont("Helvetica", 8)
    c.drawCentredString(PAGE_W/2, 0.3*inch, str(page_num))
    c.showPage()


def page_nutrition_facts(c, accent, recipe, page_num):
    _page_header(c, accent, f"NUTRITION: {recipe['name'].upper()[:30]}")
    top = PAGE_H - MARGIN - 0.6*inch

    # Nutrition box
    c.setFillColor(DARK)
    c.roundRect(MARGIN, top - 2.5*inch, PAGE_W - 2*MARGIN, 2.5*inch, 10, fill=1, stroke=0)
    c.setFillColor(accent)
    c.roundRect(MARGIN, top - 0.45*inch, PAGE_W - 2*MARGIN, 0.45*inch, 10, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(PAGE_W/2, top - 0.28*inch, "Nutrition Facts")

    nw = (PAGE_W - 2*MARGIN) / 4
    nutrients = [
        ("🔥", "Calories", recipe["calories"], accent),
        ("💪", "Protein", recipe["nutrition"]["protein"], colors.HexColor("#3b82f6")),
        ("🌾", "Carbs", recipe["nutrition"]["carbs"], colors.HexColor("#f59e0b")),
        ("🥑", "Fat", recipe["nutrition"]["fat"], colors.HexColor("#ef4444")),
    ]
    for i, (icon, label, val, col) in enumerate(nutrients):
        nx = MARGIN + i * nw + nw/2
        c.setFillColor(col)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(nx, top - 1.1*inch, icon)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(nx, top - 1.55*inch, val)
        c.setFont("Helvetica", 9)
        c.drawCentredString(nx, top - 1.82*inch, label)

    # Fiber
    c.setFillColor(LIGHT)
    c.setFont("Helvetica", 9)
    c.drawCentredString(PAGE_W/2, top - 2.15*inch, f"Fiber: {recipe['nutrition']['fiber']}  •  Per serving")

    # My Notes section
    y = top - 2.8*inch
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN, y, "MY COOKING NOTES")
    c.setStrokeColor(accent)
    c.setLineWidth(1)
    c.line(MARGIN, y-3, PAGE_W - MARGIN, y-3)
    y -= 0.3*inch
    c.setStrokeColor(GRAY)
    c.setLineWidth(0.5)
    for _ in range(8):
        c.line(MARGIN, y, PAGE_W - MARGIN, y)
        y -= 0.38*inch

    # Rating
    y -= 0.1*inch
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN, y, "MY RATING:")
    c.setFont("Helvetica", 16)
    c.drawString(MARGIN + 1.2*inch, y - 2, "☆ ☆ ☆ ☆ ☆")

    y -= 0.4*inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN, y, "WOULD I MAKE AGAIN?")
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN + 0.3*inch, y - 0.28*inch, "□  Yes, definitely!")
    c.drawString(MARGIN + 1.8*inch, y - 0.28*inch, "□  With modifications")
    c.drawString(MARGIN + 3.5*inch, y - 0.28*inch, "□  Not really")

    c.setFillColor(LIGHT)
    c.setFont("Helvetica", 8)
    c.drawCentredString(PAGE_W/2, 0.3*inch, str(page_num))
    c.showPage()


def page_cooking_tips(c, accent):
    _page_header(c, accent, "ESSENTIAL COOKING TIPS & TECHNIQUES")
    top = PAGE_H - MARGIN - 0.6*inch

    tips = [
        ("🔪", "Knife Skills", "Keep your knives sharp — a sharp knife is safer and more precise than a dull one. Use a honing steel before each use."),
        ("🌡️", "Temperature Control", "Invest in a meat thermometer. Chicken: 165°F, Beef medium: 145°F, Pork: 145°F. Never guess doneness."),
        ("🧂", "Seasoning", "Season in layers throughout cooking, not just at the end. Taste as you go. Salt enhances flavor — use it generously."),
        ("🫙", "Mise en Place", "Prepare and measure all ingredients before you start cooking. This French technique prevents mistakes and reduces stress."),
        ("🔥", "High Heat Searing", "Pat meat completely dry before searing. Moisture is the enemy of a golden crust. Hot pan + dry surface = perfect sear."),
        ("🍋", "Acid Balance", "A squeeze of lemon or splash of vinegar brightens any dish. When something tastes flat, acid is often the answer."),
        ("🧈", "Fat = Flavor", "Don't fear fat. Butter, olive oil, and rendered fats carry flavor compounds that make food taste richer and more complex."),
        ("⏰", "Resting Meat", "Always rest cooked meat 5-10 minutes before cutting. This allows juices to redistribute for a juicier result."),
    ]

    y = top
    for i, (icon, title, desc) in enumerate(tips):
        col = 0 if i % 2 == 0 else 1
        x = MARGIN if col == 0 else MARGIN + (PAGE_W - 2*MARGIN)/2 + 0.1*inch
        box_w = (PAGE_W - 2*MARGIN)/2 - 0.1*inch

        c.setFillColor(accent)
        c.setFillAlpha(0.08)
        c.roundRect(x, y - 0.75*inch, box_w, 0.78*inch, 6, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x + 0.1*inch, y - 0.18*inch, icon)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 0.4*inch, y - 0.18*inch, title)
        c.setFillColor(DARK)
        c.setFont("Helvetica", 7.5)
        words = desc.split()
        line = ""; dy = y - 0.36*inch
        for w in words:
            test = (line + " " + w).strip()
            if c.stringWidth(test, "Helvetica", 7.5) <= box_w - 0.2*inch:
                line = test
            else:
                c.drawString(x + 0.1*inch, dy, line)
                dy -= 0.17*inch; line = w
        if line: c.drawString(x + 0.1*inch, dy, line)

        if col == 1: y -= 0.95*inch
    c.showPage()


def page_measurement_guide(c, accent):
    _page_header(c, accent, "KITCHEN MEASUREMENT GUIDE")
    top = PAGE_H - MARGIN - 0.6*inch

    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(PAGE_W/2, top, "Quick Reference Conversions")

    # Volume conversions
    y = top - 0.4*inch
    sections = [
        ("VOLUME", [
            ("1 tablespoon (tbsp)", "= 3 teaspoons = 15ml"),
            ("1/4 cup", "= 4 tablespoons = 60ml"),
            ("1/3 cup", "= 5 tbsp + 1 tsp = 80ml"),
            ("1/2 cup", "= 8 tablespoons = 120ml"),
            ("1 cup", "= 16 tablespoons = 240ml"),
            ("1 pint", "= 2 cups = 480ml"),
            ("1 quart", "= 4 cups = 960ml"),
            ("1 gallon", "= 16 cups = 3.8 liters"),
        ]),
        ("WEIGHT", [
            ("1 ounce (oz)", "= 28 grams"),
            ("4 ounces", "= 113 grams = 1/4 lb"),
            ("8 ounces", "= 227 grams = 1/2 lb"),
            ("1 pound (lb)", "= 454 grams"),
            ("2.2 pounds", "= 1 kilogram"),
        ]),
        ("TEMPERATURE", [
            ("250°F", "= 120°C — Low oven"),
            ("350°F", "= 175°C — Moderate oven"),
            ("400°F", "= 200°C — Hot oven"),
            ("450°F", "= 230°C — Very hot oven"),
            ("165°F", "= 74°C — Chicken done"),
            ("145°F", "= 63°C — Beef/Pork done"),
        ]),
    ]

    for section_title, items in sections:
        c.setFillColor(accent)
        c.rect(MARGIN, y - 0.22*inch, PAGE_W - 2*MARGIN, 0.24*inch, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN + 0.1*inch, y - 0.08*inch, section_title)
        y -= 0.28*inch

        for i, (left, right) in enumerate(items):
            bg = colors.HexColor("#f9fafb") if i % 2 == 0 else WHITE
            c.setFillColor(accent)
            c.setFillAlpha(0.05 if i % 2 == 0 else 0)
            c.rect(MARGIN, y - 0.22*inch, PAGE_W - 2*MARGIN, 0.24*inch, fill=1, stroke=0)
            c.setFillAlpha(1)
            c.setFillColor(DARK)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(MARGIN + 0.1*inch, y - 0.08*inch, left)
            c.setFont("Helvetica", 9)
            c.drawRightString(PAGE_W - MARGIN - 0.1*inch, y - 0.08*inch, right)
            y -= 0.26*inch
        y -= 0.1*inch
    c.showPage()


def page_meal_planner(c, accent):
    _page_header(c, accent, "WEEKLY MEAL PLANNER")
    top = PAGE_H - MARGIN - 0.55*inch

    c.setFillColor(DARK)
    c.setFont("Helvetica", 9)
    c.drawString(MARGIN, top, "Week of: _____________________")
    c.drawRightString(PAGE_W - MARGIN, top, "Shopping Done: □")

    days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    cols = ["BREAKFAST","LUNCH","DINNER"]
    col_w = (PAGE_W - 2*MARGIN) / (len(cols) + 1)
    row_h = 0.78*inch
    y = top - 0.35*inch

    # Header
    c.setFillColor(accent)
    c.rect(MARGIN, y - 0.25*inch, PAGE_W - 2*MARGIN, 0.28*inch, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MARGIN + 0.1*inch, y - 0.1*inch, "DAY")
    for i, col in enumerate(cols):
        c.drawString(MARGIN + col_w*(i+1) + 0.1*inch, y - 0.1*inch, col)
    y -= 0.25*inch

    for di, day in enumerate(days):
        bg = colors.HexColor("#f9fafb") if di % 2 == 0 else WHITE
        c.setFillColor(accent)
        c.setFillAlpha(0.06 if di % 2 == 0 else 0)
        c.rect(MARGIN, y - row_h, PAGE_W - 2*MARGIN, row_h, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setStrokeColor(GRAY)
        c.setLineWidth(0.3)
        c.rect(MARGIN, y - row_h, PAGE_W - 2*MARGIN, row_h, fill=0)
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(MARGIN + 0.08*inch, y - 0.18*inch, day[:3].upper())
        # Vertical lines
        for ci in range(len(cols)):
            c.setStrokeColor(GRAY)
            c.line(MARGIN + col_w*(ci+1), y, MARGIN + col_w*(ci+1), y - row_h)
        y -= row_h
    c.showPage()


def page_shopping_list(c, accent):
    _page_header(c, accent, "GROCERY SHOPPING LIST")
    top = PAGE_H - MARGIN - 0.55*inch

    categories = {
        "🥩 MEAT & SEAFOOD": ["Chicken breasts","Salmon fillets","Ground beef","Beef sirloin","Eggs"],
        "🥦 VEGETABLES": ["Broccoli","Cherry tomatoes","Spinach","Bell peppers","Zucchini","Carrots","Onions","Garlic"],
        "🍎 FRUITS": ["Lemons","Avocados","Limes","Fresh berries","Bananas"],
        "🌾 PANTRY": ["Olive oil","Quinoa","Brown rice","Pasta","Canned tomatoes","Chickpeas"],
        "🧀 DAIRY": ["Butter","Parmesan","Feta cheese","Greek yogurt","Heavy cream","Mozzarella"],
        "🌿 HERBS & SPICES": ["Fresh basil","Fresh parsley","Thyme","Oregano","Cumin","Paprika"],
    }

    col_w = (PAGE_W - 2*MARGIN) / 2 - 0.1*inch
    y = top
    col = 0
    for cat, items in categories.items():
        x = MARGIN if col == 0 else MARGIN + col_w + 0.2*inch
        c.setFillColor(accent)
        c.rect(x, y - 0.22*inch, col_w, 0.24*inch, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x + 0.08*inch, y - 0.08*inch, cat)
        cy = y - 0.28*inch
        for item in items:
            c.setStrokeColor(accent)
            c.setLineWidth(0.5)
            c.roundRect(x + 0.05*inch, cy - 0.14*inch, 0.14*inch, 0.14*inch, 2, fill=0)
            c.setFillColor(DARK)
            c.setFont("Helvetica", 8)
            c.drawString(x + 0.26*inch, cy - 0.1*inch, item)
            cy -= 0.3*inch
        col = 1 - col
        if col == 0: y = cy - 0.1*inch
    c.showPage()


def page_my_recipes(c, accent):
    _page_header(c, accent, "MY OWN RECIPES")
    top = PAGE_H - MARGIN - 0.55*inch

    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(PAGE_W/2, top, "Add Your Own Favorite Recipe Here")

    y = top - 0.4*inch
    fields = [
        ("Recipe Name", 0.3*inch),
        ("Category", 0.3*inch),
        ("Prep Time", 0.3*inch),
        ("Cook Time", 0.3*inch),
        ("Servings", 0.3*inch),
    ]
    for label, h in fields:
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGIN, y, label + ":")
        c.setStrokeColor(GRAY)
        c.setLineWidth(0.5)
        c.line(MARGIN + 1.2*inch, y, PAGE_W - MARGIN, y)
        y -= 0.38*inch

    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, y, "INGREDIENTS:")
    y -= 0.25*inch
    for _ in range(8):
        c.setStrokeColor(GRAY)
        c.line(MARGIN, y, MARGIN + 2.2*inch, y)
        y -= 0.3*inch

    y_right = top - 0.4*inch - 5 * 0.38*inch - 0.25*inch
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN + 2.5*inch, y_right, "INSTRUCTIONS:")
    y_right -= 0.25*inch
    for _ in range(10):
        c.setStrokeColor(GRAY)
        c.line(MARGIN + 2.5*inch, y_right, PAGE_W - MARGIN, y_right)
        y_right -= 0.38*inch

    c.showPage()


def create_cookbook(out_path, title, subtitle, theme, pages, author):
    accent = theme_color(theme)
    c = canvas.Canvas(out_path, pagesize=(PAGE_W, PAGE_H))
    page_count = 0

    # 1. Cover
    draw_cookbook_cover(c, title, subtitle, accent, author)
    page_count += 1

    # 2. Table of Contents
    page_toc(c, accent)
    page_count += 1

    # 3. Measurement Guide
    page_measurement_guide(c, accent)
    page_count += 1

    # 4. Cooking Tips
    page_cooking_tips(c, accent)
    page_count += 1

    # 5. Recipes by chapter
    recipe_page = 5
    for chap_i, (chapter, icon, recipe_indices) in enumerate(COOKBOOK_CHAPTERS):
        if page_count >= pages: break

        # Chapter divider
        page_chapter_divider(c, accent, chapter, icon, chap_i + 1)
        page_count += 1

        for ri in recipe_indices:
            if page_count >= pages: break
            recipe = COOKBOOK_RECIPES[ri]

            # Recipe page
            page_recipe_full(c, accent, recipe, recipe_page)
            recipe_page += 1; page_count += 1

            # Nutrition + notes page
            if page_count < pages:
                page_nutrition_facts(c, accent, recipe, recipe_page)
                recipe_page += 1; page_count += 1

    # 6. Weekly meal planner pages
    while page_count < pages - 4:
        page_meal_planner(c, accent)
        page_count += 1

    # 7. Shopping list
    if page_count < pages:
        page_shopping_list(c, accent)
        page_count += 1

    # 8. My Own Recipes (blank pages)
    while page_count < pages:
        page_my_recipes(c, accent)
        page_count += 1

    c.save()
    return page_count


# ══════════════════════════════════════════
#  OTHER BOOK TYPES (simplified)
# ══════════════════════════════════════════

def _ruled(c, top, n, gap=0.38*inch):
    c.setStrokeColor(GRAY)
    c.setLineWidth(0.5)
    y = top
    for _ in range(n):
        c.line(MARGIN, y, PAGE_W - MARGIN, y)
        y -= gap


def page_journal(c, accent):
    _page_header(c, accent, "JOURNAL ENTRY", "Date: ___/___/______")
    top = PAGE_H - MARGIN - 0.6*inch
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, top, "TODAY'S THOUGHTS")
    _ruled(c, top - 0.25*inch, 7)
    c.drawString(MARGIN, top - 3.2*inch, "WHAT I LEARNED")
    _ruled(c, top - 3.45*inch, 4)
    c.drawString(MARGIN, top - 5.3*inch, "TOMORROW'S INTENTION")
    _ruled(c, top - 5.55*inch, 3)


def page_habit(c, accent):
    _page_header(c, accent, "HABIT TRACKER", "Month: _______________")
    top = PAGE_H - MARGIN - 0.6*inch
    habits = ["Wake up early", "Exercise", "Read 30 min", "Drink water", "Meditate",
              "No junk food", "Journal", "Sleep by 11pm"]
    days = list(range(1, 32))
    col_w = (PAGE_W - 2*MARGIN - 1.2*inch) / 31
    # Header row — day numbers
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 6)
    for di, d in enumerate(days):
        c.drawCentredString(MARGIN + 1.2*inch + di*col_w + col_w/2, top, str(d))
    c.setStrokeColor(GRAY); c.setLineWidth(0.3)
    c.line(MARGIN, top - 0.08*inch, PAGE_W - MARGIN, top - 0.08*inch)
    # Habit rows
    row_h = 0.33*inch
    y = top - 0.22*inch
    for hi, habit in enumerate(habits):
        bg_alpha = 0.05 if hi % 2 == 0 else 0
        c.setFillColor(accent); c.setFillAlpha(bg_alpha)
        c.rect(MARGIN, y - row_h + 0.08*inch, PAGE_W - 2*MARGIN, row_h, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setFillColor(DARK); c.setFont("Helvetica-Bold", 8)
        c.drawString(MARGIN + 0.05*inch, y - 0.1*inch, habit)
        for di in range(31):
            bx = MARGIN + 1.2*inch + di*col_w + col_w*0.1
            c.setStrokeColor(accent); c.setLineWidth(0.5)
            c.roundRect(bx, y - 0.22*inch, col_w*0.8, 0.18*inch, 2, fill=0)
        c.setStrokeColor(GRAY); c.setLineWidth(0.2)
        c.line(MARGIN, y - row_h + 0.08*inch, PAGE_W - MARGIN, y - row_h + 0.08*inch)
        y -= row_h
    # Notes
    y -= 0.15*inch
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, y, "NOTES")
    _ruled(c, y - 0.2*inch, 3, 0.3*inch)


def page_gratitude(c, accent):
    _page_header(c, accent, "GRATITUDE JOURNAL", "Date: ___/___/______")
    top = PAGE_H - MARGIN - 0.6*inch
    sections = [
        ("🙏", "3 THINGS I'M GRATEFUL FOR TODAY", 3, 0.32*inch),
        ("✨", "TODAY'S POSITIVE AFFIRMATION", 1, 0.32*inch),
        ("💡", "ONE THING THAT MADE ME SMILE", 1, 0.32*inch),
        ("🌱", "HOW I WILL MAKE TODAY GREAT", 2, 0.32*inch),
        ("🌙", "EVENING REFLECTION", 3, 0.32*inch),
    ]
    y = top
    for icon, title, lines, gap in sections:
        c.setFillColor(accent); c.setFillAlpha(0.08)
        box_h = 0.3*inch + lines * gap + 0.1*inch
        c.roundRect(MARGIN, y - box_h, PAGE_W - 2*MARGIN, box_h, 6, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGIN + 0.1*inch, y - 0.18*inch, f"{icon}  {title}")
        for li in range(lines):
            ly = y - 0.36*inch - li * gap
            if li == 0:
                c.setFillColor(accent); c.setFont("Helvetica-Bold", 8)
                if lines > 1:
                    c.drawString(MARGIN + 0.1*inch, ly - 0.04*inch, f"{li+1}.")
            c.setStrokeColor(GRAY); c.setLineWidth(0.4)
            c.line(MARGIN + 0.35*inch, ly, PAGE_W - MARGIN - 0.1*inch, ly)
        y -= box_h + 0.1*inch


def page_fitness(c, accent):
    _page_header(c, accent, "FITNESS LOG", "Date: ___/___/______")
    top = PAGE_H - MARGIN - 0.6*inch
    # Meta row
    meta = [("💪", "WORKOUT TYPE", 1.5*inch), ("⏱", "DURATION", 0.8*inch),
            ("🔥", "CALORIES", 0.8*inch), ("❤️", "AVG HR", 0.7*inch)]
    c.setFillColor(accent); c.setFillAlpha(0.1)
    c.roundRect(MARGIN, top - 0.45*inch, PAGE_W - 2*MARGIN, 0.48*inch, 6, fill=1, stroke=0)
    c.setFillAlpha(1)
    mx = MARGIN + 0.1*inch
    for icon, label, w in meta:
        c.setFillColor(accent); c.setFont("Helvetica-Bold", 7)
        c.drawString(mx, top - 0.14*inch, f"{icon} {label}")
        c.setStrokeColor(GRAY); c.setLineWidth(0.5)
        c.line(mx, top - 0.36*inch, mx + w - 0.1*inch, top - 0.36*inch)
        mx += w
    # Exercise table
    y = top - 0.65*inch
    c.setFillColor(accent)
    c.rect(MARGIN, y - 0.22*inch, PAGE_W - 2*MARGIN, 0.24*inch, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 8)
    cols = [("EXERCISE", 1.6*inch), ("SETS", 0.5*inch), ("REPS", 0.5*inch),
            ("WEIGHT", 0.65*inch), ("REST", 0.55*inch), ("NOTES", 1.5*inch)]
    cx = MARGIN + 0.05*inch
    for label, cw in cols:
        c.drawString(cx, y - 0.08*inch, label)
        cx += cw
    y -= 0.22*inch
    for ri in range(10):
        bg = 0.04 if ri % 2 == 0 else 0
        c.setFillColor(accent); c.setFillAlpha(bg)
        c.rect(MARGIN, y - 0.28*inch, PAGE_W - 2*MARGIN, 0.28*inch, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setStrokeColor(GRAY); c.setLineWidth(0.2)
        c.line(MARGIN, y - 0.28*inch, PAGE_W - MARGIN, y - 0.28*inch)
        cx = MARGIN + 0.05*inch
        for _, cw in cols:
            c.line(cx + cw - 0.05*inch, y - 0.04*inch, cx + cw - 0.05*inch, y - 0.24*inch)
            cx += cw
        y -= 0.28*inch
    # Cool-down notes
    y -= 0.1*inch
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, y, "💧 HYDRATION & NOTES")
    _ruled(c, y - 0.2*inch, 3, 0.28*inch)


def page_tracker(c, accent):
    _page_header(c, accent, "MONTHLY TRACKER", "Month / Year: _______________")
    top = PAGE_H - MARGIN - 0.6*inch
    # Mini calendar grid (7 cols × 6 rows)
    days_labels = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    cell_w = (PAGE_W - 2*MARGIN) / 7
    cell_h = 0.55*inch
    # Day headers
    c.setFillColor(accent)
    c.rect(MARGIN, top - 0.26*inch, PAGE_W - 2*MARGIN, 0.28*inch, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 8)
    for di, dl in enumerate(days_labels):
        c.drawCentredString(MARGIN + di*cell_w + cell_w/2, top - 0.1*inch, dl)
    # Calendar cells
    cy = top - 0.26*inch
    for row in range(6):
        cy -= cell_h
        for col in range(7):
            cx = MARGIN + col * cell_w
            c.setStrokeColor(GRAY); c.setLineWidth(0.3)
            c.rect(cx, cy, cell_w, cell_h, fill=0)
            # Day number placeholder
            c.setFillColor(LIGHT); c.setFont("Helvetica", 7)
            c.drawString(cx + 0.06*inch, cy + cell_h - 0.14*inch, "___")
            # Small notes lines
            for li in range(2):
                c.setStrokeColor(GRAY); c.setLineWidth(0.2)
                c.line(cx + 0.05*inch, cy + 0.22*inch - li*0.14*inch,
                       cx + cell_w - 0.05*inch, cy + 0.22*inch - li*0.14*inch)
    # Goals section
    gy = cy - 0.2*inch
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, gy, "🎯  MONTHLY GOALS")
    _ruled(c, gy - 0.2*inch, 3, 0.28*inch)


def page_budget(c, accent):
    _page_header(c, accent, "BUDGET TRACKER", "Month: _______________")
    top = PAGE_H - MARGIN - 0.6*inch
    # Summary row
    c.setFillColor(accent); c.setFillAlpha(0.1)
    c.roundRect(MARGIN, top - 0.42*inch, PAGE_W - 2*MARGIN, 0.45*inch, 6, fill=1, stroke=0)
    c.setFillAlpha(1)
    summ = [("💵", "INCOME", colors.HexColor("#16a34a")),
            ("💸", "EXPENSES", colors.HexColor("#dc2626")),
            ("💰", "SAVINGS", accent)]
    sw = (PAGE_W - 2*MARGIN) / 3
    for si, (icon, label, col) in enumerate(summ):
        sx = MARGIN + si*sw + sw/2
        c.setFillColor(col); c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(sx, top - 0.14*inch, f"{icon} {label}")
        c.setFillColor(DARK); c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(sx, top - 0.32*inch, "$___________")
    # Two-column table: income | expenses
    y = top - 0.62*inch
    for side, label, col in [
        (0, "INCOME SOURCES", colors.HexColor("#16a34a")),
        (1, "EXPENSES",       colors.HexColor("#dc2626"))
    ]:
        tx = MARGIN if side == 0 else MARGIN + (PAGE_W - 2*MARGIN)/2 + 0.1*inch
        tw = (PAGE_W - 2*MARGIN)/2 - 0.1*inch
        c.setFillColor(col)
        c.rect(tx, y - 0.22*inch, tw, 0.24*inch, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 8)
        c.drawString(tx + 0.08*inch, y - 0.08*inch, label)
        c.setFont("Helvetica-Bold", 7); c.setFillColor(WHITE)
        c.drawRightString(tx + tw - 0.05*inch, y - 0.08*inch, "AMOUNT")
        ry = y - 0.22*inch
        for ri in range(9):
            bg = 0.04 if ri % 2 == 0 else 0
            c.setFillColor(col); c.setFillAlpha(bg)
            c.rect(tx, ry - 0.28*inch, tw, 0.28*inch, fill=1, stroke=0)
            c.setFillAlpha(1)
            c.setStrokeColor(GRAY); c.setLineWidth(0.25)
            c.line(tx, ry - 0.28*inch, tx + tw, ry - 0.28*inch)
            c.line(tx + tw - 0.75*inch, ry - 0.04*inch, tx + tw - 0.05*inch, ry - 0.04*inch)
            c.line(tx + 0.05*inch, ry - 0.18*inch, tx + tw - 0.8*inch, ry - 0.18*inch)
            ry -= 0.28*inch
        # Total row
        c.setFillColor(col); c.setFillAlpha(0.15)
        c.rect(tx, ry - 0.28*inch, tw, 0.28*inch, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setFillColor(col); c.setFont("Helvetica-Bold", 8)
        c.drawString(tx + 0.08*inch, ry - 0.1*inch, "TOTAL")
        c.drawRightString(tx + tw - 0.05*inch, ry - 0.1*inch, "$___________")


def page_mindfulness(c, accent):
    _page_header(c, accent, "MINDFULNESS JOURNAL", "Date: ___/___/______")
    top = PAGE_H - MARGIN - 0.6*inch
    # Breathing exercise
    c.setFillColor(accent); c.setFillAlpha(0.08)
    c.roundRect(MARGIN, top - 0.62*inch, PAGE_W - 2*MARGIN, 0.65*inch, 8, fill=1, stroke=0)
    c.setFillAlpha(1)
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN + 0.15*inch, top - 0.16*inch, "🌬️  4-7-8 BREATHING PRACTICE")
    steps = [("Inhale", "4s", 0), ("Hold", "7s", 1.4*inch), ("Exhale", "8s", 2.8*inch)]
    for label, dur, ox in steps:
        bx = MARGIN + 0.15*inch + ox
        c.setFillColor(accent); c.setFillAlpha(0.2)
        c.roundRect(bx, top - 0.54*inch, 1.2*inch, 0.3*inch, 15, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(bx + 0.6*inch, top - 0.38*inch, f"{label} {dur}")
    c.setFillColor(LIGHT); c.setFont("Helvetica", 7)
    c.drawRightString(PAGE_W - MARGIN - 0.1*inch, top - 0.38*inch, "Rounds completed: ___ / 4")
    # Body scan checklist
    y = top - 0.78*inch
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, y, "🧘  BODY SCAN CHECK-IN")
    areas = ["Head & neck", "Shoulders", "Chest", "Abdomen", "Arms & hands", "Legs & feet"]
    for ai, area in enumerate(areas):
        ax = MARGIN + (ai % 3) * 1.7*inch
        ay = y - 0.28*inch - (ai // 3) * 0.3*inch
        c.setStrokeColor(accent); c.setLineWidth(0.5)
        c.roundRect(ax, ay - 0.14*inch, 0.14*inch, 0.14*inch, 2, fill=0)
        c.setFillColor(DARK); c.setFont("Helvetica", 8)
        c.drawString(ax + 0.2*inch, ay - 0.08*inch, area)
    y -= 0.9*inch
    # Mood + intention
    sections = [
        ("😌", "MY MOOD RIGHT NOW (circle)", "😞  😐  🙂  😄  🤩", False),
        ("🎯", "TODAY'S INTENTION", None, True),
        ("💭", "WHAT'S ON MY MIND?", None, True),
        ("🌟", "ONE THING I RELEASE TODAY", None, True),
        ("🙏", "EVENING GRATITUDE", None, True),
    ]
    for icon, title, inline, has_lines in sections:
        c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGIN, y, f"{icon}  {title}")
        if inline:
            c.setFillColor(DARK); c.setFont("Helvetica", 11)
            c.drawString(MARGIN + 2.2*inch, y - 0.02*inch, inline)
            y -= 0.32*inch
        else:
            _ruled(c, y - 0.2*inch, 2, 0.28*inch)
            y -= 0.78*inch


def page_healthy_eating(c, accent):
    _page_header(c, accent, "HEALTHY EATING TRACKER", "Date: ___/___/______")
    top = PAGE_H - MARGIN - 0.6*inch

    meals = [
        ("🌅", "BREAKFAST"),
        ("☀️", "LUNCH"),
        ("🌙", "DINNER"),
        ("🍎", "SNACKS"),
    ]
    meal_h = 1.05*inch
    y = top
    for icon, label in meals:
        c.setFillColor(accent)
        c.setFillAlpha(0.08)
        c.roundRect(MARGIN, y - meal_h, PAGE_W - 2*MARGIN, meal_h, 6, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGIN + 0.1*inch, y - 0.18*inch, f"{icon}  {label}")
        c.setFont("Helvetica", 7)
        c.setFillColor(LIGHT)
        c.drawRightString(PAGE_W - MARGIN - 0.1*inch, y - 0.18*inch, "Cal: _______")
        c.setStrokeColor(GRAY); c.setLineWidth(0.4)
        for li in range(3):
            ly = y - 0.42*inch - li * 0.22*inch
            c.line(MARGIN + 0.1*inch, ly, PAGE_W - MARGIN - 0.1*inch, ly)
        y -= meal_h + 0.08*inch

    # Water tracker
    y -= 0.05*inch
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, y, "💧  WATER INTAKE")
    wx = MARGIN + 1.5*inch
    for gi in range(8):
        c.setStrokeColor(accent); c.setFillColor(colors.HexColor("#dbeafe"))
        c.setFillAlpha(0.5)
        c.roundRect(wx + gi * 0.32*inch, y - 0.22*inch, 0.26*inch, 0.24*inch, 4, fill=1, stroke=1)
        c.setFillAlpha(1)
        c.setFillColor(LIGHT); c.setFont("Helvetica", 7)
        c.drawCentredString(wx + gi * 0.32*inch + 0.13*inch, y - 0.1*inch, "□")
    y -= 0.38*inch

    # Energy + mood
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, y, "⚡  ENERGY LEVEL:")
    c.setFont("Helvetica", 10)
    c.setFillColor(DARK)
    for si, star in enumerate(["①","②","③","④","⑤"]):
        c.drawString(MARGIN + 1.5*inch + si*0.28*inch, y - 0.02*inch, star)
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN + 3.5*inch, y, "😊  MOOD:")
    c.setFont("Helvetica", 10); c.setFillColor(DARK)
    for mi, mood in enumerate(["😞","😐","🙂","😄"]):
        c.drawString(MARGIN + 4.3*inch + mi*0.28*inch, y - 0.02*inch, mood)
    y -= 0.38*inch

    # Notes
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, y, "📝  NOTES & HOW I FEEL")
    _ruled(c, y - 0.22*inch, 4, 0.3*inch)


def page_planner(c, accent):
    _page_header(c, accent, "DAILY PLANNER", "Date: ___/___/______")
    top = PAGE_H - MARGIN - 0.6*inch
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, top, "TOP 3 PRIORITIES")
    y = top - 0.25*inch
    for _ in range(3):
        c.setStrokeColor(accent); c.roundRect(MARGIN, y - 0.16*inch, 0.16*inch, 0.16*inch, 2, fill=0)
        c.setStrokeColor(GRAY); c.line(MARGIN + 0.25*inch, y - 0.08*inch, PAGE_W - MARGIN, y - 0.08*inch)
        y -= 0.38*inch
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, y - 0.1*inch, "SCHEDULE")
    y -= 0.35*inch
    hours = ["6AM","7AM","8AM","9AM","10AM","11AM","12PM","1PM","2PM","3PM","4PM","5PM","6PM","7PM","8PM"]
    for h in hours:
        c.setFillColor(accent); c.setFont("Helvetica-Bold", 7); c.drawString(MARGIN, y, h)
        c.setStrokeColor(GRAY); c.setLineWidth(0.4); c.line(MARGIN + 0.38*inch, y, PAGE_W - MARGIN, y)
        y -= 0.27*inch
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 9); c.drawString(MARGIN, y - 0.05*inch, "NOTES")
    _ruled(c, y - 0.25*inch, 2)


def simple_cover(c, title, subtitle, accent, author):
    c.setFillColor(accent)
    c.rect(0, PAGE_H - 2.5*inch, PAGE_W, 2.5*inch, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(PAGE_W/2, PAGE_H - 1.2*inch, title)
    if subtitle:
        c.setFont("Helvetica-Oblique", 12)
        c.drawCentredString(PAGE_W/2, PAGE_H - 1.8*inch, subtitle)
    if author:
        c.setFillColor(DARK); c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(PAGE_W/2, 1.2*inch, author)
    c.setFillColor(DARK); c.setFont("Helvetica", 9)
    c.drawCentredString(PAGE_W/2, 0.6*inch, "Name: _________________________________")
    c.showPage()


def create_book(out_path, title, subtitle, ptype, theme, pages, author=""):
    if ptype == 'cookbook':
        return create_cookbook(out_path, title, subtitle, theme, pages, author)

    accent = theme_color(theme)
    pages = max(2, min(int(pages or 120), 300))
    c = canvas.Canvas(out_path, pagesize=(PAGE_W, PAGE_H))
    simple_cover(c, title, subtitle, accent, author)

    builders = {
        "journal":        page_journal,
        "planner":        page_planner,
        "habit":          page_habit,
        "gratitude":      page_gratitude,
        "fitness":        page_fitness,
        "tracker":        page_tracker,
        "budget":         page_budget,
        "mindfulness":    page_mindfulness,
        "healthy_eating": page_healthy_eating,
    }
    builder = builders.get(ptype, page_journal)
    for i in range(pages - 1):
        builder(c, accent)
        c.setFillColor(LIGHT); c.setFont("Helvetica", 8)
        c.drawCentredString(PAGE_W/2, 0.3*inch, str(i + 2))
        c.showPage()

    c.save()
    return pages


# ══════════════════════════════════════════
#  AI CONTENT ENGINE (Groq — same model/key as the Scout/Builder agents in server.js)
# ══════════════════════════════════════════

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"


def get_groq_key():
    key = os.environ.get('GROQ_KEY')
    if key:
        return key
    # standalone runs (no server.js/dotenv parent) — read .env directly
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('GROQ_KEY'):
                    return line.split('=', 1)[1].strip()
    return None


# ADR-041: real per-call AI cost, logged going forward — previously Groq's
# response `usage` field was read and discarded. Rates confirmed directly
# from Groq's own pricing docs (console.groq.com/docs/model/llama-3.1-8b-instant,
# checked 2026-07-15): $0.05/M input tokens, $0.08/M output tokens. Update
# this constant if the model or its published price ever changes — it is
# not a guess, but it is a snapshot, and needs re-verifying periodically.
GROQ_PRICING_USD_PER_MILLION_TOKENS = {"llama-3.1-8b-instant": {"input": 0.05, "output": 0.08}}
AI_COST_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'ai_cost_log.jsonl')


def _log_ai_cost(model, usage, context=None, log_file=None):
    """Appends one real, verifiable cost record per Groq call. Never raises —
    a logging failure must not break book generation. This is purely
    additive data collection for ADR-041's Margin Score real-cost
    component: with zero real calls logged yet, that component has nothing
    to average yet — this is what starts making it real over time, not a
    backdated fabrication."""
    try:
        log_file = log_file or AI_COST_LOG_FILE
        prompt_tokens = usage.get('prompt_tokens', 0) if usage else 0
        completion_tokens = usage.get('completion_tokens', 0) if usage else 0
        rates = GROQ_PRICING_USD_PER_MILLION_TOKENS.get(model)
        cost_usd = None
        if rates:
            cost_usd = round(
                prompt_tokens / 1_000_000 * rates['input'] + completion_tokens / 1_000_000 * rates['output'], 6
            )
        record = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": usage.get('total_tokens') if usage else None,
            "cost_usd": cost_usd,
            "context": context,
        }
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except Exception:
        pass  # logging must never break the actual generation call


def groq_chat(system_prompt, user_prompt, max_tokens=4096, timeout=30, retries=3, cost_context=None):
    """Calls Groq with timeout + retry + graceful failure (Constitution §3: Fault Tolerance).
    Auth/bad-request errors (401/403/400) are not retried — retrying can't fix a bad key.
    Return value is unchanged (still just the content string) — real cost
    tracking (ADR-041) is a side effect via _log_ai_cost(), not a signature
    change, so this stays a drop-in replacement for the one existing caller."""
    key = get_groq_key()
    if not key:
        raise RuntimeError("GROQ_KEY غير موجود في البيئة أو .env")
    payload = json.dumps({
        "model": GROQ_MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {key}',
        'User-Agent': 'Mozilla/5.0 (OpenClaw-Factory-BookGenerator)',
        'Accept': 'application/json',
    }

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(GROQ_API_URL, data=payload, method='POST', headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                result = json.loads(r.read().decode('utf-8'))
            _log_ai_cost(GROQ_MODEL, result.get('usage'), cost_context)
            return result['choices'][0]['message']['content']
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code in (400, 401, 403):
                break  # not transient — no point retrying
        except Exception as e:
            last_error = e
        if attempt < retries:
            time.sleep(min(2 ** (attempt - 1), 4))

    raise RuntimeError(f"فشل استدعاء Groq بعد {retries} محاولات: {last_error}")


def _parse_sectioned_book(text, expected_chapters):
    # Small/instant models reliably break valid JSON on long Arabic text (missing
    # commas, unescaped quotes) and don't reliably echo literal English tags —
    # but they do consistently emit '## heading ##'-style Markdown headers.
    # Parse by header line + keyword instead of relying on exact tag text.
    parts = re.split(r'(?m)^#{1,4}\s*(.+?)\s*#{0,4}\s*$', text)

    subtitle, introduction, conclusion = '', '', ''
    chapters = []
    # Code review fix (2026-07-13): the prompt emits TWO separate markers per
    # chapter (##CHAPTER N TITLE## and ##CHAPTER N CONTENT##) — both contain
    # "chapter", so the old single `elif 'chapter' in header.lower()` branch
    # matched BOTH independently, appending two half-empty chapter entries
    # per real chapter (title text landing in one entry's "content" field,
    # the actual body in another). Pre-existing bug, not introduced by
    # today's English-prompt translation — the markers were already English
    # even in the old Arabic-instructed prompt. Now pairs a TITLE marker
    # with the next CONTENT marker into one chapter entry; a chapter header
    # with no TITLE/CONTENT sub-tag at all (looser model output) still falls
    # back to one entry per header, as before.
    pending_chapter_title = None
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        header_lower = header.lower()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ''
        if 'خاتم' in header or 'خلاص' in header or 'conclusion' in header_lower:
            conclusion = body
        elif 'مقدم' in header or 'intro' in header_lower:
            introduction = body
        elif ('فصل' in header or 'chapter' in header_lower) and ('title' in header_lower or 'عنوان' in header):
            pending_chapter_title = body
        elif ('فصل' in header or 'chapter' in header_lower) and ('content' in header_lower or 'محتوى' in header):
            chapters.append({"title": pending_chapter_title or header, "content": body})
            pending_chapter_title = None
        elif 'فصل' in header or 'chapter' in header_lower:
            chapters.append({"title": header, "content": body})
        elif 'فرعي' in header or 'subtitle' in header_lower:
            # BUG FIX: this branch used to be reached via the generic
            # "first unrecognized header" fallback below, which assigned
            # `subtitle = header` — when the model dutifully echoes the
            # literal "##SUBTITLE##" tag, that made subtitle literally the
            # word "SUBTITLE" while the real subtitle text (in `body`) was
            # silently reassigned to `introduction`. The value belongs in
            # the body, never the tag/header text itself.
            subtitle = body
        elif not subtitle and not chapters and not introduction:
            # Loose fallback for when the model invents its own natural-
            # language header instead of a recognizable tag — use body as
            # the subtitle when there is one; only fall back to the header
            # text itself if the model left the body empty.
            subtitle = body or header
        else:
            # Code review fix (2026-07-13): observed live — a model that
            # dutifully labels its FIRST chapter "Chapter 1: ..." (matching
            # the branch above) sometimes drifts to purely natural-language
            # headers for LATER chapters ("Create a Kickoff Checklist to Get
            # Your Projects Off to a Flying Start", no "chapter"/"فصل"
            # anywhere) — those previously matched no branch at all and were
            # silently dropped, sometimes leaving zero recognized chapters.
            # Once subtitle/introduction is already set, any further
            # unrecognized header before ##CONCLUSION## can only be a
            # chapter the model titled in its own words.
            chapters.append({"title": header, "content": body})

    if not chapters:
        raise ValueError("لم يتم العثور على أي فصول في رد الذكاء الاصطناعي")

    return {
        "subtitle": subtitle,
        "introduction": introduction,
        "chapters": chapters,
        "conclusion": conclusion,
    }


def ai_generate_book_content(title, topic, chapters, audience):
    # Code review fix (2026-07-13): this prompt instructed Groq in Arabic
    # unconditionally — a gap ADR-020 (EU/US English market, 2026-07-12)
    # never actually closed here, since yesterday's work touched
    # create_book() (already English) and generate_book_from_content()
    # (content supplied externally) but never this function, the one Scout/
    # hunt()/Golden Hunter's generate_book() path actually calls. Rewritten
    # in English to match the standing market decision — no toggle added,
    # same precedent as create_book()'s printable pages (hardcoded English,
    # no parameter) since English is the default target market now, not an
    # option among several.
    n = max(2, min(int(chapters or 8), 20))
    system = (
        "You are the content-building agent at OpenClaw Factory. You write real, complete digital "
        "book content (not summaries or bare headings), at a quality bar suitable for direct "
        "publication on Amazon KDP or Gumroad, for an English-speaking EU/US audience."
    )
    chapter_markers = "\n".join(
        f"##CHAPTER {i} TITLE##\nChapter {i} title\n##CHAPTER {i} CONTENT##\nFull content of chapter {i} (300-500 words)"
        for i in range(1, n + 1)
    )
    user_prompt = f"""Write the complete content of a digital book.
Title: "{title}"
Topic/niche: {topic}
Target audience: {audience}
Number of chapters: {n}

Very important: return ONLY this exact plain-text format (no JSON, no Markdown), keeping the ##...## markers exactly as written, in the same order, for all {n} chapters:

##SUBTITLE##
A compelling subtitle
##INTRODUCTION##
A real introduction (150-250 words)
{chapter_markers}
##CONCLUSION##
A conclusion (100-150 words)

Do not add any explanation, numbering, or text outside these sections. Every chapter's content must be real, useful text, not filler."""
    raw = groq_chat(system, user_prompt, max_tokens=4096, cost_context={"niche": topic, "title": title})
    return _parse_sectioned_book(raw, n)


def _fallback_book_content(title, topic, chapters, audience):
    # Code review fix (2026-07-13): same English-market fix as
    # ai_generate_book_content() above — this fallback must never revert to
    # Arabic when the real AI call fails, or a failed Groq call would
    # silently ship an Arabic placeholder for an English-market product.
    n = max(2, min(int(chapters or 8), 20))
    return {
        "subtitle": f"A Complete Guide to {topic}",
        "introduction": (
            f"This book offers a practical introduction to {topic}, written for {audience}. "
            "AI content generation was unavailable for this attempt, so this edition shows a "
            "basic structure that can be regenerated later."
        ),
        "chapters": [
            {
                "title": f"Chapter {i}: The Basics of {topic}",
                "content": f"This chapter's content is being prepared and will cover important aspects of {topic} for {audience}.",
            }
            for i in range(1, n + 1)
        ],
        "conclusion": "We hope this book is useful to you on your journey.",
    }


def safe_cover(c, title, subtitle, accent, author):
    try:
        simple_cover(c, title, subtitle, accent, author)
    except Exception:
        try:
            c.setFillColor(WHITE)
            c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
            c.setFillColor(DARK)
            c.setFont("Helvetica-Bold", 20)
            c.drawCentredString(PAGE_W / 2, PAGE_H / 2, str(title)[:60])
            c.showPage()
        except Exception:
            c.showPage()


def draw_cover_v2(c, title, subtitle, author, topic, theme):
    """Uses cover_designer_v2.py's Pillow-rendered 70/20/10 cover instead of
    the vector-drawn safe_cover() below, when available. A cover must never
    block book production (Constitution: fault tolerance) — any failure here
    (missing Pillow, a font issue, cover_designer_v2's own quality gate
    rejecting the result) falls back to safe_cover() instead of raising.
    Returns the cover_designer_v2 result dict on success, or None if the
    fallback was used."""
    if COVER_DESIGNER_V2 is not None:
        try:
            cover_result = COVER_DESIGNER_V2.generate_cover(
                title=title, subtitle=subtitle, author=author,
                niche=topic, theme=theme,
            )
            if cover_result.get('success'):
                img = ImageReader(cover_result['path'])
                c.drawImage(img, 0, 0, PAGE_W, PAGE_H, preserveAspectRatio=False, mask='auto')
                c.showPage()
                return cover_result
        except Exception:
            pass
    safe_cover(c, title, subtitle, theme_color(theme), author)
    return None


def draw_flowing_text(c, accent, header_label, paragraphs, x, top, max_width, page_counter,
                       font="Helvetica", size=10, line_height=None, para_gap=None, bottom=1 * inch):
    if line_height is None:
        line_height = size * 1.45
    if para_gap is None:
        para_gap = line_height * 0.7
    y = top
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        words = para.split()
        line = ""
        c.setFont(font, size)
        c.setFillColor(DARK)
        for w in words:
            test = (line + " " + w).strip()
            if c.stringWidth(test, font, size) <= max_width:
                line = test
            else:
                if y < bottom:
                    c.showPage()
                    page_counter[0] += 1
                    _page_header(c, accent, header_label)
                    y = PAGE_H - MARGIN - 0.9 * inch
                    c.setFont(font, size)
                    c.setFillColor(DARK)
                c.drawString(x, y, line)
                y -= line_height
                line = w
        if line:
            if y < bottom:
                c.showPage()
                page_counter[0] += 1
                _page_header(c, accent, header_label)
                y = PAGE_H - MARGIN - 0.9 * inch
                c.setFont(font, size)
                c.setFillColor(DARK)
            c.drawString(x, y, line)
            y -= line_height
        y -= para_gap
    return y


def create_ai_book(out_path, title, subtitle, theme, author, book_data, topic=""):
    accent = theme_color(theme)
    c = canvas.Canvas(out_path, pagesize=(PAGE_W, PAGE_H))
    page_counter = [0]

    # Cover — never blocks production (see draw_cover_v2/safe_cover)
    cover_info = draw_cover_v2(c, title, subtitle, author, topic, theme)
    page_counter[0] += 1

    chapters = book_data.get('chapters') or []

    # Table of contents
    _page_header(c, accent, "TABLE OF CONTENTS")
    top = PAGE_H - MARGIN - 0.9 * inch
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(PAGE_W / 2, top, "What's Inside")
    y = top - 0.5 * inch
    for i, ch in enumerate(chapters, 1):
        if y < 1 * inch:
            c.showPage()
            page_counter[0] += 1
            _page_header(c, accent, "TABLE OF CONTENTS (cont.)")
            y = PAGE_H - MARGIN - 0.9 * inch
        c.setFillColor(accent)
        c.setFillAlpha(0.1)
        c.roundRect(MARGIN, y - 0.22 * inch, PAGE_W - 2 * MARGIN, 0.36 * inch, 5, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 10)
        label = f"{i}.  {ch.get('title', '')}"
        c.drawString(MARGIN + 0.1 * inch, y, label[:70])
        y -= 0.42 * inch
    c.showPage()
    page_counter[0] += 1

    # Introduction
    intro = book_data.get('introduction') or ''
    if intro:
        _page_header(c, accent, "INTRODUCTION")
        draw_flowing_text(c, accent, "INTRODUCTION", intro.split('\n\n'),
                           MARGIN, PAGE_H - MARGIN - 0.9 * inch, PAGE_W - 2 * MARGIN, page_counter)
        c.showPage()
        page_counter[0] += 1

    # Chapters
    for i, ch in enumerate(chapters, 1):
        header_label = f"CHAPTER {i}"
        _page_header(c, accent, header_label)
        top = PAGE_H - MARGIN - 0.9 * inch
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 17)
        y = _wrap_text(c, ch.get('title', ''), MARGIN, top, PAGE_W - 2 * MARGIN,
                        "Helvetica-Bold", 17, accent, 0.28 * inch)
        y -= 0.2 * inch
        content = ch.get('content') or ''
        draw_flowing_text(c, accent, header_label, content.split('\n\n'),
                           MARGIN, y, PAGE_W - 2 * MARGIN, page_counter)
        c.showPage()
        page_counter[0] += 1

    # Conclusion
    conclusion = book_data.get('conclusion') or ''
    if conclusion:
        _page_header(c, accent, "CONCLUSION")
        draw_flowing_text(c, accent, "CONCLUSION", conclusion.split('\n\n'),
                           MARGIN, PAGE_H - MARGIN - 0.9 * inch, PAGE_W - 2 * MARGIN, page_counter)
        c.showPage()
        page_counter[0] += 1

    c.save()
    return page_counter[0], cover_info


_PLACEHOLDER_WORDS = {
    'subtitle', 'title', 'introduction', 'conclusion', 'chapter', 'chapters',
    'audience', 'price', 'topic', 'niche', 'author', 'untitled',
}


def _looks_like_placeholder(text):
    """True when text is (almost) exactly a prompt-tag name the AI echoed
    back literally (e.g. the bare word "SUBTITLE") rather than real content.
    Only rejects short (<=2 word) matches, so a genuine subtitle that merely
    contains one of these words in a longer sentence is never rejected."""
    if not text:
        return False
    words = str(text).strip().split()
    if not words or len(words) > 2:
        return False
    normalized = re.sub(r'[^a-zA-Z]', '', str(text)).strip().lower()
    return normalized in _PLACEHOLDER_WORDS


def _resolve_subtitle(ai_subtitle, topic):
    """Never let a literal placeholder echo (e.g. "SUBTITLE") reach book
    pages or the cover. Falls back to a topic-derived subtitle, or omits it
    entirely (empty string) if there's no topic to derive one from."""
    ai_subtitle = str(ai_subtitle or '').strip()
    if ai_subtitle and not _looks_like_placeholder(ai_subtitle):
        return ai_subtitle
    topic = str(topic or '').strip()
    return f"دليلك الكامل في {topic}" if topic else ''


def _resolve_price(topic, price):
    """Smart Publishing (OPENCLAW_OS_CONSTITUTION.md) + Butter Principle
    (CONSTITUTION.md §16): a price below $30 is not an automatic rejection.
    Groq defaulting to a template price (its own few-shot example used to
    show "9.99") is a correctable mistake, not evidence the niche is weak —
    only profit_oracle scoring this niche as SKIP (<60: genuinely thin
    demand or saturated competition) means no price would make it worth
    building, and that case is left alone to fail Commercial Audit honestly
    rather than papering over it with a bigger number.

    Returns (resolved_price, was_repriced)."""
    try:
        price_val = max(0.0, float(price))
    except (TypeError, ValueError):
        price_val = 0.0
    if price_val >= 30 or PROFIT_ORACLE is None or not str(topic or '').strip():
        return price_val, False
    try:
        scored = PROFIT_ORACLE.score_opportunity(topic)
        if scored['verdict'] == 'SKIP':
            return price_val, False  # genuinely weak niche — no repricing rescues it
        new_price = float(PROFIT_ORACLE.butter_price(topic))
    except Exception:
        return price_val, False
    return new_price, True


def _summarize_inspection_failure(inspection):
    """Mirrors factory_loop.js's summarizeInspectionFailure() exactly — same
    reasoning text regardless of which side of the process boundary wrote
    the rejection."""
    if not inspection:
        return "سبب غير معروف (لا بيانات فحص)"
    failures = list((inspection.get("technical") or {}).get("failures") or []) + \
        list((inspection.get("commercial") or {}).get("failures") or [])
    return "؛ ".join(failures) if failures else "رُفض دون سبب مُفصَّل"


def _record_rejected_niche(niche, title, reason):
    """The shared circuit-breaker recording point (CONSTITUTION.md §19/§20 —
    closes the gap self_awareness.js's own Constitution-compliance check
    flagged: REJECTED_NICHES.md used to be written ONLY by factory_loop.js's
    hunt()/market_hunter.py, so a niche rejected via the Scout button
    (/api/scout/run → this exact function) or a direct /generate-book call
    was never remembered and could be retried endlessly.

    generate_book() is the ONE function every caller — hunt(), Scout,
    /generate-book directly — ultimately goes through, so writing here
    (rather than in each caller separately) means every path shares one
    memory automatically, with no risk of drifting out of sync. Writes the
    exact same file, in the exact same format, that factory_loop.js's own
    recordRejectedNiche() writes — either side can read what the other
    wrote; see REJECTED_NICHES.md's own parsing regex in factory_loop.js."""
    factory_dir = os.path.dirname(os.path.abspath(__file__))
    rejected_file = os.path.join(factory_dir, 'REJECTED_NICHES.md')
    # No 'Z' suffix: datetime.now() is naive local time, not UTC — matching
    # the same convention already used by inspectors.py's QUARANTINE.md
    # entries (Node's factory_loop.js writes a real UTC 'Z' timestamp for
    # its own entries; Date.parse() on the JS reading side still parses
    # this naive format correctly for the cooldown-window math either way).
    timestamp = datetime.now().isoformat()
    entry = (
        f"## 🚫 {timestamp}\n"
        f"**النيتش:** {niche or ''}\n"
        f"**العنوان:** {title or ''}\n"
        f"**السبب:** {reason}\n\n"
    )
    try:
        if not os.path.exists(rejected_file):
            with open(rejected_file, 'w', encoding='utf-8') as f:
                f.write(
                    "# 🚫 Rejected Niches — ذاكرة قاطع الدائرة (Circuit Breaker)\n\n"
                    "نيتشات فشلت في اجتياز الفحص المزدوج (Dual Inspection, CONSTITUTION.md §17) — "
                    "تُحفَظ هنا كي لا يُعاد توليدها ويُهدَر استدعاء Groq عليها قبل انتهاء فترة التهدئة "
                    "(7 أيام). Anti-Fragility: كل فشل هنا معرفة دائمة، لا مجرد خطأ منسي.\n\n"
                )
        with open(rejected_file, 'a', encoding='utf-8') as f:
            f.write(entry)
    except Exception:
        pass


def _sanitize_filename_component(text, fallback="book"):
    text = re.sub(r'[^\w\-]+', '_', str(text or ''), flags=re.UNICODE).strip('_').lower()
    return text or fallback


def _resolve_safe_output_path(books_dir, output, title):
    """Confines the output PDF to books_dir regardless of what the caller passes
    in `output` (Constitution §4: sanitize filenames, prevent path traversal)."""
    fallback_name = _sanitize_filename_component(title)
    if output:
        base = os.path.basename(str(output))          # drops any ../ or C:\ the caller supplied
        name, _ext = os.path.splitext(base)
        name = _sanitize_filename_component(name, fallback=fallback_name)
    else:
        name = fallback_name
    filename = f"{name}.pdf"

    books_dir_real = os.path.realpath(books_dir)
    out_path = os.path.realpath(os.path.join(books_dir_real, filename))
    if os.path.commonpath([out_path, books_dir_real]) != books_dir_real:
        raise ValueError("مسار ملف الإخراج غير آمن")
    return out_path, filename


def _log_generation(result):
    """Factory Memory (Constitution §5): every production run is recorded.
    Logging failures must never break a successful generation."""
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books', '_generation_log.jsonl')
        entry = dict(result)
        entry['timestamp'] = datetime.now().isoformat()
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception:
        pass


def _find_niche_report(niche):
    """Best-effort lookup of a previously saved niche_validator_v2.py report
    matching this niche's keyword, so the Quality Gate can reuse a real
    Amazon competition figure when one exists."""
    if not niche:
        return None
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'niche_reports')
    if not os.path.isdir(reports_dir):
        return None
    niche_lower = str(niche).lower()
    for fname in sorted(os.listdir(reports_dir), reverse=True):  # newest first (timestamp-prefixed names)
        if not fname.endswith('.json'):
            continue
        try:
            with open(os.path.join(reports_dir, fname), 'r', encoding='utf-8') as f:
                report = json.load(f)
        except Exception:
            continue
        keyword = str(report.get('keyword', '')).strip().lower()
        if keyword and (keyword in niche_lower or niche_lower in keyword):
            return report
    return None


def quality_gate(niche, theme=None):
    """Pre-generation Quality Gate (Constitution: no stage may bypass quality
    validation). Checks, in order:
      1. niche not empty
      2. estimated Amazon competition below niche_validator_v2.py's threshold
         (only when a matching saved research report exists — that tool is
         deliberately offline/manual, so we never scrape Amazon automatically;
         with no matching research the check is skipped, not failed, since a
         freshly Scout-picked niche won't have a report yet)
      3. a cover template/theme is available
    Returns {"passed": bool, "reason": str, "checks": {...}}. Callers must not
    proceed to generation when passed is False.
    """
    checks = {}

    niche_ok = bool(niche and str(niche).strip())
    checks['niche_not_empty'] = {
        'passed': niche_ok,
        'detail': str(niche).strip() if niche_ok else 'النيتش فارغ',
    }

    max_competition = (NICHE_VALIDATOR.CRITERIA['max_competition'] if NICHE_VALIDATOR else 50000)
    report = _find_niche_report(niche) if niche_ok else None
    if report and report.get('status') == 'success':
        total_results = report.get('metrics', {}).get('total_results', 0)
        competition_ok = 0 < total_results < max_competition
        checks['amazon_competition'] = {
            'passed': competition_ok,
            'detail': f"{total_results:,} نتيجة على Amazon (الحد الأقصى: {max_competition:,}) — من تقرير محفوظ: {report.get('source_file', '')}",
        }
    else:
        checks['amazon_competition'] = {
            'passed': True,
            'skipped': True,
            'detail': f"لا يوجد بحث Amazon محفوظ لهذا النيتش بعد — تم تخطي الفحص (الحد المرجعي: {max_competition:,} نتيجة)",
        }

    theme_key = str(theme or 'orange').strip().lower()
    cover_ok = theme_key in THEMES
    checks['cover_template'] = {
        'passed': cover_ok,
        'detail': theme_key if cover_ok else f"ثيم غير معروف: '{theme_key}' — المتاح: {', '.join(THEMES.keys())}",
    }

    passed = all(c['passed'] for c in checks.values())
    reason = 'نجحت كل فحوصات الجودة' if passed else '؛ '.join(
        f"{name}: {c['detail']}" for name, c in checks.items() if not c['passed']
    )
    return {'passed': passed, 'reason': reason, 'checks': checks}


def generate_book(title, topic, chapters=8, audience="القارئ العام", price=9.99,
                   theme="blue", author="OpenClaw Press", output=None):
    """يولّد كتاباً رقمياً كاملاً بمحتوى حقيقي من نفس الذكاء الاصطناعي (Groq) الذي يشغّل وكيل Scout.
    لا يتوقف عند فشل الـ AI أو الغلاف — ينتج نسخة بديلة أقل جودة بدلاً من ذلك."""
    title = str(title or '').strip()
    if not title:
        raise ValueError("العنوان (title) مطلوب")
    topic = str(topic or '').strip()[:500]
    audience = str(audience or 'القارئ العام').strip()[:200] or 'القارئ العام'
    price, repriced = _resolve_price(topic, price)
    try:
        chapters = max(2, min(int(chapters), 20))
    except (TypeError, ValueError):
        chapters = 8

    gate = quality_gate(topic, theme)
    if not gate['passed']:
        result = {
            "success": False,
            "error": f"Quality Gate: {gate['reason']}",
            "quality_gate": gate,
            "title": title,
            "topic": topic,
        }
        _log_generation(result)
        return result

    books_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books')
    os.makedirs(books_dir, exist_ok=True)
    out_path, filename = _resolve_safe_output_path(books_dir, output, title)

    ai_error = None
    try:
        book_data = ai_generate_book_content(title, topic, chapters, audience)
    except Exception as e:
        ai_error = str(e)
        book_data = _fallback_book_content(title, topic, chapters, audience)

    subtitle = _resolve_subtitle(book_data.get('subtitle'), topic)
    n_pages, cover_info = create_ai_book(out_path, title, subtitle, theme, author, book_data, topic=topic)

    result = {
        "success": True,
        "file": filename,
        "path": out_path,
        "pages": n_pages,
        "topic": topic,
        "audience": audience,
        "price": price,
        "repriced": repriced,
        "ai_used": ai_error is None,
        "ai_error": ai_error,
        "quality_gate": gate,
        "cover": cover_info,
        "cover_v2_used": cover_info is not None,
    }

    # Dual-Inspector Quality System (CONSTITUTION.md §17) — the master gate.
    # A book being written to disk successfully is not the same as it being
    # cleared to publish; that only happens if BOTH inspectors approve. If
    # the inspection system itself is unavailable, this fails closed (never
    # silently treated as approved) rather than skipping inspection.
    if INSPECTORS is not None:
        try:
            inspection = INSPECTORS.final_inspection({
                "pdf_path": out_path,
                "cover_path": cover_info.get("path") if cover_info else None,
                "title": title,
                "subtitle": subtitle,
                "author": author,
                "niche": topic,
                "price": price,
                "min_pages": 4,
            })
        except Exception as e:
            inspection = {"passed": False, "published": False,
                          "technical": {"passed": False, "checks": [], "severity": "critical",
                                        "failures": [f"استثناء غير متوقَّع أثناء الفحص: {e}"]},
                          "commercial": {"passed": False, "checks": [], "failures": [], "verdict": "لم يُدقَّق"}}
    else:
        inspection = {"passed": False, "published": False,
                      "technical": {"passed": False, "checks": [], "severity": "critical",
                                    "failures": ["inspectors.py غير متوفر — لا يمكن الموافقة على النشر"]},
                      "commercial": {"passed": False, "checks": [], "failures": [], "verdict": "لم يُدقَّق"}}

    result["published"] = inspection["published"]
    result["inspection"] = inspection

    # Circuit breaker (CONSTITUTION.md §19/§20) — recorded HERE, the one
    # function every caller (Scout, /generate-book directly, factory_loop.js's
    # hunt()) ultimately goes through, so every path shares one memory. This
    # closes the exact gap self_awareness.js's own Constitution-compliance
    # check flagged: REJECTED_NICHES.md used to be written only from
    # factory_loop.js's side, so a niche rejected via the Scout button was
    # never remembered.
    if not inspection["published"]:
        _record_rejected_niche(topic, title, _summarize_inspection_failure(inspection))

    _log_generation(result)
    return result


def generate_printable(title, ptype, price, subtitle="", pages=15, theme="blue", author="OpenClaw Press", output=None):
    """Generates a real English EU/US printable (planner/tracker/habit/
    budget/...) via the EXISTING create_book() — its internal drawing logic
    is untouched, called exactly as before — then wires the result through
    the same Dual Inspection + Factory Memory + circuit-breaker pipeline
    generate_book() already uses (ADR-020/ADR-021): create_book()'s output
    stops being a dead end. Scout/hunt()/Golden Hunter's generate_book()
    path and this one now share the exact same downstream (inspectors.py,
    books/_generation_log.jsonl, and — via schemas/product.py's
    product_type="printable" routing — distributor.py).

    Economically evaluated against "gumroad_digital" (ADR-020's separate
    $2.50 profit floor), never "kdp_ebook" — these are not KDP products."""
    title = str(title or '').strip()
    if not title:
        raise ValueError("العنوان (title) مطلوب")
    ptype = str(ptype or '').strip().lower()
    try:
        pages = max(2, min(int(pages), 60))
    except (TypeError, ValueError):
        pages = 15

    books_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books')
    os.makedirs(books_dir, exist_ok=True)
    out_path, filename = _resolve_safe_output_path(books_dir, output, title)

    n_pages = create_book(out_path, title, subtitle, ptype, theme, pages, author)

    result = {
        "success": True,
        "file": filename,
        "path": out_path,
        "pages": n_pages,
        "topic": title,
        "price": price,
        "product_type": "printable",
    }

    # Dual-Inspector Quality System (CONSTITUTION.md §17) — same master gate
    # generate_book() uses. cover_path=None: create_book() draws its cover on
    # page 1 of the same PDF, not a separate file.
    if INSPECTORS is not None:
        try:
            inspection = INSPECTORS.final_inspection({
                "pdf_path": out_path,
                "cover_path": None,
                "title": title,
                "subtitle": subtitle,
                "author": author,
                "niche": title,
                "price": price,
                "platform": _economics_platform_for("printable"),
                "page_count": n_pages,
                "min_pages": 4,
            })
        except Exception as e:
            inspection = {"passed": False, "published": False,
                          "technical": {"passed": False, "checks": [], "severity": "critical",
                                        "failures": [f"استثناء غير متوقَّع أثناء الفحص: {e}"]},
                          "commercial": {"passed": False, "checks": [], "failures": [], "verdict": "لم يُدقَّق"}}
    else:
        inspection = {"passed": False, "published": False,
                      "technical": {"passed": False, "checks": [], "severity": "critical",
                                    "failures": ["inspectors.py غير متوفر — لا يمكن الموافقة على النشر"]},
                      "commercial": {"passed": False, "checks": [], "failures": [], "verdict": "لم يُدقَّق"}}

    result["published"] = inspection["published"]
    result["inspection"] = inspection

    if not inspection["published"]:
        _record_rejected_niche(title, title, _summarize_inspection_failure(inspection))

    _log_generation(result)
    return result


# ── ECONOMICS PLATFORM ROUTING (ADR-020/ADR-024) ──
# Shared by generate_book_from_content() and schemas/product.py's mirror
# logic — kept here too so inspectors.py's Dual Inspection evaluates the
# SAME platform distributor.py will later evaluate the resulting Product
# against, never a mismatched one.
def _economics_platform_for(product_type):
    if product_type == "elite":
        return "gumroad_elite"
    if product_type == "premium":
        return "gumroad_premium"
    if product_type == "printable":
        return "gumroad_digital"
    return "kdp_ebook"


def generate_book_from_content(title, subtitle, chapters, price, theme="blue",
                                author="OpenClaw Press", output=None, product_type="book"):
    """ADR-022: assembles a real PDF from ALREADY-WRITTEN chapters — a human
    (the president) + Claude authoring/review collaboration, never Groq —
    through the exact same create_ai_book() + Dual Inspection + Factory
    Memory pipeline generate_book() already uses. ai_generate_book_content()/
    _fallback_book_content() are never called here; only the content SOURCE
    differs from generate_book(), nothing about the downstream pipeline.

    chapters: a non-empty list of {"title": str, "content": str} — content
    is used verbatim, never rewritten or truncated here.

    product_type: "book" (default, kdp_ebook economics), "printable"
    (gumroad_digital, ADR-020), or "premium" (gumroad_premium, ADR-024) —
    routes Dual Inspection's commercial audit to the matching platform so
    it never evaluates a $97 premium product against KDP's $6 floor or
    against the $2.50 printable floor."""
    title = str(title or '').strip()
    if not title:
        raise ValueError("العنوان (title) مطلوب")
    if not isinstance(chapters, list) or not chapters:
        raise ValueError("chapters يجب أن تكون قائمة غير فارغة من {title, content}")

    subtitle = _resolve_subtitle(subtitle, title)

    books_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books')
    os.makedirs(books_dir, exist_ok=True)
    out_path, filename = _resolve_safe_output_path(books_dir, output, title)

    book_data = {"chapters": chapters, "introduction": ""}
    n_pages, cover_info = create_ai_book(out_path, title, subtitle, theme, author, book_data, topic=title)

    result = {
        "success": True,
        "file": filename,
        "path": out_path,
        "pages": n_pages,
        "topic": title,
        "price": price,
        "product_type": product_type,
        "cover": cover_info,
        "cover_v2_used": cover_info is not None,
        "content_source": "human_claude_review",  # never "groq_ai" — audit trail (ADR-022)
    }

    platform = _economics_platform_for(product_type)

    if INSPECTORS is not None:
        try:
            inspection = INSPECTORS.final_inspection({
                "pdf_path": out_path,
                "cover_path": cover_info.get("path") if cover_info else None,
                "title": title,
                "subtitle": subtitle,
                "author": author,
                "niche": title,
                "price": price,
                "platform": platform,
                "page_count": n_pages,
                "min_pages": 4,
            })
        except Exception as e:
            inspection = {"passed": False, "published": False,
                          "technical": {"passed": False, "checks": [], "severity": "critical",
                                        "failures": [f"استثناء غير متوقَّع أثناء الفحص: {e}"]},
                          "commercial": {"passed": False, "checks": [], "failures": [], "verdict": "لم يُدقَّق"}}
    else:
        inspection = {"passed": False, "published": False,
                      "technical": {"passed": False, "checks": [], "severity": "critical",
                                    "failures": ["inspectors.py غير متوفر — لا يمكن الموافقة على النشر"]},
                      "commercial": {"passed": False, "checks": [], "failures": [], "verdict": "لم يُدقَّق"}}

    result["published"] = inspection["published"]
    result["inspection"] = inspection

    if not inspection["published"]:
        _record_rejected_niche(title, title, _summarize_inspection_failure(inspection))

    _log_generation(result)
    return result


def main():
    if '--quality-gate' in sys.argv:
        # Lightweight hook so other processes (server.js's /api/trends) can
        # reuse quality_gate() without duplicating its logic in JS — reads
        # {"niche": "...", "theme": "..."} from stdin, prints the gate result.
        try:
            data = json.loads(sys.stdin.read())
            result = quality_gate(data.get('niche', ''), data.get('theme', 'blue'))
            print(json.dumps(result, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"passed": False, "reason": str(e), "checks": {}}, ensure_ascii=False))
            sys.exit(1)
        return

    if '--json' not in sys.argv:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'demo_cookbook.pdf')
        n = create_cookbook(out, "The Complete Home Kitchen", "12 Chapters of Delicious Recipes", "orange", 60, "OpenClaw Press")
        print("Done ->", out, "| pages:", n)
        return
    try:
        data = json.loads(sys.stdin.read())

        if isinstance(data.get('chapters'), list):
            # Dispatch on KEY PRESENCE (a list, even empty), not truthiness —
            # an empty "chapters": [] must reach generate_book_from_content()'s
            # own ValueError("chapters يجب أن تكون قائمة غير فارغة...") for a
            # clear, honest failure. Dispatching on truthiness let an empty
            # list fall through all the way to the legacy create_book()
            # branch below, which silently produced a placeholder cookbook
            # PDF with no Dual Inspection and no clear error — exactly the
            # malformed-draft case scripts/process_approved_drafts.py must
            # reject loudly, not paper over.
            result = generate_book_from_content(
                title=data.get('title', 'Untitled'),
                subtitle=data.get('subtitle', ''),
                chapters=data['chapters'],
                price=data.get('price', 9.99),
                theme=data.get('theme', 'blue'),
                author=data.get('author', ''),
                output=data.get('output'),
                product_type=data.get('product_type', 'book'),
            )
            print(json.dumps(result, ensure_ascii=False))
            return

        if data.get('product_type') == 'printable':
            result = generate_printable(
                title=data.get('title', 'Untitled Printable'),
                ptype=data.get('ptype') or data.get('type', 'planner'),
                price=data.get('price', 5.0),
                subtitle=data.get('subtitle', ''),
                pages=data.get('pages', 15),
                theme=data.get('theme', 'blue'),
                author=data.get('author', ''),
                output=data.get('output'),
            )
            print(json.dumps(result, ensure_ascii=False))
            return

        if 'topic' in data:
            result = generate_book(
                title=data.get('title', 'Untitled Book'),
                topic=data.get('topic', ''),
                chapters=data.get('chapters', 8),
                audience=data.get('audience', 'القارئ العام'),
                price=data.get('price', 9.99),
                theme=data.get('theme', 'blue'),
                author=data.get('author', ''),
                output=data.get('output'),
            )
            print(json.dumps(result, ensure_ascii=False))
            return

        out_name = data.get('output') or 'book.pdf'
        out_path = os.path.abspath(out_name)
        n = create_book(
            out_path,
            data.get('title',    'The Complete Kitchen'),
            data.get('subtitle', 'Delicious Recipes for Every Occasion'),
            data.get('type',     'cookbook'),
            data.get('theme',    'orange'),
            data.get('pages',    120),
            data.get('author',   ''),
        )
        print(json.dumps({"success": True, "pages": n, "file": out_name}))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e), "trace": traceback.format_exc()}))
        sys.exit(1)


if __name__ == '__main__':
    main()