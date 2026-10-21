"""
Curated skincare ingredient dataset for Skyntri's Ingredient Scanner.

Structure
---------
CATEGORY_DEFAULTS: baseline safety/skin-type/timing profile per ingredient
category (e.g. most humectants are safe for all skin types, used anytime).

INGREDIENTS: the actual list of ingredients. Each entry is a dict with:
  name            - common/INCI-ish display name (required, unique)
  inci_name       - official INCI name if different from `name` (optional)
  aliases         - list of other names/spellings found on labels
  category        - key into CATEGORY_DEFAULTS
  function        - one-line plain-language description of what it does
  uses            - list of short use-cases (what it helps with)
  overrides       - dict overriding any CATEGORY_DEFAULTS field for this
                    specific ingredient (safety_status, safety_score,
                    suitable_skin_types, avoid_skin_types, when_to_use,
                    precautions)

This is a curated *seed* set (a few hundred of the most common skincare
ingredients), not an exhaustive 1000+ regulatory database — hand-authoring
safety verdicts for a thousand+ individual chemicals risks getting some
wrong, which isn't acceptable for anything health-adjacent. See
docs/EXPANDING_INGREDIENT_DB.md for how to grow this further using bulk
public sources (CosIng, INCI Beauty, etc.) instead of one-by-one by hand.
"""

ALL_SKIN_TYPES = ["Normal", "Dry", "Oily", "Combination", "Sensitive"]

CATEGORY_DEFAULTS = {
    "Humectant": {
        "safety_status": "Beneficial",
        "safety_score": 5,
        "suitable_skin_types": ALL_SKIN_TYPES,
        "avoid_skin_types": [],
        "when_to_use": "AM & PM",
        "precautions": "Generally well tolerated. In very dry/low-humidity climates, some humectants can pull moisture from deeper skin layers if used without an occlusive on top — follow with a moisturizer.",
    },
    "Emollient/Occlusive": {
        "safety_status": "Beneficial",
        "safety_score": 4,
        "suitable_skin_types": ["Normal", "Dry", "Sensitive"],
        "avoid_skin_types": ["Oily"],
        "when_to_use": "AM & PM",
        "precautions": "Can feel heavy or contribute to congestion on oily/acne-prone skin depending on comedogenicity.",
    },
    "Lightweight Emollient": {
        "safety_status": "Beneficial",
        "safety_score": 5,
        "suitable_skin_types": ALL_SKIN_TYPES,
        "avoid_skin_types": [],
        "when_to_use": "AM & PM",
        "precautions": "Generally well tolerated across skin types.",
    },
    "AHA Exfoliant": {
        "safety_status": "Caution",
        "safety_score": 3,
        "suitable_skin_types": ["Normal", "Dry", "Combination"],
        "avoid_skin_types": ["Sensitive"],
        "when_to_use": "PM only, introduce gradually (2-3x/week)",
        "precautions": "Increases sun sensitivity — daily SPF is essential. Avoid combining with other strong exfoliants or retinoids in the same routine. Patch test first.",
    },
    "BHA Exfoliant": {
        "safety_status": "Beneficial",
        "safety_score": 4,
        "suitable_skin_types": ["Oily", "Combination", "Normal"],
        "avoid_skin_types": ["Sensitive", "Dry"],
        "when_to_use": "PM, introduce gradually",
        "precautions": "Can be drying with overuse. Increases sun sensitivity — use SPF. Avoid layering with other strong exfoliants.",
    },
    "PHA Exfoliant": {
        "safety_status": "Beneficial",
        "safety_score": 5,
        "suitable_skin_types": ALL_SKIN_TYPES,
        "avoid_skin_types": [],
        "when_to_use": "AM or PM",
        "precautions": "Gentler than AHA/BHA — a good exfoliant option for sensitive skin, but still increases sun sensitivity slightly.",
    },
    "Retinoid": {
        "safety_status": "Caution",
        "safety_score": 3,
        "suitable_skin_types": ["Normal", "Oily", "Combination"],
        "avoid_skin_types": ["Sensitive", "Dry"],
        "when_to_use": "PM only, introduce 2-3x/week and build up",
        "precautions": "Increases sun sensitivity — daily SPF required. Not recommended during pregnancy/breastfeeding (consult a doctor). Can cause dryness/irritation initially (\"retinization\"). Avoid combining with AHA/BHA on the same night.",
    },
    "Vitamin C / Antioxidant": {
        "safety_status": "Beneficial",
        "safety_score": 4,
        "suitable_skin_types": ["Normal", "Oily", "Combination", "Dry"],
        "avoid_skin_types": ["Sensitive"],
        "when_to_use": "AM, under sunscreen",
        "precautions": "Pure ascorbic acid can be irritating at low pH — buffered derivatives are gentler for sensitive skin. Can oxidize (turn brown) with light/air exposure; discard if that happens.",
    },
    "Brightening Agent": {
        "safety_status": "Beneficial",
        "safety_score": 4,
        "suitable_skin_types": ["Normal", "Oily", "Combination", "Dry"],
        "avoid_skin_types": [],
        "when_to_use": "AM or PM",
        "precautions": "Results take weeks of consistent use. Always pair with sunscreen since treated pigmentation is sun-sensitive.",
    },
    "Peptide": {
        "safety_status": "Beneficial",
        "safety_score": 5,
        "suitable_skin_types": ALL_SKIN_TYPES,
        "avoid_skin_types": [],
        "when_to_use": "AM & PM",
        "precautions": "Well tolerated by most skin types; effects build gradually over weeks.",
    },
    "Barrier Lipid": {
        "safety_status": "Beneficial",
        "safety_score": 5,
        "suitable_skin_types": ALL_SKIN_TYPES,
        "avoid_skin_types": [],
        "when_to_use": "AM & PM",
        "precautions": "Excellent for barrier repair; essentially no downside for any skin type.",
    },
    "Soothing/Botanical": {
        "safety_status": "Beneficial",
        "safety_score": 5,
        "suitable_skin_types": ALL_SKIN_TYPES,
        "avoid_skin_types": [],
        "when_to_use": "AM & PM",
        "precautions": "Generally well tolerated, though plant extracts can occasionally trigger sensitivity in those with specific plant allergies.",
    },
    "Preservative": {
        "safety_status": "Caution",
        "safety_score": 3,
        "suitable_skin_types": ["Normal", "Oily", "Combination", "Dry"],
        "avoid_skin_types": ["Sensitive"],
        "when_to_use": "N/A — functional ingredient, not an active",
        "precautions": "Necessary to prevent microbial growth in the product. Some individuals are sensitive/allergic to specific preservatives — patch test if you have a known history of reactions.",
    },
    "Preservative (Higher Sensitivity Risk)": {
        "safety_status": "Potential Irritant",
        "safety_score": 2,
        "suitable_skin_types": ["Normal", "Oily"],
        "avoid_skin_types": ["Sensitive", "Dry"],
        "when_to_use": "N/A — functional ingredient, not an active",
        "precautions": "Linked to contact allergies/sensitization in a meaningful share of users, especially in leave-on products. Sensitive-skin users may want to avoid or patch test carefully.",
    },
    "Surfactant (Gentle)": {
        "safety_status": "Beneficial",
        "safety_score": 4,
        "suitable_skin_types": ALL_SKIN_TYPES,
        "avoid_skin_types": [],
        "when_to_use": "As part of a cleanser, AM & PM",
        "precautions": "Mild cleansing agents, well tolerated by most skin types including sensitive.",
    },
    "Surfactant (Strong)": {
        "safety_status": "Potential Irritant",
        "safety_score": 2,
        "suitable_skin_types": ["Oily"],
        "avoid_skin_types": ["Sensitive", "Dry"],
        "when_to_use": "As part of a cleanser — avoid daily use on dry/sensitive skin",
        "precautions": "Can strip natural oils and disrupt the skin barrier with frequent use, leading to dryness or irritation.",
    },
    "Silicone": {
        "safety_status": "Beneficial",
        "safety_score": 4,
        "suitable_skin_types": ["Normal", "Dry", "Combination"],
        "avoid_skin_types": ["Oily"],
        "when_to_use": "AM & PM",
        "precautions": "Non-comedogenic for most, but can feel occlusive; some acne-prone users prefer to limit heavy silicone use.",
    },
    "Sunscreen Filter (Chemical)": {
        "safety_status": "Beneficial",
        "safety_score": 4,
        "suitable_skin_types": ["Normal", "Oily", "Combination", "Dry"],
        "avoid_skin_types": ["Sensitive"],
        "when_to_use": "AM, reapply every 2 hours in sun",
        "precautions": "Occasionally causes stinging in the eyes or irritation in very sensitive/reactive skin — mineral filters are a common alternative.",
    },
    "Sunscreen Filter (Mineral)": {
        "safety_status": "Beneficial",
        "safety_score": 5,
        "suitable_skin_types": ALL_SKIN_TYPES,
        "avoid_skin_types": [],
        "when_to_use": "AM, reapply every 2 hours in sun",
        "precautions": "Well tolerated, including by sensitive and reactive skin. Can leave a white cast depending on formulation.",
    },
    "Fragrance/Essential Oil": {
        "safety_status": "Potential Irritant",
        "safety_score": 2,
        "suitable_skin_types": ["Normal", "Oily"],
        "avoid_skin_types": ["Sensitive", "Dry"],
        "when_to_use": "N/A — cosmetic/scent ingredient, not a treatment",
        "precautions": "A leading cause of cosmetic contact allergy and irritation, especially on compromised or sensitive skin barriers. Some citrus oils are also phototoxic (avoid before sun exposure).",
    },
    "Drying Alcohol": {
        "safety_status": "Potential Irritant",
        "safety_score": 2,
        "suitable_skin_types": ["Oily"],
        "avoid_skin_types": ["Sensitive", "Dry"],
        "when_to_use": "N/A — solvent/astringent, used sparingly",
        "precautions": "Can be drying and disrupt the skin barrier with frequent/high-concentration use.",
    },
    "Fatty Alcohol": {
        "safety_status": "Beneficial",
        "safety_score": 5,
        "suitable_skin_types": ALL_SKIN_TYPES,
        "avoid_skin_types": [],
        "when_to_use": "AM & PM",
        "precautions": "Despite the name, these are emollient and non-drying — not related to drying alcohols like ethanol.",
    },
    "pH Adjuster": {
        "safety_status": "Beneficial",
        "safety_score": 4,
        "suitable_skin_types": ALL_SKIN_TYPES,
        "avoid_skin_types": [],
        "when_to_use": "N/A — functional ingredient, not an active",
        "precautions": "Used in small amounts to balance formula pH; not a concern at cosmetic concentrations.",
    },
    "Texture/Thickener": {
        "safety_status": "Beneficial",
        "safety_score": 5,
        "suitable_skin_types": ALL_SKIN_TYPES,
        "avoid_skin_types": [],
        "when_to_use": "N/A — functional ingredient, not an active",
        "precautions": "Purely textural; not associated with irritation at typical use levels.",
    },
    "Chelating Agent": {
        "safety_status": "Beneficial",
        "safety_score": 4,
        "suitable_skin_types": ALL_SKIN_TYPES,
        "avoid_skin_types": [],
        "when_to_use": "N/A — functional ingredient, not an active",
        "precautions": "Stabilizes formulas; not a concern at cosmetic concentrations.",
    },
    "Colorant/Pigment": {
        "safety_status": "Beneficial",
        "safety_score": 4,
        "suitable_skin_types": ALL_SKIN_TYPES,
        "avoid_skin_types": [],
        "when_to_use": "N/A — cosmetic colorant",
        "precautions": "Purely cosmetic; occasionally a sensitizer for those with specific pigment allergies.",
    },
    "Acne Active": {
        "safety_status": "Caution",
        "safety_score": 3,
        "suitable_skin_types": ["Oily", "Combination"],
        "avoid_skin_types": ["Sensitive", "Dry"],
        "when_to_use": "PM, introduce gradually",
        "precautions": "Can cause dryness, peeling, or bleaching of fabrics/towels depending on the active. Start with lower strength/frequency.",
    },
    "Clay/Absorbent": {
        "safety_status": "Beneficial",
        "safety_score": 4,
        "suitable_skin_types": ["Oily", "Combination", "Normal"],
        "avoid_skin_types": ["Dry", "Sensitive"],
        "when_to_use": "1-2x/week as a mask",
        "precautions": "Can be over-drying if left on too long or used too frequently, especially on drier skin.",
    },
}


def _entry(name, category, function, uses, inci_name=None, aliases=None, **overrides):
    return {
        "name": name,
        "inci_name": inci_name,
        "aliases": aliases or [],
        "category": category,
        "function": function,
        "uses": uses,
        "overrides": overrides,
    }


INGREDIENTS = [
    # --- Humectants -------------------------------------------------------
    _entry("Glycerin", "Humectant", "Draws water into the skin from the air and deeper layers.",
           ["Hydration", "Barrier support"], aliases=["Glycerol"]),
    _entry("Hyaluronic Acid", "Humectant", "A naturally occurring molecule that holds up to 1000x its weight in water.",
           ["Hydration", "Plumping"], inci_name="Sodium Hyaluronate", aliases=["Sodium Hyaluronate", "Hyaluronan"]),
    _entry("Sodium PCA", "Humectant", "A natural component of skin's own moisturizing factor.", ["Hydration"]),
    _entry("Propylene Glycol", "Humectant", "Attracts moisture and helps other ingredients penetrate.",
           ["Hydration", "Texture enhancer"]),
    _entry("Butylene Glycol", "Humectant", "Lightweight humectant and solvent used in many serums.",
           ["Hydration", "Solvent"]),
    _entry("Urea", "Humectant", "Hydrates and gently helps shed built-up dry skin.", ["Hydration", "Mild exfoliation"],
           when_to_use="AM & PM", precautions="Can sting on broken or very irritated skin — avoid on active breakouts of eczema."),
    _entry("Sorbitol", "Humectant", "A sugar-derived humectant that softens and hydrates skin.", ["Hydration"]),
    _entry("Betaine", "Humectant", "A gentle humectant derived from sugar beets, also soothing.", ["Hydration", "Soothing"]),
    _entry("Panthenol", "Humectant", "Pro-vitamin B5; hydrates and supports barrier repair.",
           ["Hydration", "Soothing", "Barrier support"], aliases=["Pro-Vitamin B5", "D-Panthenol"]),
    _entry("Honey Extract", "Humectant", "Natural humectant with mild antibacterial properties.", ["Hydration", "Soothing"]),
    _entry("Aloe Vera", "Soothing/Botanical", "Hydrates and calms irritated or sun-exposed skin.",
           ["Hydration", "Soothing", "After-sun care"], inci_name="Aloe Barbadensis Leaf Juice"),
    _entry("Beta-Glucan", "Humectant", "Derived from oats; hydrates and soothes sensitive skin.", ["Hydration", "Soothing"]),

    # --- Emollients / Occlusives -------------------------------------------
    _entry("Dimethicone", "Silicone", "Forms a smooth, breathable film that locks in moisture.",
           ["Hydration lock-in", "Smoothing texture"]),
    _entry("Cyclopentasiloxane", "Silicone", "A lightweight, fast-evaporating silicone for silky texture.", ["Texture enhancer"]),
    _entry("Cyclohexasiloxane", "Silicone", "Similar to cyclopentasiloxane — improves spreadability.", ["Texture enhancer"]),
    _entry("Dimethiconol", "Silicone", "A conditioning silicone that adds shine and softness.", ["Conditioning"]),
    _entry("Phenyl Trimethicone", "Silicone", "Adds shine and a silky after-feel.", ["Conditioning", "Shine"]),
    _entry("Squalane", "Lightweight Emollient", "A stable, plant- or lab-derived version of skin's natural squalene.",
           ["Moisturizing", "Barrier support"], aliases=["Squalene (hydrogenated)"]),
    _entry("Shea Butter", "Emollient/Occlusive", "Rich in fatty acids; deeply moisturizes and soothes.",
           ["Deep moisturizing", "Barrier support"], inci_name="Butyrospermum Parkii Butter"),
    _entry("Jojoba Oil", "Lightweight Emollient", "Closely mimics skin's natural sebum; absorbs well.",
           ["Moisturizing", "Balancing"], inci_name="Simmondsia Chinensis Seed Oil"),
    _entry("Mineral Oil", "Emollient/Occlusive", "A highly refined occlusive that prevents water loss.",
           ["Moisture barrier", "Softening"], precautions="Cosmetic-grade mineral oil is non-comedogenic for most despite common myths, but can feel heavy on oily skin."),
    _entry("Petrolatum", "Emollient/Occlusive", "An extremely effective occlusive that seals in moisture.",
           ["Moisture barrier", "Wound/dry-patch healing"], aliases=["Petroleum Jelly"]),
    _entry("Lanolin", "Emollient/Occlusive", "A rich, wax-like emollient derived from sheep's wool.",
           ["Deep moisturizing"], precautions="A known allergen for a subset of users — patch test first if you have sensitive skin.",
           avoid_skin_types=["Sensitive", "Oily"]),
    _entry("Castor Oil", "Emollient/Occlusive", "A thick oil used for moisturizing and in some lash/brow products.", ["Moisturizing"]),
    _entry("Coconut Oil", "Emollient/Occlusive", "A rich, comedogenic oil that deeply moisturizes dry skin.",
           ["Moisturizing"], avoid_skin_types=["Oily", "Combination"], precautions="Considered comedogenic — can clog pores on acne-prone/oily skin."),
    _entry("Argan Oil", "Lightweight Emollient", "Rich in vitamin E and fatty acids; nourishes without heaviness.",
           ["Moisturizing", "Antioxidant"], inci_name="Argania Spinosa Kernel Oil"),
    _entry("Sunflower Seed Oil", "Lightweight Emollient", "Light, linoleic-acid-rich oil that supports the skin barrier.",
           ["Moisturizing", "Barrier support"]),
    _entry("Safflower Oil", "Lightweight Emollient", "Similar to sunflower oil — lightweight and barrier-supportive.", ["Moisturizing"]),
    _entry("Olive Oil", "Emollient/Occlusive", "A heavy, oleic-acid-rich oil best suited to very dry skin.",
           ["Moisturizing"], avoid_skin_types=["Oily", "Combination"], precautions="Can be comedogenic for acne-prone skin."),
    _entry("Grapeseed Oil", "Lightweight Emollient", "Light oil rich in linoleic acid and antioxidants.", ["Moisturizing", "Antioxidant"]),
    _entry("Rosehip Oil", "Lightweight Emollient", "Rich in vitamin A and fatty acids; supports skin renewal.",
           ["Moisturizing", "Brightening support"]),
    _entry("Marula Oil", "Lightweight Emollient", "A light, antioxidant-rich facial oil.", ["Moisturizing", "Antioxidant"]),
    _entry("Cetyl Alcohol", "Fatty Alcohol", "A fatty alcohol that thickens formulas and softens skin.", ["Texture", "Softening"]),
    _entry("Stearyl Alcohol", "Fatty Alcohol", "Emollient fatty alcohol used to thicken creams.", ["Texture", "Softening"]),
    _entry("Cetearyl Alcohol", "Fatty Alcohol", "A blend of cetyl/stearyl alcohol; conditions and thickens.", ["Texture", "Softening"]),
    _entry("Isopropyl Myristate", "Lightweight Emollient", "A light synthetic emollient that improves spreadability.",
           ["Texture enhancer"], avoid_skin_types=["Oily"], precautions="Can be comedogenic for some acne-prone users."),
    _entry("Isopropyl Palmitate", "Lightweight Emollient", "Similar light emollient improving product glide.",
           ["Texture enhancer"], avoid_skin_types=["Oily"]),
    _entry("Caprylic/Capric Triglyceride", "Lightweight Emollient", "A lightweight, coconut-derived emollient.", ["Moisturizing"]),
    _entry("Beeswax", "Emollient/Occlusive", "A natural wax that thickens balms and locks in moisture.", ["Moisture barrier"]),
    _entry("Candelilla Wax", "Emollient/Occlusive", "A plant-based wax alternative to beeswax.", ["Texture", "Moisture barrier"]),

    # --- AHA exfoliants -----------------------------------------------------
    _entry("Glycolic Acid", "AHA Exfoliant", "The smallest AHA molecule; exfoliates and brightens skin.",
           ["Exfoliation", "Brightening", "Texture improvement"]),
    _entry("Lactic Acid", "AHA Exfoliant", "A gentler AHA that also hydrates while exfoliating.",
           ["Exfoliation", "Hydration"], suitable_skin_types=["Normal", "Dry", "Combination", "Sensitive"], avoid_skin_types=[]),
    _entry("Mandelic Acid", "AHA Exfoliant", "A larger, gentler AHA molecule suited to sensitive/acne-prone skin.",
           ["Exfoliation", "Acne support"], suitable_skin_types=["Normal", "Dry", "Combination", "Oily", "Sensitive"], avoid_skin_types=[]),
    _entry("Citric Acid", "AHA Exfoliant", "A mild AHA also used to adjust product pH.", ["Exfoliation", "pH adjustment"]),
    _entry("Tartaric Acid", "AHA Exfoliant", "A mild AHA derived from grapes.", ["Exfoliation"]),
    _entry("Malic Acid", "AHA Exfoliant", "A mild AHA often blended with other acids.", ["Exfoliation"]),

    # --- BHA exfoliants -----------------------------------------------------
    _entry("Salicylic Acid", "BHA Exfoliant", "An oil-soluble acid that exfoliates inside the pore.",
           ["Acne treatment", "Pore clarity", "Exfoliation"]),
    _entry("Betaine Salicylate", "BHA Exfoliant", "A gentler, plant-derived BHA alternative.",
           ["Acne treatment", "Exfoliation"], safety_score=4),

    # --- PHA exfoliants -----------------------------------------------------
    _entry("Gluconolactone", "PHA Exfoliant", "A gentle exfoliating PHA suited to sensitive skin.", ["Exfoliation", "Antioxidant"]),
    _entry("Lactobionic Acid", "PHA Exfoliant", "A gentle PHA with humectant properties.", ["Exfoliation", "Hydration"]),

    # --- Retinoids -----------------------------------------------------------
    _entry("Retinol", "Retinoid", "A vitamin A derivative that speeds cell turnover and boosts collagen.",
           ["Anti-aging", "Acne support", "Texture improvement"]),
    _entry("Retinyl Palmitate", "Retinoid", "A milder, ester form of vitamin A.", ["Anti-aging"], safety_score=4),
    _entry("Retinaldehyde", "Retinoid", "A stronger vitamin A form that converts to retinoic acid faster than retinol.",
           ["Anti-aging", "Acne support"]),
    _entry("Hydroxypinacolone Retinoate", "Retinoid", "A gentler retinoid ester with less irritation potential.",
           ["Anti-aging"], safety_score=4, when_to_use="PM, can often be used nightly with less irritation than retinol"),
    _entry("Bakuchiol", "Retinoid", "A plant-derived retinol alternative with a similar effect, gentler profile.",
           ["Anti-aging", "Acne support"], safety_status="Beneficial", safety_score=5,
           suitable_skin_types=ALL_SKIN_TYPES, avoid_skin_types=[], when_to_use="AM or PM",
           precautions="Considered a gentler alternative to traditional retinoids, suitable for sensitive skin and generally pregnancy-safe — confirm with a doctor."),

    # --- Vitamin C & antioxidants ---------------------------------------------
    _entry("Ascorbic Acid", "Vitamin C / Antioxidant", "Pure vitamin C; brightens and protects against free radicals.",
           ["Brightening", "Antioxidant", "Collagen support"], aliases=["L-Ascorbic Acid"]),
    _entry("Sodium Ascorbyl Phosphate", "Vitamin C / Antioxidant", "A stable, gentler vitamin C derivative.",
           ["Brightening", "Antioxidant"], safety_score=5, suitable_skin_types=ALL_SKIN_TYPES, avoid_skin_types=[]),
    _entry("Magnesium Ascorbyl Phosphate", "Vitamin C / Antioxidant", "A stable, water-soluble vitamin C derivative.",
           ["Brightening", "Antioxidant"], safety_score=5, suitable_skin_types=ALL_SKIN_TYPES, avoid_skin_types=[]),
    _entry("Tetrahexyldecyl Ascorbate", "Vitamin C / Antioxidant", "An oil-soluble, stable vitamin C derivative.",
           ["Brightening", "Antioxidant"], safety_score=5, suitable_skin_types=ALL_SKIN_TYPES, avoid_skin_types=[]),
    _entry("Ferulic Acid", "Vitamin C / Antioxidant", "A plant antioxidant that stabilizes vitamin C/E blends.",
           ["Antioxidant", "Stabilizer"]),
    _entry("Tocopherol", "Vitamin C / Antioxidant", "Vitamin E; an antioxidant that also softens skin.",
           ["Antioxidant", "Moisturizing"], aliases=["Vitamin E"], safety_score=5, suitable_skin_types=ALL_SKIN_TYPES, avoid_skin_types=[]),
    _entry("Resveratrol", "Vitamin C / Antioxidant", "A plant antioxidant that helps neutralize free radicals.", ["Antioxidant", "Anti-aging"]),
    _entry("Coenzyme Q10", "Vitamin C / Antioxidant", "An antioxidant naturally found in skin that declines with age.",
           ["Antioxidant", "Anti-aging"], aliases=["Ubiquinone"]),
    _entry("Alpha Lipoic Acid", "Vitamin C / Antioxidant", "A potent antioxidant used in anti-aging formulas.", ["Antioxidant", "Anti-aging"]),
    _entry("Idebenone", "Vitamin C / Antioxidant", "A synthetic antioxidant similar to CoQ10.", ["Antioxidant", "Anti-aging"]),
    _entry("Green Tea Extract", "Vitamin C / Antioxidant", "Rich in EGCG, a potent antioxidant and anti-inflammatory.",
           ["Antioxidant", "Soothing"], inci_name="Camellia Sinensis Leaf Extract"),
    _entry("Grape Seed Extract", "Vitamin C / Antioxidant", "An antioxidant extract that helps fight free-radical damage.", ["Antioxidant"]),

    # --- Brightening agents ---------------------------------------------------
    _entry("Niacinamide", "Brightening Agent", "Vitamin B3; supports the barrier, evens tone, and controls oil.",
           ["Brightening", "Barrier support", "Oil control"], safety_status="Beneficial", safety_score=5,
           suitable_skin_types=ALL_SKIN_TYPES, avoid_skin_types=[]),
    _entry("Alpha Arbutin", "Brightening Agent", "A gentler, stable form of arbutin that fades dark spots.", ["Brightening"]),
    _entry("Arbutin", "Brightening Agent", "A naturally derived skin-brightening compound.", ["Brightening"]),
    _entry("Kojic Acid", "Brightening Agent", "A fungal-derived brightening agent that inhibits pigment production.",
           ["Brightening"], precautions="Can be sensitizing at higher concentrations — patch test first.", avoid_skin_types=["Sensitive"]),
    _entry("Azelaic Acid", "Brightening Agent", "Treats both pigmentation and acne/redness; gentle enough for regular use.",
           ["Brightening", "Acne support", "Redness reduction"], safety_status="Beneficial", safety_score=5,
           suitable_skin_types=ALL_SKIN_TYPES, avoid_skin_types=[]),
    _entry("Tranexamic Acid", "Brightening Agent", "Targets stubborn discoloration and post-acne marks.", ["Brightening"]),
    _entry("Licorice Root Extract", "Brightening Agent", "A soothing plant extract that also helps even tone.",
           ["Brightening", "Soothing"], inci_name="Glycyrrhiza Glabra Root Extract"),

    # --- Peptides ---------------------------------------------------------------
    _entry("Palmitoyl Pentapeptide-4", "Peptide", "A signal peptide (\"Matrixyl\") that supports collagen production.",
           ["Anti-aging"], aliases=["Matrixyl"]),
    _entry("Copper Tripeptide-1", "Peptide", "A peptide known for supporting skin repair and firmness.",
           ["Anti-aging", "Repair support"], aliases=["Copper Peptide", "GHK-Cu"]),
    _entry("Palmitoyl Tripeptide-1", "Peptide", "Supports collagen synthesis for firmer-looking skin.", ["Anti-aging"]),
    _entry("Acetyl Hexapeptide-8", "Peptide", "A peptide marketed to relax micro-expression lines.",
           ["Anti-aging"], aliases=["Argireline"]),

    # --- Barrier lipids -----------------------------------------------------------
    _entry("Ceramide NP", "Barrier Lipid", "A skin-identical lipid that restores and strengthens the barrier.",
           ["Barrier repair", "Hydration"]),
    _entry("Ceramide AP", "Barrier Lipid", "Works alongside other ceramides to rebuild the skin barrier.", ["Barrier repair"]),
    _entry("Ceramide EOP", "Barrier Lipid", "A key structural ceramide for barrier integrity.", ["Barrier repair"]),
    _entry("Cholesterol", "Barrier Lipid", "A lipid that, with ceramides and fatty acids, rebuilds the skin barrier.", ["Barrier repair"]),
    _entry("Linoleic Acid", "Barrier Lipid", "An essential fatty acid that supports barrier function.", ["Barrier repair"]),
    _entry("Phytosphingosine", "Barrier Lipid", "A lipid that supports barrier repair and has mild antimicrobial action.", ["Barrier repair"]),

    # --- Soothing / botanical -----------------------------------------------------
    _entry("Centella Asiatica Extract", "Soothing/Botanical", "Calms redness and supports wound/barrier healing.",
           ["Soothing", "Barrier repair"], aliases=["Cica", "Gotu Kola"]),
    _entry("Madecassoside", "Soothing/Botanical", "An active compound from Centella asiatica; calms and repairs.", ["Soothing", "Barrier repair"]),
    _entry("Allantoin", "Soothing/Botanical", "A gentle soothing agent that supports skin healing.", ["Soothing", "Repair support"]),
    _entry("Bisabolol", "Soothing/Botanical", "A calming compound derived from chamomile.", ["Soothing", "Anti-inflammatory"]),
    _entry("Colloidal Oatmeal", "Soothing/Botanical", "Soothes itching and irritation; supports barrier function.", ["Soothing", "Barrier support"]),
    _entry("Chamomile Extract", "Soothing/Botanical", "A calming plant extract used for sensitive/reactive skin.", ["Soothing"]),
    _entry("Calendula Extract", "Soothing/Botanical", "A gentle, calming extract traditionally used for irritation.", ["Soothing"]),
    _entry("Azulene", "Soothing/Botanical", "A calming compound derived from chamomile, gives products a blue tint.", ["Soothing"]),
    _entry("Snail Secretion Filtrate", "Soothing/Botanical", "Popular in K-beauty for hydration and repair support.", ["Hydration", "Repair support"]),

    # --- Preservatives -------------------------------------------------------------
    _entry("Phenoxyethanol", "Preservative", "A broad-spectrum preservative used at low concentrations.", ["Preservation"]),
    _entry("Potassium Sorbate", "Preservative", "A mild, widely used preservative.", ["Preservation"]),
    _entry("Sodium Benzoate", "Preservative", "A common preservative, often paired with potassium sorbate.", ["Preservation"]),
    _entry("Benzyl Alcohol", "Preservative", "Functions as both a preservative and a solvent.", ["Preservation", "Solvent"]),
    _entry("Sorbic Acid", "Preservative", "A mild preservative derived from berries.", ["Preservation"]),
    _entry("Dehydroacetic Acid", "Preservative", "A preservative often paired with benzyl alcohol.", ["Preservation"]),
    _entry("Chlorphenesin", "Preservative", "A preservative with mild antimicrobial and antifungal action.", ["Preservation"]),
    _entry("Methylparaben", "Preservative (Higher Sensitivity Risk)", "A widely used preservative from the paraben family.", ["Preservation"]),
    _entry("Propylparaben", "Preservative (Higher Sensitivity Risk)", "A paraben preservative, often paired with methylparaben.", ["Preservation"]),
    _entry("Butylparaben", "Preservative (Higher Sensitivity Risk)", "A longer-chain paraben preservative.", ["Preservation"]),
    _entry("Ethylparaben", "Preservative (Higher Sensitivity Risk)", "A shorter-chain paraben preservative.", ["Preservation"]),
    _entry("DMDM Hydantoin", "Preservative (Higher Sensitivity Risk)", "A formaldehyde-releasing preservative.",
           ["Preservation"], precautions="Slowly releases trace formaldehyde, which can be sensitizing for some — those with formaldehyde sensitivity should avoid."),
    _entry("Imidazolidinyl Urea", "Preservative (Higher Sensitivity Risk)", "A formaldehyde-releasing preservative.",
           ["Preservation"], precautions="Can release trace formaldehyde — a known sensitizer for some users."),
    _entry("Diazolidinyl Urea", "Preservative (Higher Sensitivity Risk)", "A formaldehyde-releasing preservative.",
           ["Preservation"], precautions="Can release trace formaldehyde — a known sensitizer for some users."),
    _entry("Quaternium-15", "Preservative (Higher Sensitivity Risk)", "A formaldehyde-releasing preservative.",
           ["Preservation"], precautions="One of the more sensitizing formaldehyde-releasers — avoid if you have known sensitivity."),
    _entry("Methylisothiazolinone", "Preservative (Higher Sensitivity Risk)", "A preservative increasingly restricted due to allergy potential.",
           ["Preservation"], safety_status="Potential Irritant", safety_score=1,
           precautions="Associated with a notable rise in contact allergy cases; many sensitive-skin users choose to avoid it entirely.",
           avoid_skin_types=["Sensitive", "Dry"]),
    _entry("Methylchloroisothiazolinone", "Preservative (Higher Sensitivity Risk)", "Often paired with methylisothiazolinone; similar allergy profile.",
           ["Preservation"], safety_status="Potential Irritant", safety_score=1,
           precautions="Associated with contact allergy; best avoided by sensitive-skin users.", avoid_skin_types=["Sensitive", "Dry"]),

    # --- Surfactants -----------------------------------------------------------------
    _entry("Decyl Glucoside", "Surfactant (Gentle)", "A mild, plant-derived cleansing agent.", ["Cleansing"]),
    _entry("Coco-Glucoside", "Surfactant (Gentle)", "A gentle coconut-derived cleansing agent.", ["Cleansing"]),
    _entry("Lauryl Glucoside", "Surfactant (Gentle)", "A mild cleansing agent suitable for sensitive skin.", ["Cleansing"]),
    _entry("Cocamidopropyl Betaine", "Surfactant (Gentle)", "A mild co-surfactant that boosts foam and mildness.",
           ["Cleansing"], precautions="Occasionally sensitizing for a small subset of users despite its generally mild reputation."),
    _entry("Sodium Cocoyl Isethionate", "Surfactant (Gentle)", "A gentle, coconut-derived cleansing agent common in cleansing bars.", ["Cleansing"]),
    _entry("Disodium Cocoamphodiacetate", "Surfactant (Gentle)", "A mild, foam-boosting cleansing agent.", ["Cleansing"]),
    _entry("Sodium Methyl Cocoyl Taurate", "Surfactant (Gentle)", "A gentle, sulfate-free cleansing agent.", ["Cleansing"]),
    _entry("Sodium Lauryl Sulfate", "Surfactant (Strong)", "An effective but potentially drying cleansing agent.",
           ["Cleansing"], aliases=["SLS"]),
    _entry("Sodium Laureth Sulfate", "Surfactant (Strong)", "A milder sulfate cleansing agent than SLS, still can be drying.",
           ["Cleansing"], aliases=["SLES"], safety_score=3),

    # --- Sunscreen filters --------------------------------------------------------------
    _entry("Avobenzone", "Sunscreen Filter (Chemical)", "A broad-spectrum UVA filter, often paired with UVB filters.", ["Sun protection"]),
    _entry("Octocrylene", "Sunscreen Filter (Chemical)", "A UVB filter that also stabilizes other sunscreen actives.", ["Sun protection"]),
    _entry("Octinoxate", "Sunscreen Filter (Chemical)", "A common UVB filter.", ["Sun protection"], aliases=["Octyl Methoxycinnamate"]),
    _entry("Homosalate", "Sunscreen Filter (Chemical)", "A UVB filter used in many sunscreen formulas.", ["Sun protection"]),
    _entry("Octisalate", "Sunscreen Filter (Chemical)", "A UVB filter, also used to stabilize avobenzone.",
           ["Sun protection"], aliases=["Octyl Salicylate"]),
    _entry("Oxybenzone", "Sunscreen Filter (Chemical)", "A broad-spectrum UV filter, restricted in some regions over reef-safety concerns.",
           ["Sun protection"], precautions="More prone to causing sensitization/allergy than newer filters; also restricted in some regions for environmental reasons."),
    _entry("Ensulizole", "Sunscreen Filter (Chemical)", "A water-soluble UVB filter.", ["Sun protection"]),
    _entry("Bemotrizinol", "Sunscreen Filter (Chemical)", "A modern, highly photostable broad-spectrum filter.",
           ["Sun protection"], aliases=["Tinosorb S"], safety_score=5),
    _entry("Bisoctrizole", "Sunscreen Filter (Chemical)", "A modern broad-spectrum filter effective against UVA and UVB.",
           ["Sun protection"], aliases=["Tinosorb M"], safety_score=5),
    _entry("Zinc Oxide", "Sunscreen Filter (Mineral)", "A mineral, broad-spectrum sun filter that sits on the skin's surface.",
           ["Sun protection", "Soothing"]),
    _entry("Titanium Dioxide", "Sunscreen Filter (Mineral)", "A mineral UV filter, also used as a cosmetic pigment.",
           ["Sun protection", "Pigment"]),

    # --- Fragrance / essential oils --------------------------------------------------------
    _entry("Fragrance", "Fragrance/Essential Oil", "A blend of scent compounds; the single most common cosmetic allergen.",
           ["Scent"], aliases=["Parfum"]),
    _entry("Lavender Oil", "Fragrance/Essential Oil", "An essential oil valued for scent, can be sensitizing.", ["Scent", "Relaxation"]),
    _entry("Tea Tree Oil", "Fragrance/Essential Oil", "Has antimicrobial properties but can irritate at high concentrations.",
           ["Acne support", "Antimicrobial"], safety_status="Caution", safety_score=3),
    _entry("Peppermint Oil", "Fragrance/Essential Oil", "Gives a cooling sensation; can irritate sensitive skin.", ["Scent", "Cooling sensation"]),
    _entry("Eucalyptus Oil", "Fragrance/Essential Oil", "An aromatic oil that can be irritating on broken/reactive skin.", ["Scent"]),
    _entry("Bergamot Oil", "Fragrance/Essential Oil", "A citrus oil that increases photosensitivity.",
           ["Scent"], precautions="Phototoxic — avoid sun exposure after application unless the phototoxic compounds have been removed (bergapten-free)."),
    _entry("Limonene", "Fragrance/Essential Oil", "A citrus-derived fragrance compound and EU-listed allergen.", ["Scent"]),
    _entry("Linalool", "Fragrance/Essential Oil", "A floral fragrance compound and EU-listed allergen.", ["Scent"]),
    _entry("Citronellol", "Fragrance/Essential Oil", "A fragrance compound and EU-listed allergen.", ["Scent"]),
    _entry("Geraniol", "Fragrance/Essential Oil", "A floral fragrance compound and EU-listed allergen.", ["Scent"]),
    _entry("Eugenol", "Fragrance/Essential Oil", "A clove-derived fragrance compound and EU-listed allergen.", ["Scent"]),
    _entry("Coumarin", "Fragrance/Essential Oil", "A sweet-smelling fragrance compound and EU-listed allergen.", ["Scent"]),

    # --- Alcohols -----------------------------------------------------------------------------
    _entry("Alcohol Denat", "Drying Alcohol", "A fast-evaporating solvent that can help other actives absorb.",
           ["Solvent", "Astringent"], aliases=["Denatured Alcohol", "SD Alcohol"]),
    _entry("Isopropyl Alcohol", "Drying Alcohol", "A solvent/astringent that can be drying with frequent use.", ["Solvent", "Astringent"]),
    _entry("Witch Hazel", "Drying Alcohol", "A traditional astringent, milder when alcohol-free versions are used.",
           ["Astringent", "Soothing"], safety_status="Caution", safety_score=3,
           precautions="Alcohol-containing witch hazel can be drying; alcohol-free versions are gentler."),

    # --- pH adjusters / stabilizers ----------------------------------------------------------
    _entry("Sodium Hydroxide", "pH Adjuster", "Used in tiny amounts to balance a formula's pH.", ["pH adjustment"]),
    _entry("Potassium Hydroxide", "pH Adjuster", "Used to balance formula pH, common in cleansers.", ["pH adjustment"]),
    _entry("Triethanolamine", "pH Adjuster", "A pH-balancing agent used in some formulas.", ["pH adjustment"], aliases=["TEA"]),
    _entry("Sodium Citrate", "pH Adjuster", "A mild pH-balancing agent derived from citric acid.", ["pH adjustment"]),

    # --- Texture / thickeners -----------------------------------------------------------------
    _entry("Xanthan Gum", "Texture/Thickener", "A natural thickener that gives products their gel-like texture.", ["Texture"]),
    _entry("Carbomer", "Texture/Thickener", "A synthetic thickener used in gels and lightweight lotions.", ["Texture"]),
    _entry("Hydroxyethylcellulose", "Texture/Thickener", "A plant-derived thickening agent.", ["Texture"]),
    _entry("PEG-100 Stearate", "Texture/Thickener", "An emulsifier that helps blend oil and water phases.", ["Emulsifying"]),
    _entry("Glyceryl Stearate", "Texture/Thickener", "An emulsifier and thickener derived from fatty acids.", ["Emulsifying", "Texture"]),
    _entry("Polyvinylpyrrolidone", "Texture/Thickener", "A film-forming polymer used for texture and hold.", ["Texture"], aliases=["PVP"]),
    _entry("Acrylates Copolymer", "Texture/Thickener", "A film-forming polymer that improves texture and wear.", ["Texture"]),

    # --- Chelating agents ----------------------------------------------------------------------
    _entry("Disodium EDTA", "Chelating Agent", "Binds trace metals to keep a formula stable.", ["Stabilizer"]),
    _entry("Tetrasodium EDTA", "Chelating Agent", "Similar to disodium EDTA; stabilizes formulas.", ["Stabilizer"]),

    # --- Colorants ------------------------------------------------------------------------------
    _entry("Mica", "Colorant/Pigment", "A mineral that gives products shimmer or opacity.", ["Cosmetic color/shimmer"]),
    _entry("Iron Oxides", "Colorant/Pigment", "Mineral pigments used to tint creams and mineral makeup.", ["Cosmetic color", "Sun filter boost"]),

    # --- Acne actives ---------------------------------------------------------------------------
    _entry("Benzoyl Peroxide", "Acne Active", "Kills acne-causing bacteria and reduces inflammation.",
           ["Acne treatment"], precautions="Can bleach fabrics/towels. Start at a lower concentration to build tolerance; can be drying."),
    _entry("Sulfur", "Acne Active", "A traditional acne treatment that dries out blemishes.", ["Acne treatment"]),
    _entry("Zinc PCA", "Acne Active", "Helps regulate oil production and supports acne-prone skin.",
           ["Oil control", "Acne support"], safety_status="Beneficial", safety_score=5,
           suitable_skin_types=ALL_SKIN_TYPES, avoid_skin_types=[]),

    # --- Clay / absorbents ------------------------------------------------------------------------
    _entry("Kaolin Clay", "Clay/Absorbent", "A gentle clay that absorbs excess oil.", ["Oil absorption", "Mask treatment"]),
    _entry("Bentonite Clay", "Clay/Absorbent", "A stronger absorbing clay, best for oily/combination skin.", ["Oil absorption", "Mask treatment"]),
    _entry("Activated Charcoal", "Clay/Absorbent", "Absorbs oil and impurities; popular in detox-style masks.", ["Oil/impurity absorption"]),
    _entry("Silica", "Clay/Absorbent", "A mattifying, oil-absorbing powder used in many formulas.", ["Oil absorption", "Mattifying"]),
]

# ---------------------------------------------------------------------------
# Dataset validation / metadata helpers
# ---------------------------------------------------------------------------

REQUIRED_INGREDIENT_FIELDS = {
    "name",
    "category",
    "function",
    "uses",
    "overrides",
}


def validate_ingredient_catalog() -> None:
    """
    Validate the in-code ingredient catalog at import/startup time.

    This catches malformed entries before they reach the database
    seed process.
    """
    seen_names: set[str] = set()

    for index, entry in enumerate(
        INGREDIENTS,
        start=1,
    ):
        missing = (
            REQUIRED_INGREDIENT_FIELDS
            - set(entry.keys())
        )

        if missing:
            raise ValueError(
                f"Ingredient entry #{index} "
                f"is missing fields: "
                f"{sorted(missing)}"
            )

        name = str(
            entry["name"]
        ).strip()

        if not name:
            raise ValueError(
                f"Ingredient entry #{index} "
                f"has an empty name."
            )

        normalized_name = (
            name.casefold()
        )

        if normalized_name in seen_names:
            raise ValueError(
                "Duplicate ingredient name "
                f"detected: {name}"
            )

        seen_names.add(
            normalized_name
        )

        category = entry["category"]

        if category not in CATEGORY_DEFAULTS:
            raise ValueError(
                f"Ingredient '{name}' uses "
                f"unknown category '{category}'."
            )


def get_catalog_stats() -> dict:
    """
    Return metadata about the bundled ingredient catalog.

    This does not claim SRS 1000+ compliance unless the actual
    catalog contains at least 1000 entries.
    """
    categories: dict[str, int] = {}

    for entry in INGREDIENTS:
        category = entry["category"]

        categories[category] = (
            categories.get(category, 0)
            + 1
        )

    return {
        "total_ingredients": len(
            INGREDIENTS
        ),
        "categories": categories,
        "meets_1000_requirement": (
            len(INGREDIENTS) >= 1000
        ),
    }


# ---------------------------------------------------------------------------
# Validate catalog on import
# ---------------------------------------------------------------------------

validate_ingredient_catalog()